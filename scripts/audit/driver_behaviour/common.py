"""Shared helpers for the driver-behaviour audit (scratch; not part of the package)."""
from __future__ import annotations

import os
import re

os.environ.setdefault("POLARS_MAX_THREADS", "2")
import polars as pl  # noqa: E402

from nhtsa_stats.ingestion.cache import load_table  # noqa: E402

REPO = "/home/user/nhtsa-stats-US"
OUT = "outputs/cache/audit/out"
YEARS = list(range(2016, 2025))


def norm(s: str | None) -> str:
    if s is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def codebook() -> pl.DataFrame:
    return pl.read_csv(
        f"{REPO}/outputs/audit/codebook.csv",
        schema_overrides={"code": pl.Utf8, "label": pl.Utf8},
    )


def keys(src: str) -> list[str]:
    return ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]


def lt(src, table, cols, years=None):
    return load_table(src, table, years=years, columns=cols)
