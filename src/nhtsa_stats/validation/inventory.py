"""Machine-readable inventory of every table in every archive.

Produces (under ``outputs/audit``):

* ``archive_inventory.csv`` -- one row per archive: source, year, kind, bytes, SHA-256,
  LFS-pointer match, member count;
* ``table_inventory.csv`` -- one row per (source, year, table): rows, columns, encoding,
  candidate key, key uniqueness, exact duplicate rows;
* ``column_inventory.csv`` -- one row per column: dtype, nulls, distinct values, min/max,
  whether it is a value-label column;
* ``codebook.csv`` -- every (code, label) pair harvested from the ``<VAR>NAME`` label columns
  shipped inside the CSVs, with frequencies (variables with more than ``MAX_CODES`` distinct
  codes, e.g. city names, are summarised but not enumerated);
* ``variable_availability.csv`` -- variable x source-year presence matrix.

The codebook is the project's primary source of variable definitions: the archives contain
no PDF manuals, so value meanings are taken from these embedded labels (see
docs/data_dictionary.md for how unlabelled years and auxiliary files are handled).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import polars as pl

from nhtsa_stats import config
from nhtsa_stats.ingestion.readers import label_columns

log = logging.getLogger(__name__)

MAX_CODES = 400

# Record identifiers, from the most to the least specific; the inventory reports the
# shortest prefix that is unique in each table.
CASE_ID = {"FARS": "ST_CASE", "CRSS": "CASENUM"}
KEY_CANDIDATES = ["VEH_NO", "PER_NO"]


def _candidate_key(df: pl.DataFrame, source: str) -> tuple[list[str], bool]:
    """Shortest identifying key: case id, then vehicle/person numbers, then one more column.

    Multi-row tables (one row per crash event, driver factor, drug result, ...) are keyed by
    the record identifiers plus the coded value or sequence number itself; the extra column
    is the first non-label column that makes the key unique.
    """
    case = CASE_ID[source]
    if case not in df.columns:
        return [], False
    keys = [case]
    if df.select(keys).is_unique().all():
        return keys, True
    for k in KEY_CANDIDATES:
        if k in df.columns:
            keys.append(k)
            if df.select(keys).is_unique().all():
                return keys, True
    labels = label_columns(df.columns)
    for k in df.columns:
        if k in keys or k in labels or k == "YEAR":
            continue
        trial = [*keys, k]
        if df.select(trial).is_unique().all():
            return trial, True
    return keys, False


def profile_table(df: pl.DataFrame, source: str) -> tuple[dict, list[dict], list[dict]]:
    labels = label_columns(df.columns)
    key, unique = _candidate_key(df, source)
    table_rec = {
        "rows": df.height,
        "columns": df.width,
        "label_columns": len(labels),
        "candidate_key": "+".join(key),
        "key_unique": unique,
        "duplicate_rows": int(df.height - df.unique().height),
    }
    col_recs: list[dict] = []
    code_recs: list[dict] = []
    for col in df.columns:
        s = df[col]
        rec = {
            "column": col,
            "dtype": str(s.dtype),
            "is_label": col in labels,
            "n_null": s.null_count(),
            "pct_null": round(100 * s.null_count() / max(df.height, 1), 3),
            "n_distinct": s.n_unique(),
            "min": None,
            "max": None,
        }
        if s.dtype.is_numeric() and s.null_count() < df.height:
            rec["min"], rec["max"] = str(s.min()), str(s.max())
        col_recs.append(rec)
        if col in labels:
            continue
        lab = f"{col}NAME"
        if lab in labels:
            pairs = df.group_by([col, lab]).len().sort(col)
            if pairs.height > MAX_CODES:
                code_recs.append(
                    {"variable": col, "code": None, "label": f"<{pairs.height} codes>", "n": None}
                )
                continue
            for code, label, n in pairs.iter_rows():
                code_recs.append(
                    {
                        "variable": col,
                        "code": None if code is None else str(code),
                        "label": label,
                        "n": n,
                    }
                )
    return table_rec, col_recs, code_recs


def build_inventory(out_dir: Path | None = None) -> dict[str, pl.DataFrame]:
    out_dir = out_dir or config.AUDIT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((config.INTERIM_DIR / "manifest.json").read_text())

    arch_rows, table_rows, col_rows, code_rows = [], [], [], []
    for key in sorted(manifest):
        rec = manifest[key]
        arch_rows.append(
            {
                k: rec[k]
                for k in (
                    "archive",
                    "source",
                    "year",
                    "kind",
                    "size_bytes",
                    "sha256",
                    "lfs_oid_match",
                    "n_members",
                )
            }
        )
        for table, meta in sorted(rec["tables"].items()):
            df = pl.read_parquet(config.INTERIM_DIR / meta["parquet"])
            t, cols, codes = profile_table(df, rec["source"])
            base = {
                "source": rec["source"],
                "year": rec["year"],
                "kind": rec["kind"],
                "table": table,
            }
            table_rows.append({**base, "member": meta["member"], "encoding": meta["encoding"], **t})
            col_rows += [{**base, **c} for c in cols]
            code_rows += [{**base, **c} for c in codes]
        log.info("profiled %s", key)

    archives = pl.DataFrame(arch_rows)
    tables = pl.DataFrame(table_rows)
    columns = pl.DataFrame(col_rows, infer_schema_length=None)
    codebook = pl.DataFrame(code_rows, infer_schema_length=None)
    availability = (
        columns.filter(~pl.col("is_label"))
        .with_columns((pl.col("source") + "_" + pl.col("year").cast(pl.Utf8)).alias("sy"))
        .group_by(["source", "table", "column", "sy"])
        .agg(pl.lit(1).alias("present"))
        .pivot(on="sy", index=["source", "table", "column"], values="present")
        .fill_null(0)
        .sort(["source", "table", "column"])
    )
    sy_cols = sorted(c for c in availability.columns if c not in ("source", "table", "column"))
    availability = availability.select(["source", "table", "column", *sy_cols])

    archives.write_csv(out_dir / "archive_inventory.csv")
    tables.write_csv(out_dir / "table_inventory.csv")
    columns.write_csv(out_dir / "column_inventory.csv")
    codebook.write_csv(out_dir / "codebook.csv")
    availability.write_csv(out_dir / "variable_availability.csv")
    return {
        "archives": archives,
        "tables": tables,
        "columns": columns,
        "codebook": codebook,
        "availability": availability,
    }
