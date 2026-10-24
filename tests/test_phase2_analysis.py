"""Phase-2 analysis helpers: E-values, attributable-fraction Shapley allocation, overlap
arithmetic, case explorer arithmetic and the stratified bias analysis (synthetic inputs)."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import cases, contributions, speeding, stages
from nhtsa_stats.analysis.survey import SurveyDesign


def test_e_value_known_values():
    assert speeding.e_value(1.0) == pytest.approx(1.0)
    assert speeding.e_value(2.0) == pytest.approx(2 + np.sqrt(2))
    # Protective RRs are inverted.
    assert speeding.e_value(0.5) == pytest.approx(speeding.e_value(2.0))
    assert np.isnan(speeding.e_value(-1.0))


def test_e_values_ci_crossing_one():
    km = pd.DataFrame(
        [
            {
                "exposure": "x",
                "outcome": "fatal",
                "model": "m",
                "rr": 1.5,
                "rr_low": 0.9,
                "rr_high": 2.5,
            }
        ]
    )
    st = pd.DataFrame(columns=["exposure", "outcome", "stratum", "rr", "rr_low", "rr_high"])
    out = speeding.e_values(km, st)
    assert out.loc[0, "e_value_ci"] == 1.0


def _margins_dict(names, af_of):
    """Margins such that AF(S) = af_of(S) with M_obs = 1."""
    m = {"obs": 1.0}
    for r in range(1, len(names) + 1):
        for s in itertools.combinations(names, r):
            m[contributions._key(names, s)] = 1 - af_of(frozenset(s))
    return m


@pytest.mark.parametrize("n_players", [2, 3])
def test_shapley_af_efficiency_and_symmetry(n_players):
    names = ["a", "b", "c"][:n_players]
    rng = np.random.default_rng(1)
    base = {p: rng.uniform(0.05, 0.2) for p in names}

    def af_of(s):  # sub-additive: joint AF smaller than the sum of singles
        return 1 - np.prod([1 - base[p] for p in s])

    m = _margins_dict(names, af_of)
    phis = {j: contributions._shapley_af(names, j)(m) for j in names}
    assert sum(phis.values()) == pytest.approx(af_of(frozenset(names)))
    # Order invariance: relabelling players does not change each player's value.
    rev = names[::-1]
    m_rev = _margins_dict(rev, af_of)
    for j in names:
        assert contributions._shapley_af(rev, j)(m_rev) == pytest.approx(phis[j])


def test_two_player_shapley_closed_form():
    names = ["s", "a"]
    afs = {frozenset({"s"}): 0.09, frozenset({"a"}): 0.20, frozenset({"s", "a"}): 0.26}
    m = _margins_dict(names, lambda s: afs[s])
    phi_s = contributions._shapley_af(names, "s")(m)
    assert phi_s == pytest.approx(0.5 * (0.09 + (0.26 - 0.20)))


def test_overlap_summary_arithmetic():
    rows = []
    for s, a, u, d in itertools.product((0, 1), (0, 1), (0, 1), ("yes", "no", "undetermined")):
        rows.append(
            {"speeding": s, "alcohol_bac08": a, "unbelted_victim": u, "drugs": d, "deaths": 10.0}
        )
    combos = pd.DataFrame(rows)
    combos["n_factors"] = (
        combos["speeding"]
        + combos["alcohol_bac08"]
        + (combos["drugs"] == "yes")
        + combos["unbelted_victim"]
    )
    total = int(combos["deaths"].sum())
    out = contributions.overlap_summary(combos, total).set_index("factor")
    assert out.loc["speeding-related crash", "deaths"] == pytest.approx(total / 2)
    union = out.loc["deaths involving at least one factor (union)", "deaths"]
    none = out.loc["deaths involving none of the four", "deaths"]
    assert union + none == pytest.approx(total)
    s = out.loc["sum of the four factor counts", "deaths"]
    assert out["overcount_ratio_sum_over_union"].iloc[0] == pytest.approx(s / union)
    pw = contributions.pairwise_overlap(combos, total).set_index("pair")
    assert pw.loc["speeding & alcohol", "observed_over_expected"] == pytest.approx(1.0)


def test_case_risk_function_and_shapley():
    factors = {"x": ("cx", ["0", "1"]), "y": ("cy", ["0", "1"])}
    vals = {}
    risks = {("0", "0"): 0.01, ("1", "0"): 0.03, ("0", "1"): 0.02, ("1", "1"): 0.08}
    for (a, b), r in risks.items():
        vals[cases.scenario_key({"x": a, "y": b})] = r
    case = {"x": "1", "y": "1"}
    ref = {"x": "0", "y": "0"}
    risk = cases._risk_function(vals, case, ref)
    assert risk(()) == 0.01 and risk(("x",)) == 0.03 and risk(("x", "y")) == 0.08
    phi = cases._shapley(["x", "y"], lambda s: risk(s) - risk(()))
    assert sum(phi.values()) == pytest.approx(0.07)
    assert phi["x"] == pytest.approx(0.5 * ((0.03 - 0.01) + (0.08 - 0.02)))
    # Log scale allocates differently: the allocation is not unique across scales.
    phl = cases._shapley(["x", "y"], lambda s: float(np.log(risk(s) / risk(()))))
    assert phi["x"] / 0.07 != pytest.approx(phl["x"] / np.log(8))
    assert len(cases.grid(factors)) == 4


def test_stratified_qba_identity_at_perfect_recording():
    rng = np.random.default_rng(0)
    n = 4000
    df = pd.DataFrame(
        {
            "speeding_type": rng.choice(["no", "exceeded_limit_or_racing"], n, p=[0.9, 0.1]),
            "alcohol_im": rng.choice(["no", "yes"], n, p=[0.8, 0.2]),
        }
    )
    df["fatal"] = (rng.random(n) < np.where(df["speeding_type"] == "no", 0.02, 0.1)).astype(float)
    design = SurveyDesign.from_arrays(np.ones(n), None, None)
    q = speeding.stratified_qba(df, design)
    perfect = q[(q.se_fatal == 1.0) & (q.se_nonfatal == 1.0)]
    assert np.allclose(perfect["rr_corrected"], perfect["rr_observed"])
    # Lower non-fatal sensitivity (more under-recording in non-fatal crashes) lowers the RR.
    s = q[(q.alcohol_stratum == "no") & (q.se_fatal == 1.0)].set_index("se_nonfatal")[
        "rr_corrected"
    ]
    assert s[0.5] < s[1.0]


def test_identifiability_covers_four_stages():
    t = stages.identifiability()
    assert len(t) == 4
    assert set(t.loc[t["stage"].str.startswith(("A", "D")), "identified"]) == {"no"}


# --------------------------------------------------------------------------------------
# Output-consistency checks (committed tables; skipped when absent)
# --------------------------------------------------------------------------------------
from pathlib import Path  # noqa: E402

from nhtsa_stats import config  # noqa: E402

TABLES = config.TABLES_DIR


def _t(module: str, name: str) -> pd.DataFrame:
    p = TABLES / module / f"{name}.csv"
    if not p.exists():
        pytest.skip(f"{p} not generated")
    return pd.read_csv(p)


@pytest.mark.parametrize(
    ("module", "name", "est", "low", "high"),
    [
        ("speeding", "key_models", "rr", "rr_low", "rr_high"),
        ("speeding", "strata", "rr", "rr_low", "rr_high"),
        ("multifactor", "margins", "adj_risk", "adj_risk_low", "adj_risk_high"),
        (
            "multifactor",
            "interactions",
            "additive_contrast",
            "additive_contrast_low",
            "additive_contrast_high",
        ),
        ("contributions", "nested_models", "rr", "rr_low", "rr_high"),
        ("contributions", "burden_shapley", "estimate", "estimate_low", "estimate_high"),
        ("cases", "scenarios", "model_risk", "model_risk_low", "model_risk_high"),
        (
            "restraint_behaviour",
            "dpc_by_driver_behaviour",
            "rr_belted_vs_unbelted",
            "rr_low",
            "rr_high",
        ),
    ],
)
def test_intervals_contain_estimates(module, name, est, low, high):
    d = _t(module, name).dropna(subset=[est])
    assert len(d)
    assert (d[low] <= d[est] + 1e-12).all() and (d[est] <= d[high] + 1e-12).all()


def test_speeding_lattice_matches_phase1_model_a():
    """The lattice model with the six model-A blocks is Phase-1 model A with speeding type."""
    km = _t("speeding", "key_models").set_index(["exposure", "outcome", "model"])
    p1 = _t("severity", "fatal_speeding_type").set_index("level")
    assert km.loc[("exceeded", "fatal", "environment_and_other_behaviour"), "rr"] == pytest.approx(
        p1.loc["exceeded_limit_or_racing", "adj_rr"], rel=1e-3
    )
    assert km.loc[("exceeded", "fatal", "crude"), "rr"] == pytest.approx(
        p1.loc["exceeded_limit_or_racing", "crude_rr"], rel=1e-3
    )


def test_shapley_tables_are_efficient():
    """Block shares plus the retained share sum to 1 for every exposure/outcome/variant."""
    s = _t("speeding", "shapley")
    tot = s.groupby(["exposure", "outcome", "variant"])["shapley_share_of_crude"].sum()
    assert np.allclose(tot, 1.0, atol=1e-6)
    b = _t("contributions", "burden_shapley")
    for ps, g in b.groupby("player_set"):
        g = g.set_index("quantity")
        joint = g.loc[
            [
                q
                for q in g.index
                if q.startswith("AF[")
                and q.count("+") == max(x.count("+") for x in g.index if x.startswith("AF["))
            ],
            "estimate",
        ].iloc[0]
        shap = g.loc[[q for q in g.index if q.startswith("Shapley[")], "estimate"].sum()
        assert shap == pytest.approx(joint, rel=1e-6), ps


def test_case_model_calibrated_in_large_cells():
    s = _t("cases", "scenarios")
    big = s[(s["crss_n"] >= 5000) & s["predicted_in_cell"].notna()]
    assert len(big) >= 5
    ratio = big["observed_rate"] / big["predicted_in_cell"]
    assert ratio.between(0.75, 1.33).all(), big[["scenario", "observed_rate", "predicted_in_cell"]]


def test_unsupported_cases_have_no_model_estimate():
    s = _t("cases", "scenarios")
    bad = s[s["status"] != "supported"]
    assert bad["model_risk"].isna().all() and bad["rr_vs_reference"].isna().all()
    c = _t("cases", "scenario_contrasts")
    assert c.loc[~c["allocation_supported"], "shapley_share_risk_difference"].isna().all()


def test_readme_phase2_numbers_match_tables():
    readme = (Path(config.PROJECT_ROOT) / "README.md").read_text()
    km = _t("speeding", "key_models").set_index(["exposure", "outcome", "model"])
    st = _t("speeding", "strata").set_index(["exposure", "outcome", "stratum"])
    sh = _t("speeding", "shapley").set_index(["exposure", "outcome", "variant", "block"])
    ov = _t("contributions", "fars_overlap_summary").set_index("factor")
    checks = {
        f"of {km.loc[('exceeded', 'fatal', 'crude'), 'rr']:.1f}": True,
        f"about {100 * sh.loc[('exceeded', 'fatal', 'all_blocks', 'alcohol'), 'shapley_share_of_crude']:.0f}% of its log": True,
        f"{100 * sh.loc[('exceeded', 'fatal', 'all_blocks', 'retained_after_all_blocks'), 'shapley_share_of_crude']:.0f}% remains": True,
        f"risk ratio is\n   {st.loc[('exceeded', 'fatal', 'no alcohol'), 'rr']:.1f}": True,
        f"sum to {100 * ov.loc['sum of the four factor counts', 'share_of_all_deaths']:.0f}% of all deaths": True,
        f"while {100 * ov.loc['deaths involving at least one factor (union)', 'share_of_all_deaths']:.0f}% of deaths": True,
    }
    missing = [k for k in checks if k not in readme]
    assert not missing, missing


def test_case_model_does_not_adjust_for_covariates_collinear_with_case_factors():
    """'Other driver' flags are 'no_other_vehicle' exactly when the crash is single-vehicle (a
    case factor), so adjusting for them would make the single-vehicle contrast impossible."""
    assert not {"other_speeding", "other_alcohol_im"} & set(cases.COVARIATES)
    assert {"tod", "light"}.isdisjoint(cases.COVARIATES)  # night is a case factor
