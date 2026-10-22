"""Tests of the post-2020 severity-trend machinery (synthetic data = software tests only)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import trends as T
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit


def _two_periods(
    n: int = 40000,
    seed: int = 1,
    z_share: tuple[float, float] = (0.2, 0.2),
    intercepts: tuple[float, float] = (-4.0, -4.0),
) -> tuple[pd.DataFrame, SurveyDesign]:
    """Crashes in 2018 (P0) and 2021 (P1); risk depends on Z (and a nuisance factor A)."""
    rng = np.random.default_rng(seed)
    year = np.where(rng.random(n) < 0.5, 2018, 2021)
    p1 = year == 2021
    z = rng.random(n) < np.where(p1, z_share[1], z_share[0])
    a = rng.choice(["x", "y"], n)
    eta = np.where(p1, intercepts[1], intercepts[0]) + 1.5 * z + 0.4 * (a == "y")
    y = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    stratum = rng.integers(0, 5, n)
    cluster = stratum * 10 + rng.integers(0, 4, n)
    df = pd.DataFrame(
        {
            "YEAR": year,
            "z": pd.Categorical(np.where(z, "yes", "no"), categories=["no", "yes"]),
            "a": pd.Categorical(a, categories=["x", "y"]),
            "fatal": y,
        }
    )
    return df, SurveyDesign.from_arrays(rng.uniform(1, 4, n), stratum, cluster)


def _decompose(df: pd.DataFrame, design: SurveyDesign) -> T.Decomposition:
    return T.decompose(df, design, ["z", "a"], "fatal", "test", (2018,), (2021,))


def _row(tab: pd.DataFrame, q: str) -> pd.Series:
    return tab.set_index("quantity").loc[q]


# --------------------------------------------------------------------------------------
def test_rubin_share():
    rng = np.random.default_rng(0)
    col = (rng.random(1000) < 0.3).astype(float)
    same = np.repeat(col[:, None], 10, axis=1)
    est, se, dof = T.rubin_share(same)
    assert est == pytest.approx(col.mean())
    assert se == pytest.approx(np.sqrt(col.mean() * (1 - col.mean()) / 1000))
    assert dof == np.inf
    noisy = (rng.random((1000, 10)) < 0.3).astype(float)
    est2, se2, dof2 = T.rubin_share(noisy)
    assert est2 == pytest.approx(noisy.mean())
    assert se2 > np.sqrt(est2 * (1 - est2) / 1000)
    assert np.isfinite(dof2)


def test_delta_contrast_is_accurate_for_large_totals():
    rng = np.random.default_rng(3)
    design = SurveyDesign.from_arrays(np.ones(12), np.repeat([0, 1, 2], 4), np.arange(12))
    infl = {"K": rng.normal(size=12) * 100.0, "N": rng.normal(size=12) * 1e5}
    ms = T.MarginSet({"K": 3.3e4, "N": 6.8e6}, infl, T.cluster_design(design))
    est, se = T.delta_contrast(ms, lambda m: m["K"] / m["N"])
    k, n = 3.3e4, 6.8e6
    z = infl["K"] / n - k / n**2 * infl["N"]
    exact = np.sqrt(T.cluster_design(design).vcov_total(z)[0, 0])
    assert est == pytest.approx(k / n)
    assert se == pytest.approx(exact, rel=1e-7)
    _, tot_se = T.delta_contrast(ms, lambda m: m["N"])
    exact_n = np.sqrt(T.cluster_design(design).vcov_total(infl["N"])[0, 0])
    assert tot_se == pytest.approx(exact_n, rel=1e-7)


def test_cross_margin_reproduces_surveylogit_margins_on_fit_rows():
    df, design = _two_periods(n=8000)
    mask = (df["YEAR"] == 2021).to_numpy()
    fit = T.fit_period(df, design, mask, ["z", "a"], "fatal", "P1")
    sub, sub_design = df.loc[mask], design.subset(mask)
    spec = ModelSpec(categorical={"z": ["no", "yes"], "a": ["x", "y"]})
    model = SurveyLogit(spec, ridge=T.RIDGE).fit(sub, sub["fatal"].to_numpy(), sub_design)
    m_ref, z_ref = model.margin_influence(sub, None)
    m, totals = T.cross_margin(fit, df, design, mask)
    assert m == pytest.approx(m_ref, rel=1e-10)
    np.testing.assert_allclose(totals, sub_design.cluster_totals(z_ref)[:, 0], atol=1e-12)
    # Fitted margin with an intercept equals the observed weighted share.
    w = design.weight[mask]
    assert m == pytest.approx(np.average(sub["fatal"], weights=w), rel=1e-3)


def test_pure_composition_change_is_attributed_to_composition():
    df, design = _two_periods(n=80000, seed=4, z_share=(0.1, 0.4))
    dec = _decompose(df, design)
    tab = T.decomposition_table(dec, design)
    total = _row(tab, "total_change")["estimate"]
    comp = _row(tab, "composition_effect_ref_P0")
    within = _row(tab, "within_effect_ref_P0")
    assert total > 0
    assert comp["estimate"] + within["estimate"] == pytest.approx(total)
    assert comp["low"] < total < comp["high"] or abs(comp["estimate"] - total) < 0.05
    assert within["low"] < 0 < within["high"]
    share = _row(tab, "composition_share_of_change_average")["estimate"]
    assert share == pytest.approx(1.0, abs=0.15)
    # Detailed contributions add up to the composition effect; Z carries it.
    by_factor, by_term = T.detailed_composition(dec, df, design)
    assert by_factor["contribution_pp"].sum() == pytest.approx(comp["estimate"], rel=1e-9)
    assert by_factor["share_of_composition_effect"].sum() == pytest.approx(1.0)
    z = by_factor.set_index("factor").loc["z"]
    assert z["share_of_composition_effect"] > 0.9
    assert set(by_term["term"]) == {"z[yes]", "a[y]"}


def test_pure_severity_change_is_attributed_within():
    df, design = _two_periods(n=80000, seed=9, intercepts=(-4.0, -3.6))
    dec = _decompose(df, design)
    tab = T.decomposition_table(dec, design)
    comp = _row(tab, "composition_effect_ref_P0")
    within = _row(tab, "within_effect_ref_P0")
    assert comp["low"] < 0 < comp["high"]
    assert within["low"] > 0
    rr = _row(tab, "risk_ratio_within_ref_P0")
    assert rr["low"] > 1


def test_kabco_shares_and_numerator_denominator_identity():
    rng = np.random.default_rng(2)
    n = 30000
    years = rng.choice(list(T.P0_YEARS + T.P1_YEARS), n)
    later = years >= 2020
    probs_p0 = [0.70, 0.15, 0.10, 0.04, 0.01]
    probs_p1 = [0.66, 0.15, 0.12, 0.05, 0.02]
    kab = np.where(
        later,
        rng.choice(5, n, p=probs_p1),
        rng.choice(5, n, p=probs_p0),
    ).astype(float)
    kab[rng.random(n) < 0.02] = np.nan
    df = pd.DataFrame({"YEAR": years, "kabco": kab})
    stratum = rng.integers(0, 4, n)
    design = SurveyDesign.from_arrays(
        rng.uniform(1, 3, n), stratum, stratum * 10 + rng.integers(0, 3, n)
    )
    ms = T.kabco_marginset(df, design)
    tab = T.kabco_by_year(ms, df)
    shares = tab[[f"{c}_share_of_known" for c in T.KABCO]].sum(axis=1)
    np.testing.assert_allclose(shares, 1.0)
    fars = pd.Series(1000.0, index=list(T.P0_YEARS + T.P1_YEARS))
    nd = T.numerator_denominator(ms, fars)
    comp = nd[nd["comparison"] == "2020-2024 vs 2016-2019"].set_index("quantity")["estimate"]
    assert comp["ratio_fatal_share"] == pytest.approx(
        comp["ratio_fatal_crashes_numerator"] / comp["ratio_reported_crashes_denominator"]
    )
    assert comp["numerator_share_of_log_rise"] + comp["denominator_share_of_log_rise"] == (
        pytest.approx(1.0)
    )
    assert comp["ratio_fatal_share"] > 1.5
    assert comp["FARS_ratio_fatal_crashes (census)"] == pytest.approx(1.0)


def test_fars_changes_arithmetic():
    comp = pd.DataFrame(
        {
            "YEAR": [2019, 2021, 2024],
            **{c: [100.0, 130.0, 120.0] for c in T.FARS_COUNTS},
        }
    )
    comp["speeding_crashes"] = [30.0, 45.0, 40.0]
    ch = T.fars_changes(comp).set_index("indicator")
    assert ch.loc["speeding_crashes", "change_2019_2021"] == 15
    assert ch.loc["speeding_crashes", "share_of_total_change_2019_2021"] == pytest.approx(0.5)
    assert ch.loc["fatal_crashes", "pct_change_2019_2024"] == pytest.approx(20.0)


def test_leakage_and_covariate_sets():
    T.check_leakage()
    assert "YEAR" not in T.COVARIATE_SETS["A"]
    assert set(T.COVARIATE_SETS["B"]) - set(T.COVARIATE_SETS["A"]) == {"crash_type", "n_vehicles"}


# --------------------------------------------------------------------------------------
@pytest.mark.processed
def test_real_data_decomposition_smoke():
    df_all, design_all = T.load()
    df, design = T.outcome_frame(df_all, design_all, "fatal")
    dec = T.decompose(df, design, T.COVARIATE_SETS["A"], "fatal", "smoke")
    tab = T.decomposition_table(dec, design)
    obs0 = _row(tab, "observed_share_P0")["estimate"]
    obs1 = _row(tab, "observed_share_P1")["estimate"]
    assert 0.004 < obs0 < 0.0055 and 0.0055 < obs1 < 0.007
    assert _row(tab, "fitted_share_P0")["estimate"] == pytest.approx(obs0, rel=2e-3)
    comp = _row(tab, "composition_effect_ref_P0")["estimate"]
    within = _row(tab, "within_effect_ref_P0")["estimate"]
    assert comp + within == pytest.approx(_row(tab, "total_change")["estimate"])
    assert bool(tab["converged"].all())
