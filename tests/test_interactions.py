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
