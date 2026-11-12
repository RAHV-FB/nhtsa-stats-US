"""Observed segment baseline (RQ10): synthetic unit tests and a real-data smoke test.

Synthetic numbers here are software fixtures only -- never findings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats import config
from nhtsa_stats.simulation import baseline as e

ALL_SEGS = e.PARTITION_SEGMENTS


def fs(*s: str) -> frozenset[str]:
    return frozenset(s)


def toy_baseline() -> e.EmpiricalBaseline:
    """1000 deaths/yr: speeding 200 (exceeded 50), alcohol 210, speeding&alcohol 50,
    unrestrained 50 (10 also alcohol), drugs 0."""
    deaths = e.Partition(
        "deaths",
        ALL_SEGS,
        {
            fs(): 600.0,
            fs("speeding"): 100.0,
            fs("speeding", "speeding_exceeded_limit"): 50.0,
            fs("alcohol"): 150.0,
            fs("speeding", "alcohol"): 50.0,
            fs("unrestrained_lpv"): 40.0,
            fs("alcohol", "unrestrained_lpv"): 10.0,
        },
        "observed",
        "toy",
    )
    fatal = e.Partition(
        "fatal_crashes",
        e.CRASH_SEGMENTS,
        {
            fs(): 550.0,
            fs("speeding"): 90.0,
            fs("speeding", "speeding_exceeded_limit"): 45.0,
            fs("alcohol"): 140.0,
            fs("speeding", "alcohol"): 45.0,
        },
        "observed",
        "toy",
    )
    ka_part = e.Partition(
        "ka_crashes",
        e.CRASH_SEGMENTS,
        {
            fs(): 9000.0,
            fs("speeding"): 500.0,
            fs("speeding", "speeding_exceeded_limit"): 200.0,
            fs("alcohol"): 300.0,
            fs("speeding", "alcohol"): 100.0,
        },
        "estimated",
        "toy",
    )
    assoc = {
        "severity.fatal_adj_rr.speeding": e.Quantity(
            "severity.fatal_adj_rr.speeding", 2.0, "adjusted_association", "toy", "RR", 1.5, 2.5
        )
    }
    q = {
        "crss.ka_crashes_per_year": e.Quantity(
            "crss.ka_crashes_per_year", 10100.0, "estimated", "toy", "KA"
        )
    }
    return e.EmpiricalBaseline((2022, 2024), q, deaths, fatal, ka_part, associations=assoc)


# --------------------------------------------------------------------------------------
# Partitions and baseline construction
# --------------------------------------------------------------------------------------
def test_partition_totals_overlap_union():
    b = toy_baseline()
    assert b.total_deaths() == 1000
    assert b.segment_deaths("speeding") == 200
    assert b.segment_deaths("speeding_exceeded_limit") == 50
    assert b.segment_deaths("alcohol") == 210
    assert b.segment_deaths("drugs") == 0
    assert b.segment_deaths(e.ALL) == 1000
    assert b.deaths.overlap("speeding", "alcohol") == 50
    assert b.deaths.union("speeding", "alcohol") == 360
    assert b.segment_fatal_crashes("unrestrained_lpv") is None
    assert b.segment_ka_crashes("speeding") == 800
    with pytest.raises(KeyError):
        b.deaths.segment_total("helmets")


def _synthetic_fars() -> tuple[pd.DataFrame, pd.DataFrame]:
    crash = pd.DataFrame(
        {
            "YEAR": [2022, 2022, 2023, 2023, 2024, 2021],
            "case_id": [1, 2, 1, 2, 1, 1],
            "FATALS": [2, 1, 1, 1, 1, 1],
            "speeding": [1.0, np.nan, 0.0, 1.0, 0.0, 1.0],
            "speeding_type": [e.EXCEEDED, "unknown", "no", "too_fast_for_conditions", "no", "no"],
            "drugs": [np.nan, 0.0, 1.0, 0.0, np.nan, 1.0],
            "driver_bac08_prob": [0.3, 1.0, 0.0, np.nan, 0.5, 1.0],
        }
    )
    person = pd.DataFrame(
        {
            "YEAR": [2022, 2022, 2022, 2022, 2023, 2023, 2024, 2024, 2021],
            "case_id": [1, 1, 1, 2, 1, 2, 1, 1, 1],
            "killed": [1, 1, 0, 1, 1, 1, 1, 0, 1],
            "ptype": [
                "driver",
                "passenger",
                "driver",
                "pedestrian",
                "driver",
                "driver",
                "driver",
                "driver",
                "driver",
            ],
            "body": ["car", "suv", "car", None, "car", "motorcycle", "pickup", "car", "car"],
            "seat": [
                "front_left",
                "second_row",
                "front_left",
                "unknown",
                "front_left",
                "front_left",
                "front_left",
                "front_left",
                "front_left",
            ],
            "age": [30, 10, 40, 50, 25, 33, 60, 20, 30],
            "restraint": [
                "none",
                "none",
                "none",
                "not_applicable",
                "unknown",
                "not_applicable",
                "belted",
                "none",
                "none",
            ],
        }
    )
    return crash, person


def test_baseline_from_frames_fars_counts_and_unknowns():
    crash, person = _synthetic_fars()
    b = e.baseline_from_frames(crash, person, (2022, 2024))
    # window has 6 deaths over 3 years (2021 excluded)
    assert b.total_deaths() == pytest.approx(6 / 3)
    q = b.quantities
    assert q["fars.deaths_per_year"].value == pytest.approx(2.0)
    assert q["fars.fatal_crashes_per_year"].value == pytest.approx(5 / 3)
    # speeding: crash 2022/1 (2 deaths) and 2023/2 (1 death); unknown (NaN) not counted as yes
    assert b.segment_deaths("speeding") == pytest.approx(3 / 3)
    assert q["fars.deaths_per_year.speeding.status_unknown"].value == pytest.approx(1 / 3)
    assert b.segment_deaths("speeding_exceeded_limit") == pytest.approx(2 / 3)
    # alcohol: expected value 2*0.3 + 1*1.0 + 1*0 + 1*0 (NaN -> no driver) + 1*0.5
    assert b.segment_deaths("alcohol") == pytest.approx((0.6 + 1.0 + 0.5) / 3)
    assert b.segment_fatal_crashes("alcohol") == pytest.approx((0.3 + 1.0 + 0.5) / 3)
    assert b.segment_deaths("drugs") == pytest.approx(1 / 3)
    assert q["fars.deaths_per_year.drugs.status_unknown"].value == pytest.approx(3 / 3)
    # unrestrained LPV: only the 30-year-old front-left driver (the 10-year-old is below the
    # belt-analysis age); the 'unknown' restraint driver is reported separately
    assert b.segment_deaths("unrestrained_lpv") == pytest.approx(1 / 3)
    assert q["fars.deaths_per_year.unrestrained_lpv.status_unknown"].value == pytest.approx(1 / 3)
    # partition reproduces the total and the expected speeding & alcohol overlap
    assert b.deaths.total() == pytest.approx(b.total_deaths())
    assert b.deaths.overlap("speeding", "alcohol") == pytest.approx(0.6 / 3)
    assert set(b.annual["YEAR"]) == {2022, 2023, 2024}
    # FARS counts are observed; alcohol counts are expectations over NHTSA's BAC imputations.
    assert all(
        qq.kind == ("observed_x_imputation" if "alcohol" in k else "observed")
        for k, qq in q.items()
        if k.startswith("fars.")
    )


def test_baseline_rejects_window_outside_data():
    crash, person = _synthetic_fars()
    with pytest.raises(ValueError):
        e.baseline_from_frames(crash, person, (2014, 2016))
    with pytest.raises(ValueError):
        e.baseline_from_frames(crash, person, (2024, 2022))


def _synthetic_crss(n: int = 3000, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "YEAR": rng.choice([2021, 2022, 2023, 2024], n),
            "WEIGHT": rng.uniform(5, 50, n),
            "PSUSTRAT": rng.integers(0, 4, n),
            "PSU_VAR": rng.integers(0, 3, n),
            "speeding": rng.choice([0.0, 1.0, np.nan], n, p=[0.8, 0.15, 0.05]),
            "speeding_type": rng.choice(["no", e.EXCEEDED, "unknown"], n),
            "alcohol_im": rng.choice([0.0, 1.0], n, p=[0.9, 0.1]),
            "drugs": rng.choice([0.0, 1.0, np.nan], n),
            "fatal": rng.choice([0.0, 1.0], n, p=[0.95, 0.05]),
            "ka": rng.choice([0.0, 1.0, np.nan], n, p=[0.8, 0.18, 0.02]),
            "fatal_cc": 0.0,  # complete-case columns: sensitivity only, must NOT be used
            "ka_cc": 0.0,
        }
    )


def test_crss_totals_partition_and_outcome_resolution():
    crash, person = _synthetic_fars()
    crss = _synthetic_crss(n=5000)
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=crss)
    win = crss["YEAR"].isin([2022, 2023, 2024])
    w = crss["WEIGHT"].where(win, 0.0)
    ka = (crss["ka"] == 1).astype(float)
    q = b.quantities
    assert q["crss.crashes_per_year"].value == pytest.approx(w.sum() / 3)
    assert q["crss.ka_crashes_per_year"].value == pytest.approx((w * ka).sum() / 3)
    sp = (crss["speeding"] == 1).astype(float)
    assert q["crss.ka_crashes_per_year.speeding"].value == pytest.approx((w * ka * sp).sum() / 3)
    assert q["crss.crashes_per_year"].kind == "estimated"
    lo, hi = q["crss.crashes_per_year"].low, q["crss.crashes_per_year"].high
    assert lo < q["crss.crashes_per_year"].value < hi
    # the KA partition sums to the KA total and matches each segment total
    assert b.ka_crashes.total() == pytest.approx(q["crss.ka_crashes_per_year"].value)
    assert b.segment_ka_crashes("speeding") == pytest.approx(
        q["crss.ka_crashes_per_year.speeding"].value
    )


def test_crss_partition_cells_have_design_se_and_flags():
    from nhtsa_stats.analysis.survey import SurveyDesign, svy_total

    crash, person = _synthetic_fars()
    crss = _synthetic_crss(n=4000)
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=crss)
    design = SurveyDesign.from_frame(crss)
    win = crss["YEAR"].isin([2022, 2023, 2024]).to_numpy()
    ka = (crss["ka"] == 1).to_numpy(float)
    cm = e.crash_membership(crss, "CRSS")
    only_speeding = (
        cm["speeding"]
        * (1 - cm["speeding_exceeded_limit"])
        * (1 - cm["alcohol"])
        * (1 - cm["drugs"])
    ).to_numpy()
    est = svy_total(design, ka * only_speeding, win)
    cell = fs("speeding")
    assert b.ka_crashes.cells[cell] == pytest.approx(est.estimate / 3)
    assert b.ka_crashes.se[cell] == pytest.approx(est.se / 3)
    fr = b.partitions_frame().set_index(["measure", "cell"])
    small = [c for c, n in b.ka_crashes.n.items() if 0 < n < config.MIN_CELL_N]
    empty = [c for c, n in b.ka_crashes.n.items() if n == 0]
    assert small and empty, "fixture should contain small and empty KA cells"
    for c in small:
        row = fr.loc[("ka_crashes", e._key(c))]
        assert row["flag"] == "suppressed" and np.isnan(row["per_year"])
    for c in empty:  # e.g. limit-exceeding but not speeding: structurally empty
        row = fr.loc[("ka_crashes", e._key(c))]
        assert row["flag"] == "no_sample_records" and row["per_year"] == 0
    # census (FARS) cells are never flagged; the JSON round trip keeps the SEs
    assert (fr.loc["deaths", "flag"] == "").all()
    b2 = e.EmpiricalBaseline.from_dict(b.to_dict())
    assert b2.ka_crashes.se[cell] == pytest.approx(b.ka_crashes.se[cell])


def test_crss_small_cells_are_suppressed():
    crash, person = _synthetic_fars()
    crss = _synthetic_crss(n=200)
    crss["drugs"] = 0.0
    crss.loc[crss.index[:5], "drugs"] = 1.0
    crss.loc[crss.index[:5], "YEAR"] = 2022
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=crss)
    qd = b.quantities["crss.crashes_per_year.drugs"]
    assert qd.flag == "suppressed" and qd.value is None and qd.n == 5


def test_crss_outcome_column_requires_imputed_outcome():
    assert e.crss_outcome_column(["fatal", "fatal_cc"], "fatal") == "fatal"
    with pytest.raises(e.MissingInputError):
        e.crss_outcome_column(["fatal_cc"], "fatal")


def test_baseline_roundtrip_dict():
    crash, person = _synthetic_fars()
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=_synthetic_crss())
    b2 = e.EmpiricalBaseline.from_dict(b.to_dict())
    assert b2.total_deaths() == pytest.approx(b.total_deaths())
    assert b2.segment_ka_crashes("alcohol") == pytest.approx(b.segment_ka_crashes("alcohol"))
    assert b2.quantities.keys() == b.quantities.keys()


def _write_csv(df: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def test_read_associations_missing_and_present(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path)
    with pytest.raises(e.MissingInputError, match="nhtsa analyze severity"):
        e.read_associations(require_severity=True)
    out, notes = e.read_associations(require_severity=False)
    assert out == {} and any("not found" in n for n in notes)
    _write_csv(
        pd.DataFrame(
            {
                "factor": ["speeding", "alcohol_im"],
                "level": ["yes", "yes"],
                "n": [100, 50],
                "A_adj_rr": [1.8, 4.4],
                "A_adj_rr_low": [1.5, 3.7],
                "A_adj_rr_high": [2.2, 5.3],
            }
        ),
        tmp_path / "severity" / "fatal_crude_vs_adjusted.csv",
    )
    _write_csv(
        pd.DataFrame(
            {
                "estimand": [
                    e.BELT_PRIMARY,
                    e.BELT_PRIMARY + "_misreport_f10",
                    "within_vehicle_or_killed_unbelted_vs_belted",
                ],
                "estimate": [0.66, 0.38, 5.1],
                "low": [0.65, 0.36, 4.8],
                "high": [0.67, 0.39, 5.3],
                "method": ["dpc", "dpc", "clogit"],
                "n_vehicles": [10, 10, 10],
            }
        ),
        tmp_path / "matched" / "belt_effect.csv",
    )
    out, _ = e.read_associations()
    assert out["severity.fatal_adj_rr.speeding"].value == 1.8
    assert out["severity.fatal_adj_rr.alcohol"].high == 5.3
    assert out["severity.fatal_adj_rr.alcohol"].kind == "adjusted_association"
    assert out["belt.fatality_reduction"].value == 0.66
    assert out["belt.fatality_reduction.misreport_f10"].value == 0.38
    assert not any("within_vehicle" in k for k in out)
    # tables written after the processed data are not flagged
    assert all(q.flag == "" for q in out.values())


def test_associations_older_than_processed_data_are_flagged(tmp_path, monkeypatch):
    import os

    tables, processed = tmp_path / "tables", tmp_path / "processed"
    monkeypatch.setattr(config, "TABLES_DIR", tables)
    monkeypatch.setattr(config, "PROCESSED_DIR", processed)
    sev = tables / "severity" / "fatal_crude_vs_adjusted.csv"
    _write_csv(
        pd.DataFrame(
            {
                "factor": ["speeding"],
                "level": ["yes"],
                "n": [100],
                "A_adj_rr": [1.8],
                "A_adj_rr_low": [1.5],
                "A_adj_rr_high": [2.2],
            }
        ),
        sev,
    )
    processed.mkdir()
    for name in ("crss_crash", "fars_person"):
        (processed / f"{name}.parquet").write_bytes(b"")
    os.utime(sev, (1_000_000, 1_000_000))  # upstream table older than the data rebuild
    out, notes = e.read_associations()
    assert out["severity.fatal_adj_rr.speeding"].flag == e.STALE
    assert any(n.startswith("STALE") and "severity" in n for n in notes)
    os.utime(sev, None)  # re-written after the rebuild: no flag
    out, notes = e.read_associations()
    assert out["severity.fatal_adj_rr.speeding"].flag == ""
    assert not any(n.startswith("STALE") for n in notes)


def test_lpv_definition_matches_project_and_belt_population():
    from nhtsa_stats.processing.harmonize import LPV_BODY_GROUPS

    assert set(e.LPV_BODIES) == set(LPV_BODY_GROUPS)
    person = pd.DataFrame(
        {
            "ptype": ["driver", "passenger", "driver", "driver", "passenger"],
            "body": ["light_unknown_type", "car", "truck_unknown_type", "car", "car"],
            "seat": ["front_left", "third_row_plus", "front_left", "front_left", "second_row"],
            "age": [40, 40, 40, np.nan, 12],
            "age_im": [40, 40, 40, 35, 12],
            "restraint": ["none"] * 5,
        }
    )
    assert e.unrestrained_lpv_mask(person).tolist() == [True, False, False, False, False]
    # CRSS uses NHTSA's imputed age, so the record with unrecorded age is counted there
    assert e.unrestrained_lpv_mask(person, "age_im").tolist() == [True, False, False, True, False]


def test_crss_person_baseline_uses_imputed_age():
    rng = np.random.default_rng(5)
    n = 400
    crss_p = pd.DataFrame(
        {
            "YEAR": rng.choice([2022, 2023, 2024], n),
            "WEIGHT": rng.uniform(5, 50, n),
            "PSUSTRAT": rng.integers(0, 4, n),
            "PSU_VAR": rng.integers(0, 3, n),
            "ptype": "driver",
            "body": "car",
            "seat": "front_left",
            "age": np.where(np.arange(n) < 100, np.nan, 30.0),
            "age_im": 30.0,
            "restraint": "none",
            "killed_or_serious": rng.choice([0.0, 1.0], n),
            "killed_or_serious_cc": 0.0,
        }
    )
    q = e._crss_person_baseline(crss_p, (2022, 2023, 2024))
    assert q["crss.persons_per_year.unrestrained_lpv"].value == pytest.approx(
        crss_p["WEIGHT"].sum() / 3
    )
    assert q["crss.persons_per_year.unrestrained_lpv"].n == n


# --------------------------------------------------------------------------------------
# Segment overlap and the field inventory
# --------------------------------------------------------------------------------------
def test_segment_overlap_table():
    b = toy_baseline()
    ov = e.overlap_table(b).set_index(["segment_a", "segment_b"])
    assert ov.loc[("speeding", "alcohol"), "deaths_both"] == pytest.approx(50.0)
    assert ov.loc[("speeding", "alcohol"), "deaths_either"] == pytest.approx(360.0)
    assert ov.loc[("speeding", "alcohol"), "share_of_a_also_in_b"] == pytest.approx(0.25)


def test_enforcement_field_search(tmp_path):
    inv = pd.DataFrame(
        {
            "source": ["FARS", "FARS", "CRSS", "FARS", "FARS"],
            "year": [2016, 2017, 2016, 2016, 2016],
            "table": ["violatn", "violatn", "vpicdecode", "accident", "accident"],
            "column": ["MVIOLATN", "MVIOLATN", "BASEPRICE", "HOUR", "MVIOLATNNAME"],
        }
    )
    p = tmp_path / "inv.csv"
    inv.to_csv(p, index=False)
    out = e.enforcement_field_search(str(p))
    assert sorted(out["column"]) == ["BASEPRICE", "MVIOLATN"]
    assert not out["measures_intervention_or_cost"].any()
    assert out.set_index("column").loc["MVIOLATN", "last_year"] == 2017
    assert "vehicle" in out.set_index("column").loc["BASEPRICE", "meaning"]


def test_enforcement_field_search_test_fields_and_meanings(tmp_path):
    cols = ["DRUGS", "DRUGSPEC", "DRUGRES1", "ALC_RES", "ALC_DET", "WRK_ZONE", "FIRST_MO", "HOUR"]
    inv = pd.DataFrame(
        {"source": "FARS", "year": 2020, "table": "person", "column": cols},
    )
    p = tmp_path / "inv.csv"
    inv.to_csv(p, index=False)
    out = e.enforcement_field_search(str(p)).set_index("column")
    assert "HOUR" not in out.index and len(out) == len(cols) - 1
    assert "police-reported drug involvement" in out.loc["DRUGS", "meaning"]
    assert "toxicology" in out.loc["DRUGSPEC", "meaning"]
    assert "test result" in out.loc["DRUGRES1", "meaning"]
    assert not out["meaning"].str.contains("unclassified").any()


def test_real_inventory_every_match_is_interpreted():
    p = config.AUDIT_DIR / "column_inventory.csv"
    if not p.exists():
        pytest.skip("column inventory not built")
    out = e.enforcement_field_search()
    assert len(out) > 0
    assert not out["meaning"].str.contains("unclassified").any()
    assert not out["measures_intervention_or_cost"].any()


# --------------------------------------------------------------------------------------
# Real data
# --------------------------------------------------------------------------------------
@pytest.mark.processed
def test_real_baseline_smoke():
    try:
        b = e.build_baseline((2022, 2024))
    except e.MissingInputError:
        b = e.build_baseline((2022, 2024), require_severity=False)
    ann = b.annual
    assert b.total_deaths() == pytest.approx(ann["deaths"].mean())
    assert b.fatal_crashes.total() == pytest.approx(ann["fatal_crashes"].mean())
    assert b.deaths.total() == pytest.approx(b.quantities["fars.deaths_per_year"].value)
    for seg in e.PARTITION_SEGMENTS:
        assert 0 < b.segment_deaths(seg) < b.total_deaths()
    assert b.segment_deaths("speeding_exceeded_limit") <= b.segment_deaths("speeding")
    q = b.quantities
    assert q["crss.ka_crashes_per_year"].value < q["crss.crashes_per_year"].value
    # CRSS imputed fatal-crash estimate is consistent with the FARS census (within its CI)
    f = q["crss.fatal_crashes_per_year"]
    assert f.low <= q["fars.fatal_crashes_per_year"].value <= f.high
