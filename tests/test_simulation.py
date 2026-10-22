"""Intervention simulation engine (RQ10): synthetic unit tests and a real-data smoke test.

Synthetic numbers here are software fixtures only -- never findings.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats import config
from nhtsa_stats.simulation import engine as e

ALL_SEGS = e.PARTITION_SEGMENTS


def fs(*s: str) -> frozenset[str]:
    return frozenset(s)


def toy_baseline(belt: bool = True, ka: bool = True) -> e.EmpiricalBaseline:
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
    if belt:
        assoc["belt.fatality_reduction"] = e.Quantity(
            "belt.fatality_reduction", 0.6, "adjusted_association", "toy", "share", 0.5, 0.7
        )
    q = {
        "crss.ka_crashes_per_year": e.Quantity(
            "crss.ka_crashes_per_year", 10100.0, "estimated", "toy", "KA"
        )
    }
    return e.EmpiricalBaseline(
        (2022, 2024), q, deaths, fatal, ka_part if ka else None, associations=assoc
    )


def generic(seg: str, rr: float | e.Param, **kw) -> e.GenericIntervention:
    return e.GenericIntervention(seg, relative_reduction_deaths=rr, **kw)


# --------------------------------------------------------------------------------------
# Layer A: partitions and baseline construction
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
    assert all(qq.kind == "observed" for k, qq in q.items() if k.startswith("fars."))


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
            "fatal_im": rng.choice([0.0, 1.0], n, p=[0.95, 0.05]),
            "ka_im": rng.choice([0.0, 1.0, np.nan], n, p=[0.8, 0.18, 0.02]),
            "fatal": 0.0,  # older layout: complete-case column, must NOT be used
            "ka": 0.0,
        }
    )


def test_crss_totals_partition_and_outcome_resolution():
    crash, person = _synthetic_fars()
    crss = _synthetic_crss(n=5000)
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=crss)
    win = crss["YEAR"].isin([2022, 2023, 2024])
    w = crss["WEIGHT"].where(win, 0.0)
    ka = (crss["ka_im"] == 1).astype(float)
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


def test_crss_small_cells_are_suppressed():
    crash, person = _synthetic_fars()
    crss = _synthetic_crss(n=200)
    crss["drugs"] = 0.0
    crss.loc[crss.index[:5], "drugs"] = 1.0
    crss.loc[crss.index[:5], "YEAR"] = 2022
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=crss)
    qd = b.quantities["crss.crashes_per_year.drugs"]
    assert qd.flag == "suppressed" and qd.value is None and qd.n == 5


def test_crss_outcome_column_layouts():
    assert e.crss_outcome_column(["fatal", "fatal_cc"], "fatal") == "fatal"
    assert e.crss_outcome_column(["fatal", "fatal_im"], "fatal") == "fatal_im"
    assert e.crss_outcome_column(["fatal"], "fatal") == "fatal"


def test_baseline_roundtrip_dict():
    crash, person = _synthetic_fars()
    b = e.baseline_from_frames(crash, person, (2022, 2024), crss_crash=_synthetic_crss())
    b2 = e.EmpiricalBaseline.from_dict(b.to_dict())
    assert b2.total_deaths() == pytest.approx(b.total_deaths())
    assert b2.segment_ka_crashes("alcohol") == pytest.approx(b.segment_ka_crashes("alcohol"))
    assert b2.quantities.keys() == b.quantities.keys()
    s = e.Scenario("g", generic("speeding", 0.25))
    assert e.evaluate(s, b2)["deaths_prevented"] == pytest.approx(
        e.evaluate(s, b)["deaths_prevented"]
    )


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


# --------------------------------------------------------------------------------------
# Layer C: parameters and timing
# --------------------------------------------------------------------------------------
def test_param_validation_and_sampling():
    p = e.Param(0.2)
    assert p.is_fixed and p.low == p.high == 0.2
    t = e.Param(0.2, 0.1, 0.4)
    assert t.distribution == "triangular"
    rng = np.random.default_rng(0)
    x = t.sample(rng, 200_000)
    assert x.min() >= 0.1 and x.max() <= 0.4
    assert x.mean() == pytest.approx((0.1 + 0.2 + 0.4) / 3, abs=2e-3)
    u = e.Param.range(0.1, 0.2, 0.5, "uniform").sample(rng, 200_000)
    assert u.mean() == pytest.approx(0.3, abs=2e-3)
    with pytest.raises(ValueError):
        e.Param(0.2, 0.3, 0.4)  # low > central
    with pytest.raises(ValueError):
        e.Param(0.2, 0.1, 0.3, "lognormal")
    with pytest.raises(ValueError):
        e.Param(0.2, 0.1, 0.3, "fixed")
    with pytest.raises(ValueError):
        e.Param(float("nan"))
    with pytest.raises(ValueError):
        e.Param(1.5, bounds=(0.0, 1.0))


def test_no_default_effect_sizes():
    cov = e.LinearCappedCoverage(per_unit=0.01)
    with pytest.raises(e.MissingAssumptionError, match="behavioural_response"):
        e.SpeedEnforcement(0, 10, cov, occurrence_effect=0.1, severity_effect=0.1)
    with pytest.raises(e.MissingAssumptionError, match="severity_effect"):
        e.SpeedEnforcement(0, 10, cov, behavioural_response=0.3, occurrence_effect=0.1)
    with pytest.raises(e.MissingAssumptionError, match="per_unit"):
        e.LinearCappedCoverage(per_unit=None)
    with pytest.raises(e.MissingAssumptionError):
        e.ImpairedDrivingEnforcement(0, 10, cov, detection_probability=0.5)
    with pytest.raises(e.MissingAssumptionError):
        e.RestraintEnforcement()
    with pytest.raises(e.MissingAssumptionError):
        e.GenericIntervention("speeding")
    with pytest.raises(e.MissingAssumptionError, match="Timing"):
        e.Timing(None, 0.0)


def test_input_validation():
    cov = e.LinearCappedCoverage(per_unit=0.01)
    kw = {"behavioural_response": 0.3, "occurrence_effect": 0.1, "severity_effect": 0.1}
    with pytest.raises(ValueError):
        e.SpeedEnforcement(0, 10, cov, **{**kw, "behavioural_response": 1.5})
    with pytest.raises(ValueError):
        e.SpeedEnforcement(-1, 10, cov, **kw)
    with pytest.raises(ValueError):
        e.SpeedEnforcement(0, 10, cov, target_segment="alcohol", **kw)
    with pytest.raises(TypeError):
        e.SpeedEnforcement(0, 10, 0.5, **kw)
    with pytest.raises(ValueError):
        e.GenericIntervention("helmets", relative_reduction_deaths=0.1)
    with pytest.raises(ValueError):
        e.GenericIntervention(
            "unrestrained_lpv", relative_reduction_deaths=0.1, relative_reduction_ka=0.1
        )
    with pytest.raises(ValueError):
        e.Scenario("bad.name", generic("speeding", 0.1))
    s = e.Scenario("g", generic("speeding", 0.1))
    with pytest.raises(KeyError):
        e.evaluate(s, toy_baseline(), {"nope": 0.1})
    with pytest.raises(ValueError):
        e.evaluate(s, toy_baseline(), {"relative_reduction_deaths": 2.0})


def test_timing_ramp_and_decay():
    m = [e.Timing.multiplier(t, 3.0, 0.1) for t in range(1, 6)]
    assert m == pytest.approx([1 / 3, 2 / 3, 1.0, 0.9, 0.81])
    assert [e.Timing.multiplier(t, 0.0, 0.0) for t in (1, 5)] == [1.0, 1.0]
    assert e.Timing.multiplier(3, 0.0, 0.5) == pytest.approx(0.25)
    with pytest.raises(ValueError):
        e.Timing.multiplier(0, 1.0, 0.0)


def test_project_requires_timing_and_applies_it():
    b = toy_baseline()
    s = e.Scenario("g", generic("speeding", 0.1))
    with pytest.raises(e.MissingAssumptionError):
        e.project(s, b, 3)
    s = e.Scenario("g", generic("speeding", 0.1), e.Timing(2.0, 0.0))
    p = e.project(s, b, 4)
    assert p["deaths_prevented"].tolist() == pytest.approx([10.0, 20.0, 20.0, 20.0])
    assert p["cumulative_deaths_prevented"].iloc[-1] == pytest.approx(70.0)
    assert (p["kind"] == "hypothetical").all()
    assert "relative_reduction_deaths=0.1" in p["assumptions"].iloc[0]


# --------------------------------------------------------------------------------------
# Layer B: coverage saturation and mechanism arithmetic
# --------------------------------------------------------------------------------------
def test_saturating_coverage_doubling_less_than_double():
    cov = e.SaturatingCoverage(rate=0.1)
    for u in (1.0, 5.0, 10.0, 30.0):
        assert cov(2 * u) < 2 * cov(u)
        assert cov(2 * u) > cov(u)
        assert cov(u) < 1.0
    assert cov(10.0) == pytest.approx(1 - math.exp(-1))
    capped = e.SaturatingCoverage(rate=0.1, max_coverage=0.5)
    assert capped(1e6) == pytest.approx(0.5)


def test_linear_capped_coverage_and_doubling_table():
    cov = e.LinearCappedCoverage(per_unit=0.1, cap=0.6)
    assert cov(2.0) == pytest.approx(0.2)
    assert cov(4.0) == pytest.approx(0.4)  # exactly double below the cap
    assert cov(8.0) == pytest.approx(0.6)  # cap binds
    t = e.doubling_table(cov, [1.0, 2.0, 3.0, 5.0])
    assert t["doubling_ratio"].tolist() == pytest.approx([2.0, 2.0, 0.6 / 0.3, 0.6 / 0.5])
    assert (t["doubling_ratio"] <= 2.0 + 1e-12).all()
    ts = e.doubling_table(e.SaturatingCoverage(rate=1.0), [0.5, 1.0, 2.0])
    assert (ts["doubling_ratio"] < 2.0).all()
    assert ts["doubling_ratio"].is_monotonic_decreasing


def _speed(**kw) -> e.SpeedEnforcement:
    args = dict(
        units_current=0.0,
        units_proposed=50.0,
        coverage=e.LinearCappedCoverage(per_unit=0.01),
        behavioural_response=0.4,
        occurrence_effect=0.5,
        severity_effect=0.2,
    )
    args.update(kw)
    return e.SpeedEnforcement(**args)


def test_speed_enforcement_chain_arithmetic():
    b = toy_baseline()
    r = e.evaluate(e.Scenario("cams", _speed()), b)
    # coverage 0.5, B = 0.4*0.5 = 0.2, prevented share 0.2*(1-0.5*0.8) = 0.12
    assert r["chain"]["share_of_target_speeding_removed"] == pytest.approx(0.2)
    assert r["relative_reduction_target_deaths"] == pytest.approx(0.12)
    assert r["deaths_prevented"] == pytest.approx(50 * 0.12)
    assert r["fatal_crashes_prevented"] == pytest.approx(45 * 0.12)
    assert r["ka_crashes_prevented"] is None  # no KA severity effect supplied
    assert r["pct_change_deaths"] == pytest.approx(-100 * 6.0 / 1000)
    assert r["kind"] == "hypothetical"
    names = {a["parameter"] for a in r["assumptions"]}
    assert {"behavioural_response", "coverage.per_unit", "halo", "severity_effect"} <= names
    # from an existing deployment: B = 1 - (1 - 0.4*1.0)/(1 - 0.4*0.5) = 0.25
    r2 = e.evaluate(e.Scenario("c2", _speed(units_current=50.0, units_proposed=100.0)), b)
    assert r2["chain"]["share_of_target_speeding_removed"] == pytest.approx(0.25)
    # halo: E = min(1, 1.5 * 0.5) = 0.75 -> B = 0.3; no halo without coverage
    r3 = e.evaluate(e.Scenario("c3", _speed(halo=0.5)), b)
    assert r3["chain"]["share_of_target_speeding_removed"] == pytest.approx(0.3)
    r0 = e.evaluate(e.Scenario("c0", _speed(halo=0.5, units_proposed=0.0)), b)
    assert r0["deaths_prevented"] == pytest.approx(0.0)
    r6 = e.evaluate(e.Scenario("c6", _speed(halo=3.0)), b)  # E capped at 1
    assert r6["chain"]["effective_share_proposed"] == pytest.approx(1.0)
    # KA with a KA severity effect: 0.2*(1-0.5*0.9) = 0.11 of 200 KA crashes
    r4 = e.evaluate(e.Scenario("c4", _speed(severity_effect_ka=0.1)), b)
    assert r4["ka_crashes_prevented"] == pytest.approx(200 * 0.11)
    assert r4["pct_change_ka_crashes"] == pytest.approx(-100 * 22 / 10100)
    # all speeding as target
    r5 = e.evaluate(e.Scenario("c5", _speed(target_segment="speeding")), b)
    assert r5["deaths_prevented"] == pytest.approx(200 * 0.12)


def test_doubling_units_does_not_double_effect():
    b = toy_baseline()
    cov = e.SaturatingCoverage(rate=0.02)
    one = e.evaluate(e.Scenario("a", _speed(coverage=cov, units_proposed=50.0)), b)
    two = e.evaluate(e.Scenario("b", _speed(coverage=cov, units_proposed=100.0)), b)
    assert two["deaths_prevented"] < 2 * one["deaths_prevented"]


def test_impaired_driving_deterrence_chain():
    b = toy_baseline()
    m = e.ImpairedDrivingEnforcement(
        0.0,
        1000.0,
        e.SaturatingCoverage(rate=0.001),
        detection_probability=0.5,
        deterrence_elasticity=1.0,
        occurrence_effect=0.0,
        severity_effect=1.0,
    )
    r = e.evaluate(e.Scenario("rbt", m), b)
    risk = 0.5 * (1 - math.exp(-1))
    share = 1 - math.exp(-risk)
    assert r["chain"]["perceived_risk_proposed"] == pytest.approx(risk)
    assert r["deaths_prevented"] == pytest.approx(210 * share)
    # fewer checks than now -> negative 'prevented' (an increase), not silently clipped
    m2 = e.ImpairedDrivingEnforcement(
        1000.0,
        0.0,
        e.SaturatingCoverage(rate=0.001),
        detection_probability=0.5,
        deterrence_elasticity=1.0,
        occurrence_effect=0.0,
        severity_effect=1.0,
    )
    assert e.evaluate(e.Scenario("cut", m2), b)["deaths_prevented"] < 0
    drugs = e.ImpairedDrivingEnforcement(
        0.0,
        10.0,
        e.SaturatingCoverage(rate=0.1),
        detection_probability=0.5,
        deterrence_elasticity=1.0,
        occurrence_effect=0.1,
        severity_effect=0.1,
        target_segment="drugs",
    )
    rd = e.evaluate(e.Scenario("dt", drugs), b)
    assert rd["target_reliability"] == "low" and any("LOW" in n for n in rd["notes"])


def test_restraint_uses_layer_a_belt_estimate_or_requires_input():
    b = toy_baseline()
    r = e.evaluate(e.Scenario("belt", e.RestraintEnforcement(conversion_share=0.5)), b)
    assert r["deaths_prevented"] == pytest.approx(50 * 0.5 * 0.6)
    src = {a["parameter"]: a["source"] for a in r["assumptions"]}
    assert "Layer A" in src["belt_effectiveness"]
    assert r["fatal_crashes_prevented"] is None and r["ka_crashes_prevented"] is None
    r2 = e.evaluate(
        e.Scenario("b2", e.RestraintEnforcement(conversion_share=0.5, belt_effectiveness=0.4)), b
    )
    assert r2["deaths_prevented"] == pytest.approx(10.0)
    r3 = e.evaluate(
        e.Scenario("b3", e.RestraintEnforcement(conversion_share=0.5, converter_benefit_ratio=0.5)),
        b,
    )
    assert r3["deaths_prevented"] == pytest.approx(50 * 0.5 * 0.3)
    with pytest.raises(e.MissingAssumptionError):
        e.evaluate(
            e.Scenario("b4", e.RestraintEnforcement(conversion_share=0.5)),
            toy_baseline(belt=False),
        )


def test_association_helpers_are_explicitly_assumptions():
    b = toy_baseline()
    p = e.severity_effect_from_association(b, "speeding")
    assert (p.low, p.central, p.high) == pytest.approx((1 / 3, 0.5, 0.6))
    assert "ASSUMES" in p.source
    with pytest.raises(e.MissingInputError):
        e.severity_effect_from_association(b, "alcohol")
    bp = e.belt_effectiveness_param(b)
    assert (bp.low, bp.central, bp.high) == pytest.approx((0.5, 0.6, 0.7))


# --------------------------------------------------------------------------------------
# Layer D: combination without double counting, sensitivity, solving
# --------------------------------------------------------------------------------------
def test_combination_multiplicative_survival_on_overlap():
    b = toy_baseline()
    sp = e.Scenario("sp", generic("speeding", 0.2))
    al = e.Scenario("al", generic("alcohol", 0.5))
    c = e.combine([sp, al], b)
    # 200*0.2 + 210*0.5 - 50*0.2*0.5
    assert c["deaths_prevented"] == pytest.approx(140.0)
    assert c["deaths_prevented_naive_sum"] == pytest.approx(145.0)
    assert c["double_counting_avoided"] == pytest.approx(5.0)
    assert c["deaths_in_all_target_segments_per_year"] == pytest.approx(50.0)
    assert c["kind"] == "hypothetical"
    assert any("multiplicative" in s for s in c["structural_assumptions"])
    cm = e.combine([sp, al], b, overlap="max")
    assert cm["deaths_prevented"] == pytest.approx(150 * 0.2 + 160 * 0.5 + 50 * 0.5)
    assert cm["deaths_prevented"] <= c["deaths_prevented"] <= c["deaths_prevented_naive_sum"]
    assert c["deaths_prevented"] <= b.deaths.union("speeding", "alcohol")


def test_combination_same_segment_and_full_effects_never_exceed_deaths():
    b = toy_baseline()
    a1 = e.Scenario("a1", generic("speeding", 0.2))
    a2 = e.Scenario("a2", generic("speeding", 0.3))
    assert e.combine([a1, a2], b)["deaths_prevented"] == pytest.approx(200 * (1 - 0.8 * 0.7))
    full = [e.Scenario("f1", generic("speeding", 1.0)), e.Scenario("f2", generic("alcohol", 1.0))]
    c = e.combine(full, b)
    assert c["deaths_prevented"] == pytest.approx(b.deaths.union("speeding", "alcohol"))
    assert c["deaths_prevented_naive_sum"] > c["deaths_prevented"]
    with pytest.raises(ValueError):
        e.combine([a1, e.Scenario("a1", generic("alcohol", 0.1))], b)


def test_combination_fatal_and_ka_with_person_level_scenario():
    b = toy_baseline()
    sp = e.Scenario(
        "sp",
        generic("speeding", 0.2, relative_reduction_fatal_crashes=0.2, relative_reduction_ka=0.1),
    )
    belt = e.Scenario("belt", e.RestraintEnforcement(conversion_share=0.5))
    c = e.combine([sp, belt], b)
    assert c["fatal_crashes_prevented"] == pytest.approx(180 * 0.2)
    assert c["fatal_crashes_excludes"] == ["belt"]
    assert c["ka_crashes_prevented"] == pytest.approx(800 * 0.1)
    # speeding & unrestrained do not overlap in the toy partition -> additive
    assert c["deaths_prevented"] == pytest.approx(200 * 0.2 + 50 * 0.5 * 0.6)


def test_tornado_corner_range_and_monte_carlo():
    b = toy_baseline()
    s = e.Scenario(
        "cams",
        _speed(
            behavioural_response=e.Param(0.4, 0.2, 0.6),
            severity_effect=e.Param(0.2, 0.1, 0.3, "uniform"),
        ),
    )
    t = e.tornado(s, b)
    assert t["parameter"].iloc[0] == "behavioural_response"
    assert t["swing"].is_monotonic_decreasing
    row = t.set_index("parameter").loc["behavioural_response"]
    # linear in the response when starting from zero units
    assert row["deaths_prevented_at_low"] == pytest.approx(50 * 0.1 * (1 - 0.5 * 0.8))
    fixed_rows = t[t["low"] == t["high"]]
    assert (fixed_rows["swing"] == 0).all()
    assert not t["parameter"].str.startswith("timing.").any()
    rng_ = e.corner_range(s, b)
    lo, hi = rng_["deaths_prevented"]["min"], rng_["deaths_prevented"]["max"]
    assert lo == pytest.approx(50 * 0.1 * (1 - 0.5 * 0.9))
    assert hi == pytest.approx(50 * 0.3 * (1 - 0.5 * 0.7))
    mc1 = e.monte_carlo(s, b, n_draws=4000, seed=7)
    mc2 = e.monte_carlo(s, b, n_draws=4000, seed=7)
    pd.testing.assert_frame_equal(mc1.summary, mc2.summary)
    d = mc1.draws["deaths_prevented"]
    assert lo - 1e-9 <= d.min() and d.max() <= hi + 1e-9
    assert (mc1.summary["kind"] == "hypothetical").all()
    assert {a["parameter"] for a in mc1.assumptions} >= {"behavioural_response"}
    # expectation check: E[B]=0.2 (triangular mean 0.4 * 0.5), E[1-0.5(1-s)] with E[s]=0.2
    assert d.mean() == pytest.approx(50 * 0.2 * (1 - 0.5 * 0.8), rel=0.02)


def test_tornado_and_corners_over_horizon_include_timing():
    b = toy_baseline()
    s = e.Scenario(
        "g",
        generic("speeding", 0.1),
        e.Timing(ramp_years=e.Param(2.0, 1.0, 3.0), decay_per_year=e.Param(0.0, 0.0, 0.1)),
    )
    assert e.tornado(s, b).shape[0] == 1  # steady state: only the effect parameter
    t = e.tornado(s, b, horizon_years=3).set_index("parameter")
    # ramp 1 -> 3 years at full effect; ramp 3 -> 1/3 + 2/3 + 1 = 2 years' worth
    assert t.loc["timing.ramp_years", "cumulative_deaths_prevented_3y_at_low"] == pytest.approx(
        60.0
    )
    assert t.loc["timing.ramp_years", "cumulative_deaths_prevented_3y_at_high"] == pytest.approx(
        40.0
    )
    cr = e.corner_range(s, b, horizon_years=3)
    assert "timing.ramp_years" in cr["ranged_parameters"]
    assert cr["deaths_prevented"]["max"] == pytest.approx(60.0)
    assert e.corner_range(s, b)["ranged_parameters"] == []


def test_monte_carlo_combination_and_horizon():
    b = toy_baseline()
    sp = e.Scenario("sp", generic("speeding", e.Param(0.2, 0.1, 0.3)), e.Timing.immediate())
    al = e.Scenario("al", generic("alcohol", e.Param(0.5, 0.4, 0.6)), e.Timing.immediate())
    mc = e.monte_carlo([sp, al], b, n_draws=2000, horizon_years=3)
    assert "sp.relative_reduction_deaths" in mc.draws
    x = mc.draws
    expect = (
        200 * x["sp.relative_reduction_deaths"]
        + 210 * x["al.relative_reduction_deaths"]
        - 50 * x["sp.relative_reduction_deaths"] * x["al.relative_reduction_deaths"]
    )
    np.testing.assert_allclose(x["deaths_prevented"], expect)
    np.testing.assert_allclose(x["cumulative_deaths_prevented_3y"], 3 * expect)


def test_solve_scenario_parameter():
    b = toy_baseline()
    s = e.Scenario("g", generic("speeding", 0.1))
    r = e.solve_scenario_parameter(s, b, "relative_reduction_deaths", 30.0)
    assert r["status"] == "solved" and r["value"] == pytest.approx(0.15)
    assert r["direction"] == "increasing"
    assert e.solve_scenario_parameter(s, b, "relative_reduction_deaths", 300.0)["status"] == (
        "not_achievable"
    )
    r0 = e.solve_scenario_parameter(s, b, "relative_reduction_deaths", -500.0)
    assert r0["status"] == "met_throughout_bounds"
    # mechanism parameter: deaths = 50 * 0.5 * resp * 0.6 -> resp = 6 / 15
    rs = e.solve_scenario_parameter(e.Scenario("c", _speed()), b, "behavioural_response", 6.0)
    assert rs["value"] == pytest.approx(0.4)


def test_solve_monotone_decreasing_function():
    r = e.solve_monotone(lambda x: 10 - 10 * x, 4.0, (0.0, 1.0))
    assert r["status"] == "solved" and r["direction"] == "decreasing"
    assert r["value"] == pytest.approx(0.6)
    with pytest.raises(ValueError):
        e.solve_monotone(lambda x: x, 0.5, (0.0, math.inf))


# --------------------------------------------------------------------------------------
# Assumption-free threshold arithmetic and helpers
# --------------------------------------------------------------------------------------
def test_threshold_tables():
    b = toy_baseline()
    t = e.required_share_table(b, ("speeding", "drugs"), (1.0, 50.0))
    r = t.set_index(["segment", "reduction_of_all_deaths_pct"])
    assert r.loc[("speeding", 1.0), "required_share_of_segment_deaths"] == pytest.approx(0.05)
    assert not r.loc[("speeding", 50.0), "feasible_through_segment_alone"]
    assert math.isinf(r.loc[("drugs", 1.0), "required_share_of_segment_deaths"])
    assert (t["kind"] == "hypothetical").all()
    g = e.breakeven_share_grid(b, (10.0,), ("alcohol",))
    assert g["required_share_of_segment_deaths"].iloc[0] == pytest.approx(10 / 210)
    c = e.conditional_threshold_table(b, 1.0)
    belt = c[(c["segment"] == "unrestrained_lpv") & (c["input_point"] == "estimate")]
    assert belt["required_value"].iloc[0] == pytest.approx(10 / (50 * 0.6))
    sp = c[(c["segment"] == "speeding") & (c["input_point"] == "estimate")]
    assert sp["required_value"].iloc[0] == pytest.approx(10 / (200 * 0.5))
    ov = e.overlap_table(b).set_index(["segment_a", "segment_b"])
    assert ov.loc[("speeding", "alcohol"), "deaths_both"] == pytest.approx(50.0)
    assert ov.loc[("speeding", "alcohol"), "deaths_either"] == pytest.approx(360.0)


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
    r = e.evaluate(e.Scenario("g", generic("speeding", 0.1)), b)
    assert r["deaths_prevented"] == pytest.approx(0.1 * b.segment_deaths("speeding"))
    assert r["kind"] == "hypothetical"
