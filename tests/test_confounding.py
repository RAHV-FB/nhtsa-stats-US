"""Tests of the confounding-decomposition machinery (synthetic data = software tests only)."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import confounding as C
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit


# --------------------------------------------------------------------------------------
# Synthetic survey data with confounding
# --------------------------------------------------------------------------------------
def _synthetic(n: int = 6000, seed: int = 3) -> tuple[pd.DataFrame, SurveyDesign]:
    """Exposure E (night-like) depends on confounder Z; risk is log-linear in E and Z."""
    rng = np.random.default_rng(seed)
    stratum = rng.integers(0, 4, n)
    cluster = stratum * 10 + rng.integers(0, 3, n)  # 3 PSUs per stratum
    z = rng.random(n) < 0.3
    e = rng.random(n) < np.where(z, 0.6, 0.15)
    a = rng.choice(["x", "y", "z"], n)
    risk = 0.02 * np.where(e, 2.0, 1.0) * np.where(z, 4.0, 1.0) * np.where(a == "y", 1.5, 1.0)
    y = (rng.random(n) < risk).astype(float)
    df = pd.DataFrame(
        {
            "night_period": np.where(e, "night", "day"),
            "alcohol_im": np.where(z, "yes", "no"),
            "region": np.where(a == "x", "south", np.where(a == "y", "west", "midwest")),
            "YEAR": rng.choice([2016, 2017, 2018], n),
            "fatal": y,
        }
    )
    w = rng.uniform(1, 5, n)
    return df, SurveyDesign.from_arrays(w, stratum, cluster)


TOY = C.Exposure(
    "night", "night_period", "day", "night", ("calendar_region", "alcohol"), "synthetic"
)


# --------------------------------------------------------------------------------------
def test_collapsed_fit_equals_row_level_fit():
    df, design = _synthetic()
    covs = ["night_period", "alcohol_im", "region"]
    spec = ModelSpec(categorical={c: sorted(df[c].unique()) for c in covs})
    spec.categorical["night_period"] = ["day", "night"]
    y = df["fatal"].to_numpy()
    row = SurveyLogit(spec, ridge=0.5).fit(df, y, design)
    cells, cdesign = C.collapse_cells(df, design, covs, "fatal")
    assert len(cells) < len(df) / 10
    assert cdesign.weight.sum() == pytest.approx(design.weight.sum())
    col = SurveyLogit(spec, ridge=0.5 * len(cells) / len(df)).fit(
        cells, cells["fatal"].to_numpy(), cdesign
    )
    np.testing.assert_allclose(col.coef_, row.coef_, rtol=1e-8, atol=1e-10)
    np.testing.assert_allclose(col.vcov_, row.vcov_, rtol=1e-6, atol=1e-12)
    scen = {"e": lambda d: d.assign(night_period="night")}
    m_row = row.margins(df, scen)
    m_col = col.margins(cells, scen)
    assert m_col.values["e"] == pytest.approx(m_row.values["e"], rel=1e-9)
    np.testing.assert_allclose(
        cdesign.cluster_totals(m_col.influence["e"]),
        design.cluster_totals(m_row.influence["e"]),
        rtol=1e-6,
        atol=1e-12,
    )


def test_cluster_design_reproduces_row_variance():
    df, design = _synthetic()
    z = design.weight * df["fatal"].to_numpy()
    totals = design.cluster_totals(z)
    cd = C.cluster_design(design)
    assert cd.df == design.df
    assert cd.vcov_total(totals)[0, 0] == pytest.approx(design.vcov_total(z)[0, 0], rel=1e-12)


def test_fit_subset_recovers_standardised_rr_under_confounding():
    df, design = _synthetic(n=60000, seed=11)
    crude = C.fit_subset(df, design, TOY, [], "fatal")
    adj = C.fit_subset(df, design, TOY, ["alcohol", "calendar_region"], "fatal")
    # Crude RR is confounded upwards by Z; adjusted RR close to the true (collapsible) RR 2.
    assert np.exp(crude.log_rr) > 2.6
    assert np.exp(adj.log_rr) == pytest.approx(2.0, abs=0.25)
    # Crude margins equal the observed weighted rates (saturated model, tiny ridge).
    w = design.weight
    e = (df["night_period"] == "night").to_numpy()
    y = df["fatal"].to_numpy()
    assert crude.m_exposed == pytest.approx(np.average(y[e], weights=w[e]), rel=1e-3)
    assert crude.m_reference == pytest.approx(np.average(y[~e], weights=w[~e]), rel=1e-3)


def test_lattice_tables_shapley_efficiency_and_orderings():
    df, design = _synthetic(n=20000, seed=5)
    lat = C.fit_lattice(df, design, TOY, "fatal")
    assert len(lat) == 4
    ms = C.lattice_marginset(lat, design)
    shap = C.shapley_table(lat, ms, TOY, "fatal")
    # Contributions plus the retained share sum to 1 (efficiency).
    assert shap["shapley_share_of_crude"].sum() == pytest.approx(1.0, abs=1e-9)
    alc = shap.set_index("block").loc["alcohol"]
    assert alc["share_low"] < alc["shapley_share_of_crude"] < alc["share_high"]
    assert alc["shapley_share_of_crude"] > 0.2
    seq = C.sequential_table(lat, ms, TOY, "fatal")
    prim = seq[seq["ordering"] == "primary"]
    assert prim["step"].tolist() == [0, 1, 2]
    assert prim["share_logrr_retained"].iloc[0] == pytest.approx(1.0)
    # Step removals telescope to 1 - retained share.
    last = prim.iloc[-1]
    assert prim["share_removed_this_step"].iloc[1:].sum() == pytest.approx(
        1 - last["share_logrr_retained"], abs=1e-9
    )
    assert (seq["rr_low"] < seq["rr"]).all() and (seq["rr"] < seq["rr_high"]).all()


def test_linear_and_ratio_contrasts_match_numeric_delta_method():
    df, design = _synthetic(n=8000, seed=2)
    lat = C.fit_lattice(df, design, TOY, "fatal")
    ms = C.lattice_marginset(lat, design)
    keys = ["lr|crude", "lr|alcohol"]
    est, se = C.ratio_contrast(ms, {keys[1]: 1.0}, {keys[0]: 1.0})
    num = ms.contrast(lambda m: m[keys[1]] / m[keys[0]])
    assert est == pytest.approx(num.estimate)
    assert se == pytest.approx(num.se, rel=1e-4)
    est, se = C.linear_contrast(ms, {keys[0]: 1.0, keys[1]: -1.0})
    num = ms.difference(keys[0], keys[1])
    assert est == pytest.approx(num.estimate)
    assert se == pytest.approx(num.se, rel=1e-4)


def test_shapley_values_additive_game_and_symmetry():
    players = ["a", "b", "c", "d"]
    a = {"a": 0.3, "b": -0.1, "c": 0.0, "d": 0.25}
    phi = C.shapley_values(lambda s: 1.0 - sum(a[j] for j in s), players)
    for j in players:
        assert phi[j] == pytest.approx(a[j])
    # Pure interaction between a and b: split equally; c, d get nothing.
    phi = C.shapley_values(lambda s: -1.0 if {"a", "b"} <= s else 0.0, players)
    assert phi["a"] == pytest.approx(0.5) and phi["b"] == pytest.approx(0.5)
    assert phi["c"] == pytest.approx(0.0) and phi["d"] == pytest.approx(0.0)
    # Efficiency for an arbitrary game.
    rng = np.random.default_rng(0)
    vals = {
        frozenset(s): rng.normal() for r in range(5) for s in itertools.combinations(players, r)
    }
    phi = C.shapley_values(lambda s: vals[s], players)
    assert sum(phi.values()) == pytest.approx(vals[frozenset()] - vals[frozenset(players)])


def test_exposure_definitions_exclude_the_exposure_itself():
    for ex in C.EXPOSURES.values():
        covs = ex.variables(ex.blocks)
        assert ex.column not in covs
        assert len(ex.blocks) == 8
        for name, order in C.orderings(ex).items():
            expected = set(ex.blocks) - ({"light"} if name == "primary_without_light" else set())
            assert set(order) == expected and len(order) == len(expected)
    night_covs = C.EXPOSURES["night"].variables(C.EXPOSURES["night"].blocks)
    assert "tod" not in night_covs and "night" not in night_covs
    assert "urbanicity" not in C.EXPOSURES["rural"].variables(C.EXPOSURES["rural"].blocks)
    C.check_leakage()


def test_outcome_definition_sensitivity_identical_and_selective_outcomes():
    df, design = _synthetic(n=20000, seed=7)
    primary = {
        k: C.fit_subset(df, design, TOY, s, "fatal") for k, s in C.summary_models(TOY).items()
    }
    # Identical outcome on every crash: identical RRs, ratio exactly 1 with no spread.
    df["fatal_cc"] = df["fatal"]
    tab = C.outcome_definition_sensitivity(df, design, TOY, primary).set_index("model")
    assert list(tab.index) == ["crude", "all_blocks"]
    np.testing.assert_allclose(tab["rr_cc"], tab["rr_imputed"], rtol=1e-8)
    np.testing.assert_allclose(tab["rr_ratio_cc_over_imputed"], 1.0, atol=1e-8)
    np.testing.assert_allclose(tab["rr_ratio_high"] - tab["rr_ratio_low"], 0.0, atol=1e-6)
    assert tab.loc["crude", "share_logrr_retained_cc"] == 1.0
    full = tab.loc["all_blocks"]
    assert full["share_retained_cc_low"] < full["share_logrr_retained_cc"]
    assert full["share_logrr_retained_cc"] < full["share_retained_cc_high"]
    # Undetermined only among non-fatal exposed crashes: the complete-case RR is inflated.
    rng = np.random.default_rng(1)
    drop = (df["night_period"] == "night").to_numpy() & (df["fatal"] == 0).to_numpy()
    df["fatal_cc"] = np.where(drop & (rng.random(len(df)) < 0.3), np.nan, df["fatal"])
    tab = C.outcome_definition_sensitivity(df, design, TOY, primary).set_index("model")
    assert tab.loc["crude", "n_complete_case"] < tab.loc["crude", "n_imputed"]
    assert tab.loc["crude", "rr_ratio_low"] > 1.2


def test_category_levels_rejects_undeclared_values():
    df = pd.DataFrame({"light": ["daylight", "dark_lighted", "moonlight"]})
    with pytest.raises(ValueError):
        C.category_levels(df, "light")


# --------------------------------------------------------------------------------------
@pytest.mark.processed
def test_real_data_night_crude_and_adjusted():
    df, design = C.load_frame()
    assert len(df) > 400_000
    ex = C.EXPOSURES["night"]
    crude = C.fit_subset(df, design, ex, [], "fatal")
    w = design.weight
    for level, m in (("night", crude.m_exposed), ("day", crude.m_reference)):
        d = (df[C.NIGHT_COLUMN] == level).to_numpy()
        assert m == pytest.approx(np.average(df["fatal"].to_numpy()[d], weights=w[d]), rel=1e-3)
    assert np.exp(crude.log_rr) > 1.5
    adj = C.fit_subset(df, design, ex, ["calendar_area", "alcohol", "speeding"], "fatal")
    assert adj.converged
    assert 1.0 < np.exp(adj.log_rr) < np.exp(crude.log_rr)
    overlap = C.night_light_overlap(df, design)
    night_day = overlap[(overlap["period"] == "night") & (overlap["light"] == "daylight")]
    assert float(night_day["weighted_share_of_period"].iloc[0]) < 0.05
