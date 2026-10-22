"""Harmonisation mappings (synthetic) and processed-dataset reconciliation (real data)."""

from __future__ import annotations

import polars as pl
import pytest

from nhtsa_stats import config
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.processing.features import any_flag, body_flag


def _apply(expr: pl.Expr, **cols) -> list:
    return pl.DataFrame(cols).select(expr.alias("out"))["out"].to_list()


def test_restraint_break_2016_none_code():
    # 2016 used 7 = 'None Used'; 2017+ use 20 = 'None Used/Not Applicable'.
    assert _apply(h.restraint_use(), REST_USE=[7, 20, 3, 99, 96, 17]) == [
        "none",
        "none",
        "belted",
        "unknown",
        "not_applicable",
        "not_applicable",
    ]


def test_helmet_moves_from_rest_use_to_helm_use_in_2019():
    out = _apply(
        h.helmet_use(),
        YEAR=[2017, 2017, 2018, 2019, 2019, 2019, 2017],
        REST_USE=[5, 17, 3, 20, 20, 20, 99],
        HELM_USE=[None, None, None, 5, 17, 99, None],
        # motorcycles, except the last row: a car occupant with unknown restraint (2017)
        BODY_TYP=[80, 80, 80, 80, 80, 80, 4],
    )
    assert out == [
        "helmet",
        "none",
        "not_applicable",
        "helmet",
        "none",
        "unknown",
        "not_applicable",
    ]


def test_restraint_kept_when_seat_unknown():
    out = _apply(
        h.restraint_in_belted_seat(),
        REST_USE=[3, 20, 3, 3],
        BODY_TYP=[4, 4, 4, 80],
        SEAT_POS=[99, 98, 55, 11],
    )
    assert out == ["belted", "none", "not_applicable", "not_applicable"]


def test_unknown_is_never_no():
    # SPEEDREL 8 (no driver present / unknown if driver present) is unknown, not "no"
    assert _apply(h.speeding_related(), SPEEDREL=[0, 3, 9, 8]) == [0, 1, None, None]
    assert _apply(h.police_reported("DRINKING"), DRINKING=[0, 1, 8, 9]) == [0, 1, None, None]
    assert _apply(h.fatal("INJ_SEV"), INJ_SEV=[4, 3, 5, 6, 9]) == [1, 0, None, None, None]


def test_body_groups_absorb_2017_pickup_merge():
    assert _apply(h.body_group(), BODY_TYP=[30, 31, 34, 14, 80, 66, 99]) == [
        "pickup",
        "pickup",
        "pickup",
        "suv",
        "motorcycle",
        "medium_heavy_truck",
        "unknown",
    ]


def test_unknown_body_codes_stay_unknown():
    assert _apply(h.body_group(), BODY_TYP=[48, 49, 73, 79, 78, 98]) == [
        "light_truck_other",
        "light_unknown_type",
        "truck_unknown_type",
        "truck_unknown_type",
        "medium_heavy_truck",
        "unknown",
    ]


def test_body_flag_is_tri_state():
    df = pl.DataFrame(
        {
            "g": [1, 1, 2, 2, 3, 3, 4],
            "body": ["car", "motorcycle", "car", "truck_unknown_type", "car", "unknown", "car"],
        }
    )
    out = df.group_by("g", maintain_order=True).agg(
        body_flag(["motorcycle"], h.BODY_UNKNOWN_FOR["motorcycle"]).alias("m"),
        body_flag(["medium_heavy_truck"], h.BODY_UNKNOWN_FOR["heavy"]).alias("h"),
    )
    assert out["m"].to_list() == [1, 0, None, 0]
    assert out["h"].to_list() == [0, None, None, 0]


def test_tri_state_any_flag():
    df = pl.DataFrame({"g": [1, 1, 2, 2, 3, 3], "x": [0, 1, 0, 0, 0, None]})
    out = df.group_by("g", maintain_order=True).agg(any_flag("x"))["x"].to_list()
    assert out == [1, 0, None]


def test_leakage_registry_blocks_post_crash():
    with pytest.raises(ValueError, match="ejected"):
        h.assert_no_leakage(["light", "ejected"])
    with pytest.raises(ValueError, match="hit_and_run"):
        h.assert_no_leakage(["light", "hit_and_run"])
    with pytest.raises(ValueError, match="unregistered_thing"):
        h.assert_no_leakage(["unregistered_thing"])
    h.assert_no_leakage(["light", "speeding", "crash_type"])


# ---------------------------------------------------------------------------- real data
@pytest.mark.processed
def test_crss_crash_reconciles_with_raw_accident():
    from nhtsa_stats.ingestion.cache import load_table

    raw = load_table("CRSS", "accident", columns=["CASENUM", "MAX_SEV"])
    proc = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet",
        columns=["case_id", "fatal", "fatal_cc", "MAX_SEV", "MAXSEV_IM", "n_sev_unknown"],
    )
    assert proc.height == raw.height
    assert proc["case_id"].n_unique() == proc.height
    # primary outcome: imputed severity; null exactly when MAXSEV_IM is 5, 6 or 8
    assert proc.filter(pl.col("fatal").is_null())["MAXSEV_IM"].is_in([5, 6, 8]).all()
    assert proc.filter(pl.col("MAXSEV_IM") == 4)["fatal"].eq(1).all()
    # complete-case sensitivity: never 'not fatal' when a person's severity is unknown
    assert proc.filter(pl.col("MAX_SEV") == 4)["fatal_cc"].eq(1).all()
    assert proc.filter(pl.col("fatal_cc") == 0)["n_sev_unknown"].eq(0).all()


@pytest.mark.processed
def test_crss_imputed_fatal_total_matches_fars():
    """CRSS weights are calibrated to FARS through MAXSEV_IM (docs/audit/crss_survey_design.md)."""
    crss = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet", columns=["YEAR", "WEIGHT", "fatal"]
    )
    fars = pl.read_parquet(config.PROCESSED_DIR / "fars_crash.parquet", columns=["YEAR"])
    w = crss.group_by("YEAR").agg((pl.col("WEIGHT") * (pl.col("fatal") == 1)).sum().alias("w"))
    both = w.join(fars.group_by("YEAR").len(), on="YEAR")
    assert both.height == len(config.YEARS)
    assert ((both["w"] / both["len"] - 1).abs() < 0.015).all()


@pytest.mark.processed
def test_fars_crash_reconciles_with_raw_accident():
    from nhtsa_stats.ingestion.cache import load_table

    raw = load_table("FARS", "accident", columns=["ST_CASE", "FATALS"])
    proc = pl.read_parquet(
        config.PROCESSED_DIR / "fars_crash.parquet",
        columns=["YEAR", "case_id", "FATALS", "n_killed"],
    )
    assert proc.height == raw.height
    assert proc["FATALS"].sum() == raw["FATALS"].sum()
    assert (proc["FATALS"] == proc["n_killed"]).all()


@pytest.mark.processed
def test_person_files_keep_one_row_per_person():
    for name in ("crss_person", "fars_person"):
        df = pl.read_parquet(
            config.PROCESSED_DIR / f"{name}.parquet",
            columns=["YEAR", "case_id", "VEH_NO", "PER_NO"],
        )
        assert df.select(["YEAR", "case_id", "VEH_NO", "PER_NO"]).n_unique() == df.height, name


@pytest.mark.processed
def test_tri_state_columns_are_tri_state():
    df = pl.read_parquet(config.PROCESSED_DIR / "crss_crash.parquet")
    for col in (
        "speeding",
        "alcohol",
        "alcohol_im",
        "drugs",
        "distracted",
        "young_driver",
        "dark",
        "night",
    ):
        assert set(df[col].drop_nulls().unique().to_list()) <= {0, 1}, col


def test_restraint_not_applicable_outside_belted_seats():
    out = _apply(
        h.restraint_in_belted_seat(),
        REST_USE=[20, 20, 20, 3, 20],
        BODY_TYP=[4, 80, 50, 14, 34],
        SEAT_POS=[11, 11, 21, 13, 52],
    )
    # car driver unbelted; motorcyclist (2019+ code 20) n/a; bus 2nd row unbelted; SUV belted; pickup bed n/a
    assert out == ["none", "not_applicable", "none", "belted", "not_applicable"]
