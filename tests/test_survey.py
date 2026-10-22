"""Unit tests of the design-based estimators on synthetic data (software tests only)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from nhtsa_stats.analysis.survey import (
    ModelSpec,
    SurveyDesign,
    SurveyLogit,
    interaction_contrasts,
    logit_ci,
    proportion_table,
    svy_mean,
    svy_total,
)


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(7)


def test_srs_mean_matches_textbook(rng):
    y = rng.normal(size=500)
    d = SurveyDesign.from_arrays(np.ones(500), None, None)
    est = svy_mean(d, y)
    assert est.estimate == pytest.approx(y.mean())
    assert est.se == pytest.approx(y.std(ddof=1) / np.sqrt(500), rel=1e-10)


def test_total_variance_stratified_cluster_by_hand():
    # Two strata, two clusters each, known cluster totals.
    w = np.array([1, 1, 2, 2, 1, 3], dtype=float)
    y = np.array([1, 0, 1, 1, 0, 1], dtype=float)
    strata = np.array([0, 0, 0, 0, 1, 1])
    clus = np.array([0, 0, 1, 1, 2, 3])
    d = SurveyDesign.from_arrays(w, strata, clus)
    # cluster totals of w*y: c0 = 1, c1 = 4, c2 = 0, c3 = 3
    v_expected = 2 / 1 * ((1 - 2.5) ** 2 + (4 - 2.5) ** 2) + 2 / 1 * (
        (0 - 1.5) ** 2 + (3 - 1.5) ** 2
    )
    est = svy_total(d, y)
    assert est.estimate == pytest.approx(8.0)
    assert est.se**2 == pytest.approx(v_expected)
    assert d.df == 2


def test_domain_keeps_cluster_universe():
    w = np.ones(6)
    d = SurveyDesign.from_arrays(w, [0, 0, 0, 1, 1, 1], [0, 1, 2, 3, 4, 5])
    sub = d.subset(np.array([True, True, False, False, False, False]))
    assert sub.n_clusters == d.n_clusters
    assert sub.df == d.df


def _sim_logit(rng, n=4000, n_clusters=40):
    clus = rng.integers(0, n_clusters, n)
    strata = clus // 10
    u = rng.normal(scale=0.5, size=n_clusters)[clus]
    a = rng.integers(0, 2, n)
    b = rng.integers(0, 2, n)
    x = rng.normal(size=n)
    eta = -2 + 0.8 * a + 0.5 * b + 0.6 * a * b + 0.3 * x + u
    y = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    w = rng.uniform(0.5, 3, n)
    df = pd.DataFrame({"a": a, "b": b, "x": x})
    return df, y, w, strata, clus


def test_logit_matches_statsmodels_point_estimates_and_cluster_se(rng):
    df, y, w, _, clus = _sim_logit(rng)
    spec = ModelSpec(
        categorical={"a": [0, 1], "b": [0, 1]}, numeric=["x"], interactions=[("a", "b")]
    )
    design = SurveyDesign.from_arrays(w, None, clus)
    m = SurveyLogit(spec).fit(df, y, design)
    x, _ = spec.design_matrix(df)
    ref = sm.GLM(y, x, family=sm.families.Binomial(), freq_weights=w / w.mean()).fit()
    np.testing.assert_allclose(m.coef_, ref.params, rtol=1e-6, atol=1e-8)
    # Single stratum: our variance = G/(G-1) * (uncorrected statsmodels cluster sandwich).
    g = design.n_clusters
    ref_cl = sm.GLM(y, x, family=sm.families.Binomial(), var_weights=w / w.mean()).fit(
        cov_type="cluster", cov_kwds={"groups": clus, "use_correction": False}
    )
    np.testing.assert_allclose(m.vcov_, ref_cl.cov_params() * g / (g - 1), rtol=1e-5)
    assert m.converged_


def test_saturated_margins_equal_weighted_group_rates(rng):
    df, y, w, strata, clus = _sim_logit(rng)
    spec = ModelSpec(categorical={"a": [0, 1]})
    design = SurveyDesign.from_arrays(w, strata, clus)
    m = SurveyLogit(spec).fit(df, y, design)
    ms = m.margins(df, {"a1": lambda d: d.assign(a=1), "a0": lambda d: d.assign(a=0)})
    for lv, name in ((1, "a1"), (0, "a0")):
        dom = df["a"].to_numpy() == lv
        assert ms.values[name] == pytest.approx(np.average(y[dom], weights=w[dom]), rel=1e-8)
    # In a saturated model the margin's linearised SE equals the domain-mean SE.
    direct = svy_mean(design, y, df["a"].to_numpy() == 1)
    assert ms.estimate("a1").se == pytest.approx(direct.se, rel=1e-6)


def test_interaction_contrast_arithmetic(rng):
    df, y, w, strata, clus = _sim_logit(rng)
    spec = ModelSpec(
        categorical={"a": [0, 1], "b": [0, 1]}, numeric=["x"], interactions=[("a", "b")]
    )
    design = SurveyDesign.from_arrays(w, strata, clus)
    m = SurveyLogit(spec).fit(df, y, design)
    sc = {f"p{i}{j}": (lambda d, i=i, j=j: d.assign(a=i, b=j)) for i in (0, 1) for j in (0, 1)}
    ms = m.margins(df, sc)
    out = interaction_contrasts(ms, "p11", "p10", "p01", "p00")
    v = ms.values
    assert out["ic"].estimate == pytest.approx(v["p11"] - v["p10"] - v["p01"] + v["p00"])
    assert out["reri"].estimate == pytest.approx(
        v["p11"] / v["p00"] - v["p10"] / v["p00"] - v["p01"] / v["p00"] + 1
    )
    assert out["ic"].se > 0


def test_wald_test_and_coef_table(rng):
    df, y, w, strata, clus = _sim_logit(rng)
    spec = ModelSpec(categorical={"a": [0, 1], "b": [0, 1]}, interactions=[("a", "b")])
    m = SurveyLogit(spec).fit(df, y, SurveyDesign.from_arrays(w, strata, clus))
    tab = m.coef_table()
    assert list(tab["term"]) == ["Intercept", "a[1]", "b[1]", "a[1]:b[1]"]
    res = m.wald_test(["a[1]:b[1]"])
    assert 0 <= res["p"] <= 1


def test_modelspec_rejects_undeclared_levels():
    spec = ModelSpec(categorical={"a": ["x", "y"]})
    with pytest.raises(ValueError, match="outside declared levels"):
        spec.design_matrix(pd.DataFrame({"a": ["x", "z"]}))


def test_proportion_table_flags_small_cells(rng):
    n = 200
    df = pd.DataFrame(
        {"g": ["big"] * 190 + ["small"] * 10, "y": rng.integers(0, 2, n).astype(float)}
    )
    df.loc[0, "y"] = np.nan  # unknown outcome excluded from denominator
    d = SurveyDesign.from_arrays(np.ones(n), None, None)
    tab = proportion_table(df, d, "y", "g", min_n=30)
    small = tab[tab.g == "small"].iloc[0]
    big = tab[tab.g == "big"].iloc[0]
    assert small.flag == "suppressed"
    assert big.n == 189


def test_logit_ci_bounds():
    lo, hi = logit_ci(0.01, 0.005, 40)
    assert 0 < lo < 0.01 < hi < 1
