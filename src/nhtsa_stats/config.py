"""Project-wide paths and constants.

Everything that controls *which* data are read and *where* derived files go lives here so
that a rebuild is fully determined by the raw archives plus this module.  Paths can be
redirected with the ``NHTSA_DATA_DIR`` / ``NHTSA_OUTPUT_DIR`` environment variables (used by
tests to point at synthetic fixtures).
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("NHTSA_DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
# Typed per-table Parquet copies of the raw CSVs (one file per source/table/year).
INTERIM_DIR = DATA_DIR / "interim"
# Harmonised analytic datasets built from the interim tables.
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = Path(os.environ.get("NHTSA_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
TABLES_DIR = OUTPUT_DIR / "tables"
FIGURES_DIR = OUTPUT_DIR / "figures"
MODELS_DIR = OUTPUT_DIR / "models"
AUDIT_DIR = OUTPUT_DIR / "audit"

YEARS: tuple[int, ...] = tuple(range(2016, 2025))
SOURCES: tuple[str, ...] = ("FARS", "CRSS")

# Temporal split used by every predictive model (see docs/model_validation.md).
TRAIN_YEARS: tuple[int, ...] = (2016, 2017, 2018, 2019, 2020, 2021)
VALID_YEARS: tuple[int, ...] = (2022,)
TEST_YEARS: tuple[int, ...] = (2023, 2024)

RANDOM_SEED = 20240601

# Minimum unweighted sample size below which a CRSS cell estimate is suppressed, and the
# relative-standard-error threshold above which it is flagged as unstable.
MIN_CELL_N = 30
MAX_RSE = 0.30
