"""Factorial margins, interaction contrasts and suppression (synthetic data)."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import factorial as fa
from nhtsa_stats.analysis.survey import SurveyDesign


def _data(n: int = 6000, seed: int = 1, k: int = 3) -> tuple[pd.DataFrame, SurveyDesign]:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f"f{i}": rng.choice(["no", "yes"], n) for i in range(k)})
    df["cov"] = rng.choice(["a", "b"], n)
    eta = -2.0 + sum(0.6 * (df[f"f{i}"] == "yes") for i in range(k)) + 0.3 * (df["cov"] == "b")
    eta += 0.5 * ((df["f0"] == "yes") & (df["f1"] == "yes"))
    df["y"] = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    df["YEAR"] = 2020
    w = rng.uniform(0.5, 3.0, n)
    strata = np.repeat(np.arange(4), n // 4)
    psu = np.tile(np.arange(10), n // 10)
    return df, SurveyDesign.from_arrays(w, strata, psu)


FACTORS3 = [fa.Factor(f"f{i}", f"f{i}", ("yes",), ("no",)) for i in range(3)]


def test_keys_and_signs():
    assert fa.keys(2) == ["00", "01", "10", "11"]
    terms = dict(fa.subset_keys((0, 2), 3))
    assert terms == {"000": 1, "001": -1, "100": -1, "101": 1}


def test_product_terms_cover_all_subsets():
    assert len(fa.product_terms(FACTORS3)) == 4  # 3 pairs + 1 triple


def test_saturated_margins_equal_weighted_cell_means():
    df, design = _data()
    res = fa.fit_factorial(df, design, FACTORS3, [], "y", ridge=0.0, min_n=1, min_events=1)
    w = design.weight
    for key in fa.keys(3):
        mask = np.ones(len(df), bool)
        for i, b in enumerate(key):
            mask &= (df[f"f{i}"] == ("yes" if b == "1" else "no")).to_numpy()
        expected = np.average(df.loc[mask, "y"], weights=w[mask])
        assert res.margins.values[key] == pytest.approx(expected, rel=1e-6)


def test_contrast_arithmetic_matches_margins():
    df, design = _data()
    res = fa.fit_factorial(df, design, FACTORS3, ["cov"], "y", min_n=1, min_events=1)
    m = res.margins.values
    tab = fa.interaction_table(res).set_index("contrast")
    pair = tab.loc["f0 x f1"]
    assert pair["additive_contrast"] == pytest.approx(m["110"] - m["100"] - m["010"] + m["000"])
    assert pair["multiplicative_ratio"] == pytest.approx(
        m["110"] * m["000"] / (m["100"] * m["010"])
    )
    three = tab.loc["f0 x f1 x f2"]
    expected = sum(
        (-1) ** (3 - sum(b)) * m["".join(map(str, b))] for b in itertools.product((0, 1), repeat=3)
    )
    assert three["additive_contrast"] == pytest.approx(expected)
    # The data were generated with a positive f0 x f1 log-odds interaction.
    assert pair["additive_contrast"] > 0
    single = fa.single_factor_table(res)
    row = single[(single.factor == "f0") & (single.key_reference == "000")].iloc[0]
    assert row["rr"] == pytest.approx(m["100"] / m["000"])


def test_order_invariance_of_contrasts():
    """Permuting the factor order permutes the keys but not the estimates."""
    df, design = _data(seed=3)
    a = fa.fit_factorial(df, design, FACTORS3, ["cov"], "y", min_n=1, min_events=1)
    b = fa.fit_factorial(df, design, FACTORS3[::-1], ["cov"], "y", min_n=1, min_events=1)
    assert a.margins.values["110"] == pytest.approx(b.margins.values["011"], rel=1e-8)
    ta = fa.interaction_table(a).set_index("contrast")
    tb = fa.interaction_table(b).set_index("contrast")
    assert ta.loc["f0 x f1 x f2", "additive_contrast"] == pytest.approx(
        tb.loc["f2 x f1 x f0", "additive_contrast"], rel=1e-8
    )


def test_suppression_propagates():
    df, design = _data()
    # Make the all-exposed cell tiny.
    full = (df[["f0", "f1", "f2"]] == "yes").all(axis=1)
    drop = df.index[full][5:]
    keep = ~df.index.isin(drop)
    df2 = df[keep].reset_index(drop=True)
    d2 = design.subset(keep)
    res = fa.fit_factorial(df2, d2, FACTORS3, [], "y")
    assert "111" in res.suppressed
    mt = fa.margins_table(res).set_index("key")
    assert np.isnan(mt.loc["111", "adj_risk"]) and mt.loc["111", "flag"]
    it = fa.interaction_table(res).set_index("contrast")
    assert np.isnan(it.loc["f0 x f1 x f2", "additive_contrast"])
    assert np.isfinite(it.loc["f0 x f1", "additive_contrast"])  # does not use cell 111


def test_unknown_levels_kept_separate():
    df, design = _data()
    df.loc[df.index[:300], "f2"] = "unknown"
    res = fa.fit_factorial(df, design, FACTORS3, [], "y", min_n=1, min_events=1)
    assert "f2[unknown]" in res.model.names_
    sup = res.support.set_index("key")
    # Rows with unknown f2 are in no observed cell but stay in the standardisation population.
    assert sup["n"].sum() == len(df) - 300


def test_missing_values_rejected():
    df, design = _data()
    df.loc[0, "cov"] = None
    with pytest.raises(ValueError, match="missing"):
        fa.fit_factorial(df, design, FACTORS3, ["cov"], "y")


def test_holm():
    p = pd.Series([0.01, 0.04, np.nan, 0.03])
    adj = fa.holm(p)
    assert adj[0] == pytest.approx(0.03)
    assert adj[3] == pytest.approx(0.06)
    assert adj[1] == pytest.approx(0.06)
    assert np.isnan(adj[2])


def test_saturated_in_all_levels_is_calibrated_within_recorded_cells():
    """With products over every observed level (unknown included), weighted predictions sum to
    weighted events in every recorded factor cell (score equations; no ridge)."""
    df, design = _data(seed=5)
    df.loc[df.index[:500], "f1"] = "unknown"
    res = fa.fit_factorial(df, design, FACTORS3[:2], ["cov"], "y", ridge=0.0, min_n=1, min_events=1)
    pred = res.model.predict(df)
    w = design.weight
    for a in ("no", "yes"):
        for b in ("no", "yes", "unknown"):
            m = ((df["f0"] == a) & (df["f1"] == b)).to_numpy()
            assert np.sum(w[m] * pred[m]) == pytest.approx(np.sum(w[m] * df.loc[m, "y"]), rel=1e-6)
    assert "f0{yes}:f1{unknown}" in res.model.names_


def test_product_terms_with_levels():
    terms = fa.product_terms(FACTORS3[:2], {"f0": ["no", "yes"], "f1": ["no", "yes", "unknown"]})
    assert len(terms) == 2
