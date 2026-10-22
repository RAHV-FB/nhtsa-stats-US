"""Incremental conversion of the raw archives to a typed Parquet cache.

Layout: ``data/interim/{SOURCE}/{table}/{year}.parquet``.  A manifest
(``data/interim/manifest.json``) records the SHA-256 of every archive that produced the cache,
so an archive is re-extracted only when its bytes change or an output file is missing.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.archives import (
    Archive,
    discover_archives,
    sha256_file,
    validate_archive,
)
from nhtsa_stats.ingestion.readers import read_member, table_members

log = logging.getLogger(__name__)

MANIFEST = "manifest.json"


def interim_path(source: str, table: str, year: int, root: Path | None = None) -> Path:
    return (root or config.INTERIM_DIR) / source / table / f"{year}.parquet"


def _load_manifest(root: Path) -> dict:
    p = root / MANIFEST
    return json.loads(p.read_text()) if p.exists() else {}


def _convert_archive(archive: Archive, root: Path) -> dict:
    record = validate_archive(archive)
    tables = {}
    for table, member in sorted(table_members(archive.path).items()):
        df, meta = read_member(archive.path, member)
        out = interim_path(archive.source, table, archive.year, root)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(out, compression="zstd")
        meta["parquet"] = str(out.relative_to(root))
        tables[table] = meta
    record["tables"] = tables
    return record


def build_interim(
    root: Path | None = None, force: bool = False, workers: int = 2
) -> dict[str, dict]:
    """Convert every archive whose content changed since the last run."""
    root = root or config.INTERIM_DIR
    root.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(root)
    archives = discover_archives()
    todo: list[Archive] = []
    for a in archives:
        prev = manifest.get(a.key)
        up_to_date = (
            not force
            and prev is not None
            and prev.get("size_bytes") == a.size_bytes
            and all((root / t["parquet"]).exists() for t in prev.get("tables", {}).values())
        )
        if up_to_date:
            # Size match is a cheap pre-check; confirm content identity via SHA-256.
            if sha256_file(a.path) == prev["sha256"]:
                continue
        todo.append(a)
    log.info("%d/%d archives need conversion", len(todo), len(archives))
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for a, rec in zip(
                todo, ex.map(_convert_archive, todo, [root] * len(todo)), strict=True
            ):
                manifest[a.key] = rec
                log.info("converted %s (%d tables)", a.path.name, len(rec["tables"]))
    (root / MANIFEST).write_text(json.dumps(manifest, indent=1, sort_keys=True))
    return manifest


def load_table(
    source: str,
    table: str,
    years: tuple[int, ...] | list[int] | None = None,
    columns: list[str] | None = None,
    root: Path | None = None,
    strict: bool = False,
) -> pl.DataFrame:
    """Load one table for several years, aligning columns that differ between years.

    Requested columns absent in a year are filled with nulls (and logged); with
    ``strict=True`` an absent column raises instead.  A ``YEAR`` column is always present.
    """
    years = list(years or config.YEARS)
    frames = []
    for y in years:
        p = interim_path(source, table, y, root)
        if not p.exists():
            if strict:
                raise FileNotFoundError(p)
            log.debug("%s %s %d not available", source, table, y)
            continue
        lf = pl.scan_parquet(p)
        have = lf.collect_schema().names()
        if columns is not None:
            missing = [c for c in columns if c not in have]
            if missing and strict:
                raise KeyError(f"{source}.{table}.{y} lacks {missing}")
            sel = [pl.col(c) for c in columns if c in have]
            sel += [pl.lit(None).alias(c) for c in missing if c != "YEAR"]
            lf = lf.select(sel)
        df = lf.collect()
        if "YEAR" in df.columns:
            df = df.with_columns(pl.col("YEAR").cast(pl.Int64))
            n_bad = df["YEAR"].null_count() + int((df["YEAR"] != y).sum())
            if n_bad:
                log.warning("%s.%s %d: %d rows with YEAR != file year", source, table, y, n_bad)
        else:
            df = df.with_columns(pl.lit(y, dtype=pl.Int64).alias("YEAR"))
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"no {source}.{table} data for years {years}")
    return pl.concat(frames, how="diagonal_relaxed")
