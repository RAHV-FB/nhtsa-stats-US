"""Culpability coding, QIE identity, burden and app prediction helpers (synthetic data)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
import pytest

from nhtsa_stats.analysis import exposure
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit


def test_culpability_codes():
    codes = pl.DataFrame({"c": [0, 4, 7, 8, 46, 58, 71, 98, 99, 95]})
    out = codes.select(exposure.culpability(pl.col("c")).alias("x"))["x"].to_list()
    # 0 none -> 0; 4/46/58/98 moving -> 1; 7/8 post-crash -> 0; 71 licence (non-moving) -> 0; 99/95 unknown -> null
    assert out == [0, 1, 0, 0, 1, 1, 0, 1, None, None]


def test_charge_based_culpability_excludes_circular_codes():
    # 1 manslaughter / 9 violation resulting in death (outcome-defined) and 11-19 impairment
    # charges never define culpability, so alcohol is not built into the outcome.
    codes = pl.DataFrame({"c": [1, 9, 11, 15, 19, 20, 10]})
    out = codes.select(exposure.culpability(pl.col("c")).alias("x"))["x"].to_list()
    assert out == [0, 0, 0, 0, 0, 1, 1]


def test_c1_classification():
    d = pl.DataFrame(
        {
            # speeding; culpable pre-crash event; error code; clean non-culpable;
            # neutral event but speeding unknown; non-culpable event with unknown driver factor
            "SPEEDREL": [3, 0, 0, 0, 9, 0],
            "P_CRASH2": [60, 6, 60, 60, 1, 62],
            "error": [False, False, True, False, False, False],
            "drf_unknown": [False, False, False, False, False, True],
        }
    )
    out = d.select(exposure.culp_c1().alias("c"))["c"].to_list()
    assert out == [1, 1, 1, 0, None, None]


def test_qualifying_pairs():
    d = pl.DataFrame(
        {
            "YEAR": [2020] * 10,
            "case_id": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
            # 1 ok; 2 both culpable; 3 one undetermined; 4 one driver absent; 5 ok
            "culpable": [1, 0, 1, 1, 1, None, 1, 0, 0, 1],
            "PER_TYP": [1, 1, 1, 1, 1, 1, 1, None, 1, 1],
            "DR_PRES": [1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
        }
    )
    keep = exposure.qualifying_pairs(d).sort("case_id")["case_id"].to_list()
    assert keep == [1, 5]


def test_candidate_crashes_exclude_hit_and_run():
    crash = pl.DataFrame(
        {
            "n_veh_in_transport": [2, 2, 2, 3, 2],
            "any_nonmotorist": [0, 0, 1, 0, 0],
            "hit_and_run": [0, 1, 0, 0, None],
        }
    )
    # Unknown hit-and-run status is excluded as well (unknown is not "no").
    assert exposure.candidate_crashes(crash).height == 1


def test_rir_equals_within_group_odds_in_one_to_one_pairs():
    # Two drivers per crash, exactly one culpable: RIR_g = culpable share / non-culpable share = odds within g.
    rng = np.random.default_rng(0)
    n_crash = 4000
    young_culp = rng.random(n_crash) < 0.3
    young_non = rng.random(n_crash) < 0.15
    df = pd.DataFrame(
        {
            "group": np.r_[
                np.where(young_culp, "young", "other"), np.where(young_non, "young", "other")
            ],
            "culpable": np.r_[np.ones(n_crash), np.zeros(n_crash)],
        }
    )
    crash = np.r_[np.arange(n_crash), np.arange(n_crash)]
    design = SurveyDesign.from_arrays(np.ones(2 * n_crash), None, crash)
    m = SurveyLogit(ModelSpec(categorical={"group": ["other", "young"]})).fit(
        df, df["culpable"].to_numpy(), design
    )
    ms = m.margins(df, {"young": lambda d: d.assign(group="young")})
    p = ms.values["young"]
    rir = young_culp.mean() / young_non.mean()
    assert p / (1 - p) == pytest.approx(rir, rel=1e-6)


def test_app_prediction_matches_model():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    pytest.importorskip("streamlit")
    from views.severity_model import predict

    rng = np.random.default_rng(1)
    n = 3000
    df = pd.DataFrame({"a": rng.choice(["no", "yes"], n)})
    y = (rng.random(n) < np.where(df["a"] == "yes", 0.2, 0.05)).astype(float)
    spec = ModelSpec(categorical={"a": ["no", "yes"]})
    m = SurveyLogit(spec).fit(df, y, SurveyDesign.from_arrays(np.ones(n), None, None))
    model = {
        "levels": spec.categorical,
        "terms": m.names_,
        "coef": m.coef_.tolist(),
        "vcov": m.vcov_.tolist(),
        "design_df": 100,
    }
    p, lo, hi = predict(model, {"a": "yes"})
    assert p == pytest.approx(y[df["a"] == "yes"].mean(), rel=1e-6)
    assert lo < p < hi


def _burden_fixture(rng, rr_speed: float):
    from nhtsa_stats.analysis import burden

    n = 20000
    df = pd.DataFrame(
        {
            "speeding": rng.choice(["no", "yes"], n, p=[0.8, 0.2]),
            "alcohol_im": rng.choice(["no", "yes"], n, p=[0.9, 0.1]),
            "light": "daylight",
            "speed_limit": "30-35",
        }
    )
    p = 0.01 * np.where(df["speeding"] == "yes", rr_speed, 1.0)
    y = (rng.random(n) < p).astype(float)
    spec = ModelSpec(categorical={"speeding": ["no", "yes"], "alcohol_im": ["no", "yes"]})
    design = SurveyDesign.from_arrays(np.ones(n), np.repeat([1, 2], n // 2), np.arange(n) % 40)
    model = SurveyLogit(spec).fit(df, y, design)
    return burden, df, design, model, y


def test_af_matches_closed_form_and_scales_only_fatal():
    rng = np.random.default_rng(3)
    burden, df, design, model, y = _burden_fixture(rng, rr_speed=3.0)
    rows = burden._af_rows(model, df, design, burden.SHIFTS[:2], "fatal", 1000.0, 900.0)
    af = rows[0]["af"]
    # Saturated in speeding: AF = 1 - sum(p_cf)/sum(p_obs) with p_cf the 'no' rate.
    p_no = y[df["speeding"] == "no"].mean()
    expected = 1 - (len(df) * p_no) / y.sum()
    assert af == pytest.approx(expected, abs=0.01)
    assert rows[0]["fars_scaled_deaths_per_year"] == pytest.approx(af * 1000.0)
    ka = burden._af_rows(model, df, design, burden.SHIFTS[:1], "ka", 1000.0, 900.0)
    assert np.isnan(ka[0]["fars_scaled_deaths_per_year"])


def test_af_near_zero_without_effect_and_joint_counts_union():
    rng = np.random.default_rng(4)
    burden, df, design, model, _ = _burden_fixture(rng, rr_speed=1.0)
    joint = next(s for s in burden.SHIFTS if s.name == "speeding_and_alcohol_removed")
    rows = burden._af_rows(model, df, design, [burden.SHIFTS[0], joint], "fatal", 1.0, 1.0)
    lo, hi = rows[0]["af_low"], rows[0]["af_high"]
    assert lo < 0 < hi
    union = ((df["speeding"] == "yes") | (df["alcohol_im"] == "yes")).sum()
    assert rows[1]["n_exposed_crss"] == union
