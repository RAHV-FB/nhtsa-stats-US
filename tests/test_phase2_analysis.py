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
