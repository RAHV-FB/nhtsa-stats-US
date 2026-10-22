"""Load the processed analytic datasets in the form the analyses need.

All analysis modules go through these loaders so that population definitions (which rows,
which outcome, how unknowns are coded) are identical everywhere.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import polars as pl

from nhtsa_stats import config
from nhtsa_stats.analysis.survey import SurveyDesign

TRI_STATE = {1: "yes", 0: "no"}


def _read(name: str, columns: Sequence[str] | None = None) -> pl.DataFrame:
    path = config.PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run `nhtsa build` first")
    return pl.read_parquet(path, columns=list(columns) if columns else None)


def tri_state(s: pd.Series) -> pd.Series:
    """0/1/null indicator -> 'no'/'yes'/'unknown' categorical labels."""
    return s.map(TRI_STATE).fillna("unknown").astype(object)


def crss_crash(
    years: Sequence[int] | None = None,
    outcome: str | None = "fatal",
    tri_state_cols: Sequence[str] = (),
) -> tuple[pd.DataFrame, SurveyDesign]:
    """CRSS crash file as pandas plus its survey design.

    Rows with an unknown ``outcome`` (MAXSEV_IM 5/6/8 for 'fatal') are dropped *after* the
    design object is built from the full sample (so domain variance uses every PSU) -- the
    returned design is already subset to the returned rows.
    """
    df = _read("crss_crash").to_pandas()
    if years is not None:
        keep_year = df["YEAR"].isin(list(years)).to_numpy()
    else:
        keep_year = np.ones(len(df), dtype=bool)
    design = SurveyDesign.from_frame(df)
    keep = keep_year.copy()
    if outcome is not None:
        keep &= df[outcome].notna().to_numpy()
    for c in tri_state_cols:
        df[c] = tri_state(df[c])
    out = df.loc[keep].reset_index(drop=True)
    return out, design.subset(keep)


def crss_person(
    years: Sequence[int] | None = None,
    outcome: str | None = "killed",
    occupants_only: bool = True,
    tri_state_cols: Sequence[str] = (),
) -> tuple[pd.DataFrame, SurveyDesign]:
    df = _read("crss_person").to_pandas()
    keep = np.ones(len(df), dtype=bool)
    if years is not None:
        keep &= df["YEAR"].isin(list(years)).to_numpy()
    if occupants_only:
        keep &= df["PER_TYP"].isin([1, 2, 9]).to_numpy()
    design = SurveyDesign.from_frame(df)
    if outcome is not None:
        keep &= df[outcome].notna().to_numpy()
    for c in tri_state_cols:
        df[c] = tri_state(df[c])
    return df.loc[keep].reset_index(drop=True), design.subset(keep)


def fars_crash(years: Sequence[int] | None = None) -> pd.DataFrame:
    df = _read("fars_crash").to_pandas()
    if years is not None:
        df = df[df["YEAR"].isin(list(years))].reset_index(drop=True)
    return df


def fars_person(years: Sequence[int] | None = None) -> pd.DataFrame:
    df = _read("fars_person").to_pandas()
    if years is not None:
        df = df[df["YEAR"].isin(list(years))].reset_index(drop=True)
    return df


def fars_design(df: pd.DataFrame) -> SurveyDesign:
    """Unit weights, single stratum, crash clusters: cluster-robust inference for FARS."""
    cluster = (
        df["YEAR"].astype(np.int64).to_numpy() * 1_000_000
        + df["case_id"].astype(np.int64).to_numpy()
    )
    return SurveyDesign.from_arrays(np.ones(len(df)), None, cluster)
