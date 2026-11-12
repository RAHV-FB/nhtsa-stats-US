"""Interaction machinery on synthetic data (software tests only)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import interactions as it
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit, interaction_contrasts


def _synthetic(n: int = 20_000, seed: int = 3) -> tuple[pd.DataFrame, np.ndarray, SurveyDesign]:
    rng = np.random.default_rng(seed)
    a = rng.choice(["no", "yes", "unknown"], n, p=[0.7, 0.25, 0.05])
    b = rng.choice(["low1", "low2", "high1", "high2"], n)
    eta = (
        -3
        + 0.7 * (a == "yes")
        + 0.5 * np.isin(b, ["high1", "high2"])
        + 0.6 * ((a == "yes") & np.isin(b, ["high1", "high2"]))
    )
    y = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    clus = rng.integers(0, 60, n)
    design = SurveyDesign.from_arrays(rng.uniform(0.5, 2, n), clus // 10, clus)
    return pd.DataFrame({"a": a, "b": b}), y, design


def test_product_term_column():
    df = pd.DataFrame({"a": ["yes", "no", "yes"], "b": ["high1", "high2", "low1"]})
    spec = ModelSpec(
        categorical={"a": ["no", "yes"]}, products=[(("a", ["yes"]), ("b", ["high1", "high2"]))]
    )
    x, names = spec.design_matrix(df)
    assert names[-1] == "a{yes}:b{high1|high2}"
    np.testing.assert_array_equal(x[:, -1], [1.0, 0.0, 0.0])


def test_group_margins_are_level_mixtures():
    df, y, design = _synthetic()
    comb = it.Combination(
        "a x high",
        (
            it.Exposure("a", ("yes",), ("no",), "a"),
            it.Exposure("b", ("high1", "high2"), ("low1", "low2"), "b high"),
        ),
    )
    spec = ModelSpec(
        categorical={"a": ["no", "yes", "unknown"], "b": ["low1", "low2", "high1", "high2"]},
        products=[(("a", ["yes"]), ("b", ["high1", "high2"]))],
    )
    model = SurveyLogit(spec).fit(df, y, design)
    ms = it.combo_margins(model, df, design, comb)
    # p11 must equal the weighted mixture of the two level-specific margins.
    w = design.weight
    share_h1 = w[df.b == "high1"].sum() / w[df.b.isin(["high1", "high2"])].sum()
    m_h1, _ = model.margin_influence(df, lambda d: d.assign(a="yes", b="high1"))
    m_h2, _ = model.margin_influence(df, lambda d: d.assign(a="yes", b="high2"))
    assert ms.values["p11"] == pytest.approx(share_h1 * m_h1 + (1 - share_h1) * m_h2)
    # The simulated positive interaction is recovered on the additive scale.
    ic = interaction_contrasts(ms, "p11", "p10", "p01", "p00")["ic"]
    assert ic.estimate > 0


def test_indicator_handles_other_levels():
    df = pd.DataFrame({"a": ["yes", "no", "unknown"]})
    ind = it._indicator(df, it.Exposure("a", ("yes",), ("no",), "a"))
    assert ind[0] == 1 and ind[1] == 0 and np.isnan(ind[2])


def test_holm_and_bh():
    p = pd.Series([0.01, 0.04, 0.03, 0.5])
    holm = it._adjust_p(p, "holm")
    np.testing.assert_allclose(holm.to_numpy(), [0.04, 0.09, 0.09, 0.5])
    bh = it._adjust_p(p, "bh")
    np.testing.assert_allclose(bh.to_numpy(), [0.04, 0.0533333, 0.0533333, 0.5], rtol=1e-5)


def test_pairs_use_registered_covariates_only():
    from nhtsa_stats.processing.harmonize import assert_no_leakage

    for comb in it.PAIRS + it.TRIPLES:
        assert_no_leakage([c for c in it._covariates(comb) if c != "YEAR"])


def test_group_margin_se_matches_analytic_mixture_variance():
    # Saturated (a x b) model: the margin that sets a='yes' and mixes b over the 'high' levels
    # is sum_l s_l * ybar(yes, l), s_l the weight shares.  Its SE is the design-based SE of that
    # linear combination of domain means, computed here from first principles.
    df, y, design = _synthetic()
    spec = ModelSpec(
        categorical={"a": ["no", "yes", "unknown"], "b": ["low1", "low2", "high1", "high2"]},
        interactions=[("a", "b")],
    )
    model = SurveyLogit(spec).fit(df, y, design)
    comb = it.Combination(
        "a x high",
        (
            it.Exposure("a", ("yes",), ("no",), "a"),
            it.Exposure("b", ("high1", "high2"), ("low1", "low2"), "b high"),
        ),
    )
    ms = it.combo_margins(model, df, design, comb)
    w = design.weight
    high = ["high1", "high2"]
    z = np.zeros(len(df))
    value = 0.0
    for lv in high:
        s_l = w[df.b == lv].sum() / w[df.b.isin(high)].sum()
        cell = ((df.a == "yes") & (df.b == lv)).to_numpy()
        ybar = (w[cell] * y[cell]).sum() / w[cell].sum()
        value += s_l * ybar
        z += s_l * np.where(cell, w * (y - ybar), 0.0) / w[cell].sum()
    assert ms.values["p11"] == pytest.approx(value, rel=1e-6)
    assert ms.estimate("p11").se == pytest.approx(
        float(np.sqrt(design.vcov_total(z)[0, 0])), rel=1e-5
    )


def _pair_data(n: int = 40_000, seed: int = 11):
    rng = np.random.default_rng(seed)
    a = rng.choice(["no", "yes"], n, p=[0.8, 0.2])
    b = rng.choice(["no", "yes"], n, p=[0.7, 0.3])
    cov = rng.choice(["no", "yes"], n)
    coef = {"int": -3.0, "a": 0.8, "b": 0.5, "ab": 0.9}
    eta = (
        coef["int"]
        + coef["a"] * (a == "yes")
        + coef["b"] * (b == "yes")
        + coef["ab"] * ((a == "yes") & (b == "yes"))
    )
    p = 1 / (1 + np.exp(-eta))
    y = (rng.random(n) < p).astype(float)
    clus = rng.integers(0, 80, n)
    design = SurveyDesign.from_arrays(np.ones(n), clus // 20, clus)
    df = pd.DataFrame({"speeding": a, "alcohol_im": b, "weekend": cov, "YEAR": 2016, "y": y})
    return df, design, coef


def test_analyse_pair_end_to_end_recovers_known_interaction(monkeypatch):
    df, design, coef = _pair_data()
    monkeypatch.setattr(it.specs, "PRE_CRASH", ["weekend"])
    monkeypatch.setattr(it.h, "assert_no_leakage", lambda *a, **k: None)
    comb = it.Combination("speeding x alcohol", (it.SPEEDING, it.ALCOHOL))
    rec = it.analyse_pair(df, design, "y", comb, n_years=1)

    def expit(x):
        return 1 / (1 + np.exp(-x))

    p00 = expit(coef["int"])
    p10 = expit(coef["int"] + coef["a"])
    p01 = expit(coef["int"] + coef["b"])
    p11 = expit(coef["int"] + coef["a"] + coef["b"] + coef["ab"])
    truth = {
        "adj_p00": p00,
        "adj_p11": p11,
        "ic": p11 - p10 - p01 + p00,
        "ratio_of_rr": (p11 / p01) / (p10 / p00),
        "rr_A_given_B0": p10 / p00,
    }
    for key, true in truth.items():
        lo, hi = rec[key + "_low"], rec[key + "_high"]
        assert lo < true < hi, (key, lo, true, hi)
    # The product-term odds ratio recovers exp(interaction coefficient) and the test rejects.
    assert rec["product_or_low"] < np.exp(coef["ab"]) < rec["product_or_high"]
    assert rec["product_p"] < 0.01 and rec["ic_p"] < 0.01
    assert rec["ratio_of_rr"] == pytest.approx(
        rec["rr_A_given_B1"] / rec["rr_A_given_B0"], rel=1e-9
    )
    assert rec["flag"] == "" and rec["prespecified"] is True


def test_holm_applied_over_prespecified_pairs_only():
    res = pd.DataFrame(
        {
            "pair": ["p1", "p2", "p3", "x1"],
            "prespecified": [True, True, True, False],
            "flag": ["", "", "", ""],
            "ic_p": [0.01, 0.04, 0.03, 0.0001],
        }
    )
    out = it._holm_family(res.copy())
    # Family of 3: sorted 0.01, 0.03, 0.04 -> 0.03, 0.06, 0.06.  The exploratory pair, though
    # it has the smallest p, neither enters the family nor receives an adjusted value.
    np.testing.assert_allclose(out.loc[:2, "ic_p_holm"], [0.03, 0.06, 0.06])
    assert np.isnan(out.loc[3, "ic_p_holm"]) and np.isnan(out.loc[3, "ic_p_bh"])


def test_failed_prespecified_pair_raises_but_exploratory_failure_is_reported():
    base = pd.DataFrame(
        {
            "pair": ["p1", "p2", "x1"],
            "prespecified": [True, True, False],
            "flag": ["", "", ""],
            "ic_p": [0.01, 0.04, 0.5],
        }
    )
    bad = base.copy()
    bad.loc[1, ["flag", "ic_p"]] = ["failed: singular matrix", np.nan]
    with pytest.raises(RuntimeError, match="p2"):
        it._holm_family(bad)
    expl = base.copy()
    expl.loc[2, ["flag", "ic_p"]] = ["failed: singular matrix", np.nan]
    out = it._holm_family(expl)
    assert out.loc[2, "flag"].startswith("failed")
    np.testing.assert_allclose(out.loc[:1, "ic_p_holm"], [0.02, 0.04])


def test_run_pairs_records_prespecified_flag_on_failed_rows(monkeypatch):
    # A failing exploratory pair carries prespecified=False (it used to be NaN -> filled True).
    def boom(*a, **k):
        raise ValueError("boom")

    monkeypatch.setattr(it, "analyse_pair", boom)
    monkeypatch.setattr(it.severity, "load", lambda o, y: (pd.DataFrame({"YEAR": [2016]}), None))
    monkeypatch.setattr(it, "PAIRS", [])
    res = it.run_pairs("fatal")
    assert res["prespecified"].eq(False).all() and res["flag"].str.startswith("failed").all()
    # The same failure in a pre-specified pair aborts the run.
    monkeypatch.setattr(it, "PAIRS", [it.Combination("x", it.FOLLOW_UP[0].exposures)])
    with pytest.raises(RuntimeError, match="pre-specified"):
        it.run_pairs("fatal")


def test_linked_variables_move_with_the_exposure():
    # Setting crash_type to 'pedestrian' must carry n_vehicles from pedestrian crashes, never
    # attach a multi-vehicle count to a single-vehicle crash type.
    df = pd.DataFrame(
        {
            "crash_type": ["pedestrian"] * 6 + ["mv_angle"] * 3 + ["sv_on_roadway"] * 3,
            "n_vehicles": ["1"] * 5 + ["2"] + ["2", "2", "3+"] + ["1"] * 3,
        }
    )
    w = np.ones(len(df))
    ped = it.PEDESTRIAN
    assert ped.linked == ("n_vehicles",)
    exposed = it._level_weights(df, w, ped, 1)
    assert exposed == {("pedestrian", "1"): pytest.approx(5 / 6), ("pedestrian", "2"): 1 / 6}
    ref = it._level_weights(df, w, ped, 0)
    assert set(ref) == {("mv_angle", "2"), ("mv_angle", "3+"), ("sv_on_roadway", "1")}
    assert sum(ref.values()) == pytest.approx(1.0)
