"""Tests of the FARS within-vehicle module (software tests on synthetic data + real smoke test).

Synthetic data here only exercise the estimators; they are never findings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import matched


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(5)


# --------------------------------------------------------------------------------------
# Double-pair comparison
# --------------------------------------------------------------------------------------
def expected_cells(
    n_by_type: dict[tuple[int, int], float],
    severities: np.ndarray,
    seat_d: float,
    seat_p: float,
    risk: dict[int, float],
) -> np.ndarray:
    """Exact expected 16-cell table under the multiplicative DPC model with independent deaths.

    P(death) = severity * seat factor * risk[x]; vehicles of each (x_d, x_p) type are spread
    evenly over the severity values.
    """
    c = np.zeros((2, 2, 2, 2))
    for (xd, xp), n in n_by_type.items():
        for s in severities:
            pd_ = s * seat_d * risk[xd]
            pp = s * seat_p * risk[xp]
            for kd in (0, 1):
                for kp in (0, 1):
                    prob = (pd_ if kd else 1 - pd_) * (pp if kp else 1 - pp)
                    c[xd, kd, xp, kp] += n / len(severities) * prob
    return c


def test_dpc_recovers_true_risk_ratio_exactly():
    risk = {1: 0.4, 0: 1.0}  # x = 1 (belted) has 40% of the unbelted risk
    c = expected_cells(
        {(1, 1): 5000, (1, 0): 800, (0, 1): 700, (0, 0): 1500},
        severities=np.array([0.05, 0.2, 0.5, 0.9]),
        seat_d=1.0,
        seat_p=1.1,
        risk=risk,
    )
    logs, var = matched.dpc_components(c)
    np.testing.assert_allclose(np.exp(logs), 0.4, rtol=1e-12)
    assert np.all(var > 0)
    assert np.exp(matched.dpc_combined(c)) == pytest.approx(0.4, rel=1e-12)


def test_dpc_is_vectorised_over_replicates():
    c = expected_cells(
        {(1, 1): 100, (1, 0): 50, (0, 1): 50, (0, 0): 100},
        np.array([0.3]),
        1.0,
        1.0,
        {1: 0.5, 0: 1.0},
    )
    batch = np.stack([c, 2 * c, 3 * c])
    np.testing.assert_allclose(matched.dpc_combined(batch), np.log(0.5), rtol=1e-12)


def _pairs_from_cells(counts: np.ndarray) -> pd.DataFrame:
    rows = []
    vid = 0
    for idx in np.ndindex(2, 2, 2, 2):
        for _ in range(int(counts[idx])):
            rows.append((vid, vid // 2, *idx))
            vid += 1
    return pd.DataFrame(rows, columns=["vehicle_id", "crash_id", "x_d", "k_d", "x_p", "k_p"])


def test_cell_counts_and_bootstrap(rng):
    counts = rng.integers(5, 40, size=(2, 2, 2, 2))
    pairs = _pairs_from_cells(counts)
    np.testing.assert_array_equal(matched.cell_counts(pairs), counts)
    bv = matched.bootstrap_counts(pairs, 50, rng)
    bc = matched.bootstrap_counts(pairs, 50, rng, cluster="crash_id")
    assert bv.shape == (50, 2, 2, 2, 2)
    np.testing.assert_array_equal(bv.sum(axis=(1, 2, 3, 4)), counts.sum())
    # crash bootstrap resamples whole crashes (2 vehicles each here, except possibly the last)
    assert np.all(np.abs(bc.sum(axis=(1, 2, 3, 4)) - counts.sum()) <= counts.sum())


def test_reclassify_moves_only_belted_survivors():
    c = np.arange(1, 17, dtype=float).reshape(2, 2, 2, 2)
    np.testing.assert_array_equal(matched.reclassify(c, 0.0), c)
    r = matched.reclassify(c, 0.25)
    assert r.sum() == pytest.approx(c.sum())
    dd0, dp0 = matched.death_counts(c)
    dd1, dp1 = matched.death_counts(r)
    # deaths are never reclassified: total driver / other deaths unchanged
    assert dd1.sum() == pytest.approx(dd0.sum())
    assert dp1.sum() == pytest.approx(dp0.sum())
    # driver deaths with a belted driver are unchanged (deaths keep their code)
    np.testing.assert_allclose(dd1[1].sum(), dd0[1].sum())
    # belted surviving drivers shrink by (1 - f)
    assert r[1, 0].sum() == pytest.approx(0.75 * c[1, 0].sum())
    with pytest.raises(ValueError):
        matched.reclassify(c, 1.0)


def test_misreporting_moves_belt_estimate_towards_null_and_tipping_point():
    c = expected_cells(
        {(1, 1): 50000, (1, 0): 4000, (0, 1): 4000, (0, 0): 6000},
        np.array([0.1, 0.4, 0.8]),
        1.0,
        1.0,
        {1: 0.4, 0: 1.0},
    )
    est = [float(np.exp(matched.dpc_combined(matched.reclassify(c, f)))) for f in (0, 0.05, 0.1)]
    assert est[0] == pytest.approx(0.4)
    assert est[0] < est[1] < est[2]
    f_star = matched.dpc_tipping_point(c)
    assert 0 < f_star < 0.95
    assert matched.dpc_combined(matched.reclassify(c, f_star)) == pytest.approx(0.0, abs=1e-5)


def test_dpc_analysis_table(rng):
    c = expected_cells(
        {(1, 1): 3000, (1, 0): 600, (0, 1): 600, (0, 0): 900},
        np.array([0.2, 0.6]),
        1.0,
        1.2,
        {1: 0.5, 0: 1.0},
    )
    pairs = _pairs_from_cells(np.round(c))
    tab = matched.dpc_analysis(pairs, "t", "belted", rng, n_boot=200, fractions=(0.0, 0.1))
    comb = tab.loc[tab["component"].str.startswith("combined")]
    assert len(comb) == 2
    r0 = comb.iloc[0]
    assert r0["rr_low"] < r0["rr_x1_vs_x0"] < r0["rr_high"]
    assert r0["rr_x1_vs_x0"] == pytest.approx(0.5, rel=0.05)
    assert r0["reduction_1_minus_rr"] == pytest.approx(1 - r0["rr_x1_vs_x0"])
    assert comb.iloc[1]["rr_x1_vs_x0"] > r0["rr_x1_vs_x0"]


# --------------------------------------------------------------------------------------
# Matched sets, conditional logit, matched-pair OR
# --------------------------------------------------------------------------------------
def _pair_sets(n10: int, n01: int, n00: int, n11: int, shuffle_rng=None) -> pd.DataFrame:
    """Two-occupant vehicles with exactly one death, by (dead unbelted, survivor unbelted)."""
    rows = []
    vid = 0
    for (dead_unb, alive_unb), n in {(1, 0): n10, (0, 1): n01, (0, 0): n00, (1, 1): n11}.items():
        for _ in range(n):
            rows.append((vid, vid // 3, 1, dead_unb))
            rows.append((vid, vid // 3, 0, alive_unb))
            vid += 1
    df = pd.DataFrame(rows, columns=["vehicle_id", "crash_id", "killed", "unbelted"])
    if shuffle_rng is not None:
        df = df.sample(frac=1.0, random_state=1).reset_index(drop=True)
    return df


def test_matched_pair_or_closed_form():
    sets = _pair_sets(300, 100, 500, 80)
    r0 = matched.matched_pair_or(sets, 0.0)
    assert r0["or_unbelted_vs_belted"] == pytest.approx(3.0)
    se = np.sqrt(1 / 300 + 1 / 100)
    assert r0["or_low"] == pytest.approx(3.0 * np.exp(-1.959964 * se), rel=1e-5)
    r1 = matched.matched_pair_or(sets, 0.1)
    assert r1["or_unbelted_vs_belted"] == pytest.approx(0.9 * 300 / (100 + 0.1 * 500))
    f_star = r0["tipping_point_f"]
    assert f_star == pytest.approx((300 - 100) / (300 + 500))
    assert matched.matched_pair_or(sets, f_star)["or_unbelted_vs_belted"] == pytest.approx(1.0)


def test_clogit_equals_mcnemar_ratio_for_pairs_and_handles_unsorted_groups(rng):
    sets = _pair_sets(240, 80, 300, 60, shuffle_rng=rng)
    x = sets[["unbelted"]].astype(float)
    res = matched.fit_clogit(
        sets["killed"].to_numpy(),
        x,
        sets["vehicle_id"].to_numpy(),
        sets["crash_id"].to_numpy(),
    )
    t = res.table.set_index("term").loc["unbelted"]
    assert t["odds_ratio"] == pytest.approx(3.0, rel=1e-6)
    assert t["se_model"] == pytest.approx(np.sqrt(1 / 240 + 1 / 80), rel=1e-3)
    assert np.isfinite(t["se_robust"]) and t["se_robust"] > 0
    assert res.info["converged"]
    assert res.info["n_sets"] == 680


def test_clogit_rejects_concordant_sets():
    sets = _pair_sets(10, 5, 5, 5)
    extra = pd.DataFrame(
        {"vehicle_id": [10_000, 10_000], "crash_id": [1, 1], "killed": [0, 0], "unbelted": [1, 0]}
    )
    sets = pd.concat([sets, extra], ignore_index=True)
    with pytest.raises(ValueError):
        matched.fit_clogit(
            sets["killed"].to_numpy(),
            sets[["unbelted"]].astype(float),
            sets["vehicle_id"].to_numpy(),
            sets["crash_id"].to_numpy(),
        )


def _synthetic_fars(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for case in range(1, 401):
        for veh in (1, 2):
            n_occ = rng.integers(1, 4)
            for per in range(1, n_occ + 1):
                rows.append(
                    {
                        "YEAR": 2020,
                        "case_id": case,
                        "VEH_NO": veh,
                        "PER_NO": per,
                        "PER_TYP": 1 if per == 1 else 2,
                        "ptype": "driver" if per == 1 else "passenger",
                        "age": int(rng.choice([10, 30, 70])),
                        "sex": str(rng.choice(["male", "female"])),
                        "killed": int(rng.random() < 0.4),
                        "seat": ["front_left", "front_other", "second_row"][per - 1],
                        "SEAT_POS": [11, 13, 21][per - 1],
                        "restraint": str(rng.choice(["belted", "none", "unknown"])),
                        "helmet": "not_applicable",
                        "body": str(rng.choice(["car", "suv", "medium_heavy_truck"])),
                    }
                )
    rows.append({**rows[0], "PER_NO": 9, "PER_TYP": 3, "ptype": "parked_vehicle_occupant"})
    return matched.add_ids(pd.DataFrame(rows))


def test_eligibility_flow_rules(rng):
    df = _synthetic_fars(rng)
    elig, flow = matched.lpv_flow_and_eligible(df)
    assert set(elig["ptype"]) <= {"driver", "passenger"}
    assert set(elig["body"]) <= set(matched.LPV_BODIES)
    assert (elig["age"] >= matched.MIN_AGE).all()
    assert set(elig["restraint"]) <= {"belted", "none"}
    assert (elig["unbelted"] == (elig["restraint"] == "none")).all()
    persons = flow["persons"].tolist()
    assert persons[0] == len(df)
    assert persons[:7] == sorted(persons[:7], reverse=True)
    assert persons[6] == len(elig)
    sets = matched.matched_sets(elig)["discordant"]
    k = sets.groupby("vehicle_id")["killed"].agg(["sum", "size"])
    assert ((k["sum"] > 0) & (k["sum"] < k["size"]) & (k["size"] >= 2)).all()


def test_pair_frame_requires_unique_driver_and_other():
    df = pd.DataFrame(
        {
            "vehicle_id": [1, 1, 2, 2, 2, 3],
            "crash_id": [1, 1, 2, 2, 2, 3],
            "belted": [1, 0, 1, 1, 0, 1],
            "killed": [0, 1, 1, 0, 0, 1],
            "role": ["d", "p", "d", "p", "p", "d"],
        }
    )
    pairs = matched.pair_frame(df, "belted", df["role"] == "d", df["role"] == "p")
    # vehicle 2 has two 'other' occupants and vehicle 3 has none -> only vehicle 1
    assert pairs["vehicle_id"].tolist() == [1]
    assert pairs.iloc[0][["x_d", "k_d", "x_p", "k_p"]].tolist() == [1, 0, 0, 1]


def test_age_dummies_reject_uncovered_ages():
    with pytest.raises(ValueError):
        matched.age_dummies(pd.Series([12.0, 30.0]), matched.AGE_FINE, matched.AGE_FINE_REF)
    d = matched.age_dummies(pd.Series([13.0, 30.0, 80.0]), matched.AGE_FINE, "25-34")
    assert "age[25-34]" not in d.columns
    assert d.loc[2, "age[75+]"] == 1.0


# --------------------------------------------------------------------------------------
# Real data smoke test
# --------------------------------------------------------------------------------------
@pytest.mark.processed
def test_real_data_smoke(rng):
    df = matched.load_fars_occupants(years=[2023])
    elig, flow = matched.lpv_flow_and_eligible(df)
    assert flow["persons"].iloc[0] == len(df)
    assert len(elig) > 20_000
    elig["belted"] = 1 - elig["unbelted"]
    drv = (elig["ptype"] == "driver") & (elig["SEAT_POS"] == matched.SEAT_POS_DRIVER)
    rf = (elig["ptype"] == "passenger") & (elig["SEAT_POS"] == matched.SEAT_POS_RIGHT_FRONT)
    pairs = matched.pair_frame(elig, "belted", drv, rf)
    assert len(pairs) > 5_000
    c = matched.cell_counts(pairs)
    assert np.isfinite(matched.dpc_combined(c))
    sets = matched.matched_sets(elig)["discordant"].sort_values(["vehicle_id", "PER_NO"])
    x = matched.occupant_covariates(sets)
    res = matched.fit_clogit(
        sets["killed"].to_numpy(), x, sets["vehicle_id"].to_numpy(), sets["crash_id"].to_numpy()
    )
    assert res.info["converged"]
    t = res.table.set_index("term").loc["unbelted"]
    assert np.isfinite([t["odds_ratio"], t["or_low"], t["or_high"]]).all()


def _clustered_sets(rng: np.random.Generator, n_crashes: int) -> pd.DataFrame:
    """Vehicles nested in crashes that share a crash-level severity (between-vehicle dependence)."""
    rows, vid = [], 0
    for crash in range(n_crashes):
        sev = rng.normal(0.0, 1.0)
        for _veh in range(int(rng.integers(1, 3))):
            n = int(rng.integers(2, 5))
            unb = rng.random(n) < 0.3
            old = rng.random(n) < 0.25
            eta = -0.5 + sev + 1.2 * unb + 0.8 * old
            killed = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(int)
            rows += [(vid, crash, killed[i], int(unb[i]), float(old[i])) for i in range(n)]
            vid += 1
    df = pd.DataFrame(rows, columns=["vehicle_id", "crash_id", "killed", "unbelted", "old"])
    return matched.matched_sets(df)["discordant"].sample(frac=1.0, random_state=4)


def test_clogit_robust_se_matches_crash_jackknife(rng):
    """The crash-cluster sandwich agrees with a delete-one-crash jackknife (shuffled rows)."""
    sets = _clustered_sets(rng, 160).reset_index(drop=True)
    cols = ["unbelted", "old"]
    res = matched.fit_clogit(
        sets["killed"].to_numpy(),
        sets[cols].astype(float),
        sets["vehicle_id"].to_numpy(),
        sets["crash_id"].to_numpy(),
    )
    crashes = sets["crash_id"].unique()
    est = []
    for c in crashes:
        sub = sets.loc[sets["crash_id"] != c]
        r = matched.fit_clogit(
            sub["killed"].to_numpy(),
            sub[cols].astype(float),
            sub["vehicle_id"].to_numpy(),
            sub["crash_id"].to_numpy(),
            start=res.params,
        )
        est.append(r.params)
    est = np.array(est)
    g = len(crashes)
    jk = np.sqrt((g - 1) / g * ((est - est.mean(axis=0)) ** 2).sum(axis=0))
    np.testing.assert_allclose(res.table["se_robust"].to_numpy(), jk, rtol=0.1)


def test_clogit_flags_sparse_terms():
    sets = _pair_sets(240, 80, 300, 60)
    sets["rare"] = 0.0
    rare_rows = [*sets.index[sets["killed"] == 1][:6], *sets.index[sets["killed"] == 0][-6:]]
    sets.loc[rare_rows, "rare"] = 1.0
    res = matched.fit_clogit(
        sets["killed"].to_numpy(),
        sets[["unbelted", "rare"]].astype(float),
        sets["vehicle_id"].to_numpy(),
        sets["crash_id"].to_numpy(),
    )
    t = res.table.set_index("term")
    assert t.loc["rare", "n_with_term"] == 12
    assert t.loc["rare", "deaths_with_term"] == 6
    assert t.loc["rare", "flag"] == "suppressed"
    assert t.loc["unbelted", "flag"] == ""


def test_dpc_flags_small_death_counts(rng):
    c = expected_cells(
        {(1, 1): 3000, (1, 0): 60, (0, 1): 600, (0, 0): 900},
        np.array([0.2, 0.6]),
        1.0,
        1.2,
        {1: 0.5, 0: 1.0},
    )
    pairs = _pairs_from_cells(np.round(c))
    tab = matched.dpc_analysis(pairs, "t", "belted", rng, n_boot=200).set_index("component")
    # pair type (driver belted, other unbelted) has ~60 vehicles -> driver deaths < 30
    assert tab.loc["driver_subject|other_x=0", "min_death_count"] < 30
    assert tab.loc["driver_subject|other_x=0", "flag"] == "suppressed"
    assert tab.loc["combined (inverse-variance weighted)", "flag"] == "suppressed"
    assert tab.loc["driver_subject|other_x=1", "flag"] == ""


def test_belt_effect_table_uses_crash_cluster_ci(rng):
    c = expected_cells(
        {(1, 1): 3000, (1, 0): 600, (0, 1): 600, (0, 0): 900},
        np.array([0.2, 0.6]),
        1.0,
        1.2,
        {1: 0.5, 0: 1.0},
    )
    pairs = _pairs_from_cells(np.round(c))
    dpc = matched.dpc_analysis(
        pairs, "t", "belted", rng, n_boot=200, fractions=matched.MISREPORT_FRACTIONS
    )
    dpc_cc = matched.dpc_analysis(pairs, "t_cc", "belted", rng, n_boot=200)
    sets = _pair_sets(240, 80, 300, 60)
    cl = {
        "main": matched.fit_clogit(
            sets["killed"].to_numpy(),
            sets[["unbelted"]].astype(float),
            sets["vehicle_id"].to_numpy(),
            sets["crash_id"].to_numpy(),
        )
    }
    mp = pd.DataFrame([matched.matched_pair_or(sets, f) for f in matched.MISREPORT_FRACTIONS])
    belt = matched.belt_effect_table(dpc, cl, mp, dpc_cc)
    assert list(belt.columns) == ["estimand", "estimate", "low", "high", "method", "n_vehicles"]
    assert belt["estimand"].is_unique
    b = belt.set_index("estimand")
    comb = dpc.loc[(dpc["misreport_fraction"] == 0) & dpc["component"].str.startswith("comb")]
    comb = comb.iloc[0]
    rr = b.loc["fatality_rr_belted_vs_unbelted_given_fatal_crash"]
    red = b.loc["fatality_risk_reduction_belt_given_fatal_crash"]
    assert rr["low"] == pytest.approx(comb["rr_low_crash_boot"])
    assert rr["high"] == pytest.approx(comb["rr_high_crash_boot"])
    assert red["estimate"] == pytest.approx(1 - rr["estimate"])
    assert red["low"] == pytest.approx(1 - rr["high"])
    assert red["high"] == pytest.approx(1 - rr["low"])
    assert red["low"] < red["estimate"] < red["high"]
    assert rr["n_vehicles"] == comb["n_pairs_with_death"]
    for sfx in (
        "_misreport_f05",
        "_misreport_f10",
        "_misreport_f20",
        "_complete_restraint_vehicles",
    ):
        assert "fatality_risk_reduction_belt_given_fatal_crash" + sfx in b.index
    assert "within_vehicle_or_killed_unbelted_vs_belted" in b.index
