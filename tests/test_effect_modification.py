"""Follow-up tables (docs/red_team_2026-11.md section 5): effect modification of model-A
associations by crash configuration, model-A calibration by decile, and the imputed-BAC injury
diagnostic.  Synthetic data with a known truth; no data cache needed."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import measurement, severity, specs
from nhtsa_stats.analysis.survey import SurveyDesign


# --------------------------------------------------------------------------------------
# homogeneity test, weighted deciles, calibration
# --------------------------------------------------------------------------------------
def test_homogeneity_test_matches_hand_computation():
    from scipy import stats

    log_rr = np.array([0.0, 0.5])
    v = np.diag([0.01, 0.03])
    t = severity.homogeneity_test(log_rr, v, design_df=40)
    w = 0.5**2 / 0.04
    assert t["wald_chi2"] == pytest.approx(w)
    f = (40 - 1 + 1) / 40 * w
    assert t["p"] == pytest.approx(stats.f.sf(f, 1, 40))
    # positive covariance between the strata shrinks the variance of the difference
    v2 = np.array([[0.01, 0.01], [0.01, 0.03]])
    assert severity.homogeneity_test(log_rr, v2, 40)["p"] < t["p"]
    assert np.isnan(severity.homogeneity_test(np.array([0.1]), np.array([[1.0]]), 40)["p"])


def test_weighted_deciles_hold_equal_weight():
    rng = np.random.default_rng(0)
    p = rng.random(2000)
    w = rng.integers(1, 20, 2000).astype(float)
    dec = severity.weighted_deciles(p, w)
    assert set(dec) == set(range(1, 11))
    share = np.array([w[dec == g].sum() for g in range(1, 11)]) / w.sum()
    assert np.allclose(share, 0.1, atol=0.01)
    # ordered by predicted risk, every boundary strict
    assert all(p[dec == g].max() < p[dec == g + 1].min() for g in range(1, 10))


def test_weighted_deciles_keep_tied_predictions_together():
    rng = np.random.default_rng(5)
    p = np.round(rng.random(3000), 1)  # eleven distinct values: heavy ties
    w = rng.integers(1, 20, 3000).astype(float)
    dec = severity.weighted_deciles(p, w)
    for v in np.unique(p):
        assert len(np.unique(dec[p == v])) == 1
    groups = np.unique(dec)
    assert all(p[dec == g].max() < p[dec == h].min() for g, h in itertools.pairwise(groups))
    # everything tied: one group, nothing split
    assert len(np.unique(severity.weighted_deciles(np.full(50, 0.2), np.ones(50)))) == 1


def _calib_data(scale: float, n: int = 40000, seed: int = 1):
    rng = np.random.default_rng(seed)
    p = np.clip(rng.beta(1.2, 20, n), 1e-4, 0.5)
    y = (rng.random(n) < np.minimum(p * scale, 0.99)).astype(float)
    cl = rng.integers(0, 30, n)
    design = SurveyDesign.from_arrays(rng.uniform(0.5, 2, n), cl // 10, cl)
    return p, y, design


def test_calibration_covers_one_when_calibrated_and_flags_miscalibration():
    p, y, design = _calib_data(1.0)
    c = severity.calibration_by_decile(p, y, design)
    assert list(c["decile"][:10]) == list(range(1, 11)) and c["decile"].iloc[-1] == "all"
    assert (c["n_crashes"].iloc[:10].sum()) == len(p)
    allrow = c.iloc[-1]
    assert allrow["ratio_low"] < 1 < allrow["ratio_high"]
    assert (c["observed_low"] <= c["observed"]).all() and (
        c["observed"] <= c["observed_high"]
    ).all()
    dec = severity.weighted_deciles(p, design.weight)
    deciles = c.iloc[:10]
    # deciles partition the sample and reproduce the overall totals ...
    assert deciles["n_crashes"].sum() == allrow["n_crashes"] == len(p)
    assert deciles["n_events"].sum() == allrow["n_events"] == int(y.sum())
    w = design.weight
    for g in range(1, 11):
        m = dec == g
        assert c.loc[g - 1, "n_crashes"] == m.sum()
        assert c.loc[g - 1, "predicted"] == pytest.approx(np.average(p[m], weights=w[m]))
        assert c.loc[g - 1, "observed"] == pytest.approx(np.average(y[m], weights=w[m]))
    # ... so weight-averaging the decile means gives the overall weighted observed / predicted
    dw = np.array([w[dec == g].sum() for g in range(1, 11)])
    assert np.average(deciles["observed"], weights=dw) == pytest.approx(allrow["observed"])
    assert np.average(deciles["predicted"], weights=dw) == pytest.approx(allrow["predicted"])
    assert allrow["ratio_observed_to_predicted"] == pytest.approx((w * y).sum() / (w * p).sum())
    # predicted risk is strictly ordered across deciles (ties are never split)
    assert (np.diff(deciles["predicted_min"]) > 0).all()
    assert (
        deciles["predicted_max"].to_numpy()[:-1] < deciles["predicted_min"].to_numpy()[1:]
    ).all()
    p2, y2, d2 = _calib_data(1.3)
    c2 = severity.calibration_by_decile(p2, y2, d2).iloc[-1]
    assert c2["ratio_observed_to_predicted"] == pytest.approx(1.3, abs=0.15)
    assert c2["ratio_low"] > 1.0


# --------------------------------------------------------------------------------------
# effect modification
# --------------------------------------------------------------------------------------
def _em_frame(rr_single: float, rr_multi: float, n: int = 30000, seed: int = 3):
    rng = np.random.default_rng(seed)
    cols = {c: specs.CRASH_LEVELS[c][0] for c in specs.PRE_CRASH}
    df = pd.DataFrame({c: [v] * n for c, v in cols.items()})
    df["YEAR"] = 2016
    single = rng.random(n) < 0.4
    moto = np.where(rng.random(n) < 0.15, "yes", "no")
    df["any_motorcycle"] = moto
    df["n_vehicles"] = np.where(single, "1", "2")
    df["crash_type"] = np.where(
        single, "sv_off_roadway", rng.choice(["mv_angle", "mv_rear_end"], n)
    )
    df["speeding_type"] = "no"
    base = np.where(single, 0.05, 0.02)
    rr = np.where(moto == "yes", np.where(single, rr_single, rr_multi), 1.0)
    df["fatal"] = (rng.random(n) < base * rr).astype(float)
    cl = rng.integers(0, 30, n)
    return df, SurveyDesign.from_arrays(np.ones(n), cl // 10, cl)


def _run_em(monkeypatch, rr_single, rr_multi):
    df, design = _em_frame(rr_single, rr_multi)
    monkeypatch.setattr(severity, "load", lambda outcome, years=None: (df.copy(), design))
    monkeypatch.setattr(
        severity,
        "EM_EXPOSURES",
        {"motorcycle": ("any_motorcycle", "yes", "no", "Motorcycle involved")},
    )
    return severity.effect_modification("fatal")


def test_effect_modification_recovers_stratum_rrs_and_flags_heterogeneity(monkeypatch):
    out = _run_em(monkeypatch, 5.0, 1.5)
    v = out[out["modifier"] == "single vs multi-vehicle"].set_index("stratum")
    assert v.loc["single-vehicle", "adj_rr"] == pytest.approx(5.0, rel=0.25)
    assert v.loc["multi-vehicle", "adj_rr"] == pytest.approx(1.5, rel=0.35)
    assert v.loc["single-vehicle", "adj_rr_low"] < 5.0 < v.loc["single-vehicle", "adj_rr_high"]
    assert v["p_homogeneity_rr"].iloc[0] < 0.001 and v["p_interaction_logit"].iloc[0] < 0.001
    assert v.loc["multi-vehicle", "rr_ratio_to_first_stratum"] < 0.6
    assert v.loc["single-vehicle", "rr_ratio_to_first_stratum"] == 1.0
    assert v["pooled_model_a_rr"].notna().all()
    # pooled RR lies between the stratum RRs
    pooled = v["pooled_model_a_rr"].iloc[0]
    assert v.loc["multi-vehicle", "adj_rr"] < pooled < v.loc["single-vehicle", "adj_rr"]
    # finer crash types: the two multi-vehicle types and the single-vehicle type all qualify
    t = out[out["modifier"] == "crash type"].set_index("stratum")
    assert set(t.index) == {"sv_off_roadway", "mv_angle", "mv_rear_end"}
    assert (t["status"] == "ok").all()
    assert t.loc["mv_angle", "adj_rr"] == pytest.approx(t.loc["mv_rear_end", "adj_rr"], rel=0.6)


def test_effect_modification_null_has_large_p_and_min_events_rule(monkeypatch):
    out = _run_em(monkeypatch, 2.0, 2.0)
    v = out[out["modifier"] == "single vs multi-vehicle"]
    assert v["p_homogeneity_rr"].iloc[0] > 0.05
    # raise the bar so no stratum qualifies: no estimates, an explanatory status, no test
    monkeypatch.setattr(severity, "EM_MIN_EVENTS", 10**6)
    out2 = severity.effect_modification("fatal")
    v2 = out2[out2["modifier"] == "single vs multi-vehicle"]
    assert v2["adj_rr"].isna().all() and v2["status"].str.startswith("not estimated").all()
    assert v2["p_homogeneity_rr"].isna().all()


# --------------------------------------------------------------------------------------
# imputed-BAC injury diagnostic
# --------------------------------------------------------------------------------------
def _per_frame(n: int = 8000, seed: int = 5) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tested = rng.random(n) < 0.5
    bac08 = rng.random(n) < 0.2
    p08 = np.where(tested, bac08.astype(float), np.round(rng.beta(1, 6, n), 1))
    logit = -1.0 + np.where(tested & bac08, np.log(3.0), 0.0)  # injury depends on measured BAC only
    killed = rng.random(n) < 1 / (1 + np.exp(-logit))
    return pd.DataFrame(
        {
            "case_id": np.arange(n),
            "YEAR": rng.choice([2016, 2017], n),
            "ptype": "driver",
            "killed": killed.astype(float),
            "p_p08": p08,
            "ALC_RES": np.where(tested, np.where(bac08, 120, 10), 995),
            "age_band": rng.choice(["25-34", "35-44"], n),
            "sex": rng.choice(["male", "female"], n),
            "body": rng.choice(["car", "suv"], n),
            "crash_type": rng.choice(["mv_angle", "sv_off_roadway"], n),
            "tod": rng.choice(["10-15", "20-23"], n),
            "pr_alcohol": rng.choice([0.0, 1.0, np.nan], n),
            "light": rng.choice(["daylight", "dark_lighted"], n),
            "rural": rng.choice([0.0, 1.0], n),
            "weekend": rng.choice([0.0, 1.0], n),
        }
    )


def test_imputed_bac_injury_separates_measured_from_imputed():
    out = measurement.imputed_bac_injury(_per_frame())
    prim = out[out["covariate_set"] == "primary"].set_index("group")
    assert prim.loc["tested", "adj_or"] == pytest.approx(3.0, rel=0.25)
    assert prim.loc["tested", "adj_or_low"] > 2.0
    assert prim.loc["imputed", "adj_or_low"] < 1.0 < prim.loc["imputed", "adj_or_high"]
    diff = prim.loc["imputed vs tested"]
    assert diff["adj_or"] == pytest.approx(
        prim.loc["imputed", "adj_or"] / prim.loc["tested", "adj_or"], rel=0.2
    )
    assert diff["p"] < 0.05
    assert prim.loc["imputed", "n_drivers"] + prim.loc["tested", "n_drivers"] == 8000
    assert set(out["covariate_set"]) == {"primary", "plus police alcohol, light, area, weekend"}
    assert prim["converged"].all()
