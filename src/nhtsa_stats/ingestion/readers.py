"""Read individual CSV members of an archive into typed Polars frames.

All columns are first read as text so that nothing is lost to type inference, then converted
column-by-column:

* ``<VAR>NAME`` columns whose stem ``<VAR>`` is also present are value labels and stay text;
* columns whose non-null values are all integers become ``Int64`` -- unless any value carries
  a leading zero (e.g. railway-crossing identifiers such as ``0000000``), in which case the
  column stays text so the identifier is not altered;
* columns whose non-null values are all decimal numbers become ``Float64``;
* everything else stays text.

Member names differ in case and directory prefix between years (``ACCIDENT.CSV``,
``FARS2024NationalCSV/accident.csv``) and the 2019 CRSS crash-event table is called
``cevents``; :func:`normalise_table_name` maps them all to one canonical lower-case name.
"""

from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path

import polars as pl

log = logging.getLogger(__name__)

TABLE_ALIASES = {"cevents": "cevent"}
INT_RE = r"^-?\d+$"
FLOAT_RE = r"^-?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$"


def normalise_table_name(member: str) -> str:
    stem = Path(member).name.rsplit(".", 1)[0].lower()
    return TABLE_ALIASES.get(stem, stem)


def table_members(zip_path: Path) -> dict[str, str]:
    """Map canonical table name -> member name for every CSV in the archive."""
    with zipfile.ZipFile(zip_path) as zf:
        out: dict[str, str] = {}
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".csv"):
                continue
            name = normalise_table_name(info.filename)
            if name in out:
                raise ValueError(f"{zip_path.name}: duplicate table {name}")
            out[name] = info.filename
    return out


def decode_bytes(raw: bytes) -> tuple[str, str]:
    """Decode CSV bytes, preferring UTF-8 and falling back to Windows-1252."""
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", raw, 0, 1, "undecodable")  # pragma: no cover


def label_columns(columns: list[str]) -> set[str]:
    cols = set(columns)
    return {c for c in columns if c.endswith("NAME") and c[:-4] in cols}


def _convert_types(df: pl.DataFrame) -> pl.DataFrame:
    labels = label_columns(df.columns)
    exprs = []
    for col in df.columns:
        s = df[col]
        if col in labels:
            continue
        nn = s.drop_nulls().str.strip_chars()
        if nn.len() == 0:
            continue
        if nn.str.contains(INT_RE).all():
            has_leading_zero = nn.str.contains(r"^-?0\d").any()
            if not has_leading_zero:
                exprs.append(pl.col(col).str.strip_chars().cast(pl.Int64))
            continue
        if nn.str.contains(FLOAT_RE).all():
            exprs.append(pl.col(col).str.strip_chars().cast(pl.Float64))
    return df.with_columns(exprs) if exprs else df


def read_member(zip_path: Path, member: str, typed: bool = True) -> tuple[pl.DataFrame, dict]:
    """Read one CSV member; return the frame and a small provenance record."""
    with zipfile.ZipFile(zip_path) as zf:
        raw = zf.read(member)
    text, encoding = decode_bytes(raw)
    df = pl.read_csv(
        text.encode("utf-8"),
        infer_schema=False,
        null_values=[""],
        quote_char='"',
    )
    df = df.rename({c: re.sub(r"\s+", "", c).upper() for c in df.columns})
    if typed:
        df = _convert_types(df)
    meta = {
        "member": member,
        "encoding": encoding,
        "bytes": len(raw),
        "rows": df.height,
        "columns": df.width,
    }
    return df, meta
