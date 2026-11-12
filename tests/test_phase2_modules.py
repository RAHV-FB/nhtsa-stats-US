"""Pure helpers of the Phase-2 modules ``drugs``, ``restraint_behaviour`` and ``multifactor``
on small synthetic frames (no data caches needed)."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from nhtsa_stats.analysis import data, drugs, factorial, matched, multifactor, restraint_behaviour
from nhtsa_stats.analysis.survey import SurveyDesign

NAN = np.nan


# --------------------------------------------------------------------------------------
# drugs
# --------------------------------------------------------------------------------------
def _drivers(rows: list[dict]) -> pd.DataFrame:
    base = {
        "YEAR": 2019,
        "STATE": 1,
        "survival": "killed",
        "drv_drug_test_status": "tested",
        "drv_pr_drugs": NAN,
        "drv_pr_alcohol": NAN,
        "drv_bac08_measured": NAN,
        "drv_drug_any": NAN,
        "drv_kabco": NAN,
        "drv_drug_presumptive_only": NAN,
        "drv_drug_carboxy_thc_only": NAN,
        **{f"drv_drug_{c}": NAN for c in drugs.DRUG_CLASSES},
    }
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["drug_tested"] = (df["drv_drug_test_status"] == "tested").astype(float)
    df["bac_tested"] = df["drv_bac08_measured"].notna().astype(float)
    return df


def test_or2x2_woolf_and_zero_cell():
    o, lo, hi = drugs._or2x2(10, 20, 5, 40)
    assert o == pytest.approx(4.0)
    se = np.sqrt(1 / 10 + 1 / 20 + 1 / 5 + 1 / 40)
    assert lo == pytest.approx(np.exp(np.log(4) - 1.96 * se))
    assert hi == pytest.approx(np.exp(np.log(4) + 1.96 * se))
    assert all(np.isnan(v) for v in drugs._or2x2(0, 5, 5, 5))


def test_driver_frame_coding():
    df = pd.DataFrame(
        {
            "YEAR": [2018, 2022, 2022],
            "drv_age_band": ["25-34", None, "75+"],
            "drv_sex": ["male", None, "female"],
            "body": ["car", "motorcycle", "medium_heavy_truck"],
            "crash_type": ["sv_rollover", "pedestrian", "mv_head_on"],
            "night": [1, 0, NAN],
            "drv_bac08_measured": [1, 0, NAN],
            "drv_drug_any": [1.0, 0.0, NAN],
        }
    )
    d = drugs._driver_frame(df)
    assert d["age"].tolist() == ["25-34", "unknown", "75+"]
    assert d["sex"].tolist() == ["male", "unknown", "female"]
    assert d["vehicle"].tolist() == ["light", "motorcycle", "heavy"]
    assert d["config"].tolist() == ["single_vehicle", "nonmotorist", "multi_vehicle"]
    assert d["night_"].tolist() == ["night", "day", "unknown"]
    assert d["period"].tolist() == ["2016-2019", "2020-2024", "2020-2024"]
    assert d["alcohol"].tolist()[:2] == ["yes", "no"] and pd.isna(d["alcohol"].iloc[2])
    assert d["drug"].tolist()[:2] == ["yes", "no"] and pd.isna(d["drug"].iloc[2])


def test_testing_rates_shares_and_unknown_survival_excluded():
    df = _drivers(
        [
            {"survival": "killed", "drv_drug_test_status": "tested", "drv_pr_drugs": 1},
            {"survival": "killed", "drv_drug_test_status": "not_tested", "drv_pr_drugs": 0},
            {"survival": "killed", "drv_drug_test_status": "tested", "drv_pr_drugs": 0},
            {"survival": "survived", "drv_drug_test_status": "not_tested", "drv_kabco": 3},
            {"survival": "unknown", "drv_drug_test_status": "tested"},
        ]
    )
    out = drugs.testing_rates(df)
    k = out[(out["dimension"] == "all years") & (out["survival"] == "killed")].iloc[0]
    assert k["n"] == 3 and k["share_tested"] == pytest.approx(2 / 3)
    assert k["share_not_tested"] == pytest.approx(1 / 3)
    s = out[(out["dimension"] == "all years") & (out["survival"] == "survived")].iloc[0]
    assert s["n"] == 1 and s["share_tested"] == 0
    yes = out[(out["dimension"] == "police drug report") & (out["level"] == "yes")]
    assert yes[yes["survival"] == "killed"]["n"].iloc[0] == 1
    sev = out[out["dimension"] == "survivor injury severity"].set_index("level")
    assert sev.loc["A (serious)", "n"] == 1 and sev.loc["O (none)", "n"] == 0
    assert out["n"].min() >= 0 and "unknown" not in set(out["survival"])


def test_state_testing_high_testing_flag_and_tertiles():
    rows = []
    for state, (k_rate, s_rate) in enumerate(
        [(0.9, 0.8), (0.6, 0.55), (0.4, 0.9), (0.9, 0.3), (0.7, 0.6), (0.2, 0.1)], start=1
    ):
        for surv, rate in (("killed", k_rate), ("survived", s_rate)):
            n_t = round(rate * 10)
            for i in range(10):
                rows.append(
                    {
                        "STATE": state,
                        "survival": surv,
                        "drv_drug_test_status": "tested" if i < n_t else "not_tested",
                        "drv_bac08_measured": 0.0 if i < n_t else NAN,
                        "drv_drug_any": 1.0 if (surv == "killed" and i < 2) else 0.0,
                    }
                )
    df = _drivers(rows)
    out = drugs.state_testing(df).set_index("STATE")
    assert out.loc[1, "drug_tested_killed"] == pytest.approx(0.9)
    # High testing needs >= 50% of killed AND surviving drivers, drug and BAC tested.
    assert out["high_testing"].to_dict() == {
        1: True,
        2: True,
        3: False,
        4: False,
        5: True,
        6: False,
    }
    assert out.loc[1, "drug_positivity_killed_tested"] == pytest.approx(2 / 9)
    assert set(out["tertile_survivor_drug_testing"]) == {"low", "middle", "high"}
    assert out.loc[6, "tertile_survivor_drug_testing"] == "low"


def test_positivity_periods_and_indeterminate_share():
    rows = [
        {
            "YEAR": 2019,
            "drv_drug_any": 1.0,
            "drv_drug_cannabinoid": 1.0,
            "drv_drug_presumptive_only": 0.0,
            "drv_drug_carboxy_thc_only": 0.0,
        },
        {"YEAR": 2019, "drv_drug_any": 0.0, "drv_drug_cannabinoid": 0.0},
        {"YEAR": 2019, "drv_drug_any": NAN},  # tested, indeterminate
        {"YEAR": 2019, "drv_drug_test_status": "not_tested"},  # not in the tested base
        {
            "YEAR": 2023,
            "drv_drug_any": 1.0,
            "drv_drug_cannabinoid": 1.0,
            "drv_drug_presumptive_only": 1.0,
            "drv_drug_carboxy_thc_only": 1.0,
        },
        {"YEAR": 2023, "survival": "unknown", "drv_drug_any": 1.0},
    ]
    out = drugs.positivity(_drivers(rows)).set_index(["period", "survival"])
    early = out.loc[("2016-2021 (3-digit codes)", "killed")]
    assert early["n_tested"] == 3
    assert early["share_indeterminate"] == pytest.approx(1 / 3)
    assert early["any_psychoactive"] == pytest.approx(0.5)  # among determinate results only
    assert early["cannabinoid"] == pytest.approx(0.5)
    assert early["presumptive_only_share_of_positive"] == 0
    late = out.loc[("2022-2024 (4-digit codes)", "killed")]
    assert late["n_tested"] == 1 and late["any_psychoactive"] == 1
    assert late["presumptive_only_share_of_positive"] == 1
    assert late["carboxy_thc_only_share_of_cannabinoid"] == 1
    assert out.loc[("2022-2024 (4-digit codes)", "survived"), "n_tested"] == 0


def test_co_occurrence_and_police_validity_two_by_two():
    rows = (
        [{"drv_bac08_measured": 1, "drv_drug_any": 1.0, "drv_pr_alcohol": 1, "drv_pr_drugs": 1}] * 4
        + [{"drv_bac08_measured": 1, "drv_drug_any": 0.0, "drv_pr_alcohol": 1, "drv_pr_drugs": 0}]
        * 2
        + [{"drv_bac08_measured": 0, "drv_drug_any": 1.0, "drv_pr_alcohol": 0, "drv_pr_drugs": 1}]
        * 1
        + [{"drv_bac08_measured": 0, "drv_drug_any": 0.0, "drv_pr_alcohol": 0, "drv_pr_drugs": 0}]
        * 3
        + [{"drv_bac08_measured": NAN, "drv_drug_any": 1.0}]  # no BAC: excluded from toxicology 2x2
    )
    df = _drivers(rows)
    co = drugs.co_occurrence(df).set_index(["measure", "survival"])
    tox = co.loc[("toxicology: BAC >= .08 and any psychoactive drug", "killed")]
    assert tox["n"] == 10
    assert tox["share_both"] == pytest.approx(0.4)
    assert tox["odds_ratio"] == pytest.approx(4 * 3 / (2 * 1))
    assert tox["share_drug_among_alcohol"] == pytest.approx(4 / 6)
    pol = co.loc[("police report: alcohol and drugs both recorded", "killed")]
    assert pol["n"] == 10 and pol["share_alcohol"] == pytest.approx(0.6)
    assert co.loc[("toxicology: BAC >= .08 and any psychoactive drug", "survived"), "n"] == 0

    pv = drugs.police_validity(df).set_index("survival").loc["killed"]
    assert pv["n_positive"] == 6 and pv["n_negative"] == 5
    assert pv["sensitivity_unknown_as_no"] == pytest.approx(5 / 6)  # 5 of 6 positives reported
    assert pv["sensitivity_among_known"] == pytest.approx(1.0)
    assert pv["police_unknown_among_positive"] == pytest.approx(1 / 6)
    assert pv["specificity_among_known"] == pytest.approx(1.0)


def test_selection_gradient_groups_by_state_tertile():
    df = _drivers(
        [
            {"STATE": 1, "drv_drug_any": 1.0, "drv_bac08_measured": 1.0},
            {"STATE": 1, "drv_drug_any": 0.0, "drv_bac08_measured": 0.0},
            {"STATE": 1, "drv_drug_test_status": "not_tested"},
            {"STATE": 2, "drv_drug_any": 0.0, "drv_bac08_measured": 0.0},
        ]
    )
    states = pd.DataFrame({"STATE": [1, 2], "tertile_survivor_drug_testing": ["low", "high"]})
    out = drugs.selection_gradient(df, states).set_index("survivor_test_tertile")
    assert out.loc["low", "n_tested"] == 2 and out.loc["low", "share_tested"] == pytest.approx(
        2 / 3
    )
    assert out.loc["low", "drug_positivity"] == pytest.approx(0.5)
    assert out.loc["high", "drug_positivity"] == 0


def _fake_crash_frame():
    """Weighted CRSS-like frame: known drug status 1/0 and unknown (NaN), fatal 1/0."""
    rows = [
        # year, drugs, fatal, weight
        (2017, 1.0, 1, 10.0),
        (2017, 1.0, 0, 90.0),
        (2017, 0.0, 1, 20.0),
        (2017, 0.0, 0, 880.0),
        (2017, NAN, 1, 30.0),
        (2017, NAN, 0, 270.0),
    ]
    rows += [(2020, *r[1:]) for r in rows]  # the later period has the same structure
    df = pd.DataFrame(rows, columns=["YEAR", "drugs", "fatal", "WEIGHT"])
    design = SurveyDesign.from_arrays(df["WEIGHT"], np.zeros(len(df)), np.arange(len(df)))
    return df, design


def test_crss_bounds_unknown_allocation_arithmetic(monkeypatch):
    monkeypatch.setattr(data, "crss_crash", lambda outcome="fatal": _fake_crash_frame())
    out = drugs.crss_bounds()
    p = out[out["period"] == "2016-2018"]
    assert set(out["period"]) == {"2016-2018", "2019-2024", "2016-2024"}
    a, b, c, d, uf, un = 10, 90, 20, 880, 30, 270
    cc = (a / (a + b)) / (c / (c + d))
    assert np.allclose(p["rr_complete_case"], cc)
    assert p["share_unknown"].iloc[0] == pytest.approx(300 / 1300)
    assert p["unknown_share_fatal"].iloc[0] == pytest.approx(30 / 60)
    assert p["unknown_share_nonfatal"].iloc[0] == pytest.approx(270 / 1240)

    def rr(ef, en):
        A, B, C, D = a + ef * uf, b + en * un, c + (1 - ef) * uf, d + (1 - en) * un
        return (A / (A + B)) / (C / (C + D))

    neg = p[p["scenario"] == "all unknown negative"].iloc[0]
    pos = p[p["scenario"] == "all unknown positive"].iloc[0]
    assert neg["rr"] == pytest.approx(rr(0, 0))
    assert pos["rr"] == pytest.approx(rr(1, 1))
    # k = 1 for both: unknowns get the known-positive prevalence of their own stratum
    # (differential missingness shifts the RR away from the complete-case value).
    pf, pn = a / (a + c), b / (b + d)
    same = p[(p["k_fatal"] == 1.0) & (p["k_nonfatal"] == 1.0)].iloc[0]
    assert same["rr"] == pytest.approx(rr(pf, pn))
    # k = 0 for both reproduces "all unknown negative"; the grid is complete.
    zero = p[(p["k_fatal"] == 0.0) & (p["k_nonfatal"] == 0.0)].iloc[0]
    assert zero["rr"] == pytest.approx(neg["rr"])
    assert (p["scenario"] == "k scenario").sum() == len(drugs.K_GRID) ** 2
    # The allocated prevalence is k_f x the known-positive prevalence (capped at 1).
    big = p[(p["k_fatal"] == 3.0) & (p["k_nonfatal"] == 0.0)].iloc[0]
    assert big["rr"] == pytest.approx(rr(min(1.0, 3 * pf), 0.0))
    # Allocating more of the unknowns as positive among the fatal raises the RR.
    fat = p[p["k_nonfatal"] == 1.0].sort_values("k_fatal")["rr"].to_numpy()
    assert np.all(np.diff(fat) > 0)
    assert neg["rr"] < pos["rr"]


# --------------------------------------------------------------------------------------
# restraint_behaviour
# --------------------------------------------------------------------------------------
def test_strata_masks_are_disjoint_where_labelled_and_handle_unknown():
    elig = pd.DataFrame(
        {
            "own_speeding_type": [
                "no",
                "exceeded_limit_or_racing",
                "too_fast_for_conditions",
                "speeding_unspecified",
                "unknown",
                None,
            ],
            "drv_p_p08": [0.0, 0.9, 0.5, 0.51, NAN, 0.0],
            "n_vehicles": ["1", "2", "3+", "1", "2", "1"],
            "night": [0, 1, NAN, 1, 0, 0],
        }
    )
    st = restraint_behaviour.strata(elig)
    sp = st["driver speeding (any)"]
    assert sp["driver not speeding"].tolist() == [True, False, False, False, False, False]
    assert sp["driver speeding"].tolist() == [False, True, True, True, False, False]
    ex = st["driver exceeded limit"]["driver exceeded limit / racing"]
    assert ex.tolist() == [False, True, False, False, False, False]
    bac = st["driver BAC >= .08 (MI)"]
    assert bac["driver BAC >= .08"].tolist() == [False, True, False, True, False, False]
    assert bac["driver BAC < .08"].tolist() == [
        True,
        False,
        True,
        False,
        False,
        True,
    ]  # 0.5 is not > 0.5
    both = st["driver speeding and alcohol"]
    assert both["both"].tolist() == [False, True, False, True, False, False]
    assert both["neither"].tolist() == [True, False, False, False, False, False]
    nv = st["vehicles in crash"]
    assert (nv["multi-vehicle"] ^ nv["single vehicle"]).all()
    t = st["time"]
    assert t["night"].tolist() == [False, True, False, True, False, False]
    assert not (t["day"] & t["night"]).any()  # unknown night belongs to neither
    assert st["all"]["all vehicles"].all()


def test_dpc_by_stratum_heterogeneity_arithmetic(monkeypatch):
    """Stub the pair builder and the DPC estimator: the module's job is to turn two strata
    into a ratio of risk ratios and a z-test from the bootstrap SEs."""
    elig = pd.DataFrame(
        {
            "ptype": ["driver", "passenger"] * 4,
            "SEAT_POS": [matched.SEAT_POS_DRIVER, matched.SEAT_POS_RIGHT_FRONT] * 4,
            "own_speeding_type": ["no", "no", "no", "no"] + ["exceeded_limit_or_racing"] * 4,
            "drv_p_p08": [0.0] * 8,
            "n_vehicles": ["1"] * 8,
            "night": [0] * 8,
        }
    )
    per_label = {
        "all vehicles": (0.5, 0.10),
        "driver not speeding": (0.5, 0.10),
        "driver speeding": (0.25, 0.10),
        "driver exceeded limit / racing": (0.25, 0.10),
    }

    def fake_pair_frame(sub, attribute, drv, rf):
        return pd.DataFrame({"n": [int(drv.sum())]})

    def fake_dpc(pairs, label, attr, rng, n_boot):
        rr, se = next((v for k, v in per_label.items() if label.endswith(k)), (0.4, 0.2))
        return pd.DataFrame(
            [
                {"component": "x"},
                {
                    "component": "combined (inverse-variance weighted)",
                    "n_pairs": int(pairs["n"].iloc[0]),
                    "n_pairs_with_death": 3,
                    "min_death_count": 12.0,
                    "rr_x1_vs_x0": rr,
                    "rr_low_crash_boot": rr / 2,
                    "rr_high_crash_boot": rr * 2,
                    "reduction_1_minus_rr": 1 - rr,
                    "se_log_bootstrap": se,
                    "flag": "ok",
                },
            ]
        )

    monkeypatch.setattr(matched, "pair_frame", fake_pair_frame)
    monkeypatch.setattr(matched, "dpc_analysis", fake_dpc)
    out = restraint_behaviour.dpc_by_stratum(elig, np.random.default_rng(0), n_boot=1)
    r = out[(out["split"] == "driver speeding (any)")].set_index("stratum")
    assert np.isnan(
        r.loc["driver not speeding", "heterogeneity_ratio"]
    )  # only on the second stratum
    het = r.loc["driver speeding", "heterogeneity_ratio"]
    assert het == pytest.approx(0.5)
    z = np.log(0.5) / np.hypot(0.1, 0.1)
    from scipy import stats

    assert r.loc["driver speeding", "heterogeneity_p"] == pytest.approx(2 * stats.norm.sf(abs(z)))
    row = r.loc["driver not speeding"]
    assert row["reduction"] == pytest.approx(0.5)
    assert row["reduction_low"] == pytest.approx(1 - 1.0)  # 1 - rr_high
    assert row["reduction_high"] == pytest.approx(1 - 0.25)  # 1 - rr_low
    # The "all" split has one stratum and so no heterogeneity test.
    assert out[out["split"] == "all"]["heterogeneity_p"].isna().all()


def test_pool_log_ratios_inverse_variance_and_heterogeneity():
    d = np.log(np.array([1.2, 1.2, 1.2]))
    se = np.array([0.1, 0.1, 0.1])
    out = restraint_behaviour.pool_log_ratios(d, se)
    assert out["ratio"] == pytest.approx(1.2)
    assert out["q_heterogeneity_p"] == pytest.approx(1.0)
    s = 0.1 / np.sqrt(3)
    assert out["low"] == pytest.approx(1.2 * np.exp(-1.959964 * s), rel=1e-5)
    # unequal precision: the precise layer dominates the pooled estimate
    out2 = restraint_behaviour.pool_log_ratios(np.log(np.array([1.0, 2.0])), np.array([0.01, 1.0]))
    assert out2["ratio"] == pytest.approx(1.0, abs=0.01)
    assert 0 <= out2["p"] <= 1


def _config_frame(n: int = 16) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(
        {
            "ptype": ["driver", "passenger"] * (n // 2),
            "SEAT_POS": [matched.SEAT_POS_DRIVER, matched.SEAT_POS_RIGHT_FRONT] * (n // 2),
            "own_speeding_type": rng.choice(["no", "exceeded_limit_or_racing"], n),
            "drv_p_p08": rng.choice([0.0, 0.9], n),
            "n_vehicles": rng.choice(["1", "2"], n),
            "veh_rollover": rng.choice([0.0, 1.0, np.nan], n),
            "crash_type": rng.choice(["mv_angle", "sv_rollover_first", "sv_off_roadway"], n),
        }
    )


def test_configuration_layers_and_behaviour_masks():
    elig = _config_frame()
    lay = restraint_behaviour.configuration_layers(elig)
    assert set(lay) == {
        "single vs multi-vehicle crash",
        "rollover vs no rollover",
        "single/multi-vehicle x rollover",
        "crash type",
    }
    sm = lay["single vs multi-vehicle crash"]
    assert (sm["single vehicle"] ^ sm["multi-vehicle"]).all()
    rl = lay["rollover vs no rollover"]
    unknown = elig["veh_rollover"].isna().to_numpy()
    assert not (rl["rollover"] | rl["no rollover"])[unknown].any()  # unknown rollover in neither
    assert not (rl["rollover"] & rl["no rollover"]).any()
    cross = lay["single/multi-vehicle x rollover"]
    assert sum(m.astype(int) for m in cross.values()).max() == 1
    beh = restraint_behaviour.behaviour_masks(elig)
    spd, ref = beh["driver speeding (any) vs not speeding"]
    assert not (spd & ref).any()


def test_config_contrasts_pools_layer_log_ratios(monkeypatch):
    """Stub the DPC: a behaviour effect that is constant within layers (ratio 1.5) but whose
    marginal ratio is confounded by layer composition must pool to 1.5 within layers."""
    elig = _config_frame(40)
    elig["n_vehicles"] = ["1", "1", "2", "2"] * 10
    elig["own_speeding_type"] = ["exceeded_limit_or_racing", "no"] * 20
    layer_rr = {True: 0.2, False: 0.4}  # belt RR in single-vehicle vs multi-vehicle crashes

    def fake_belt_rr(el, mask, label, rng, n_boot):
        sub = el.loc[mask]
        single = (sub["n_vehicles"] == "1").mean()
        beh = label.endswith("behaviour") or "behaviour" in label
        rr = (layer_rr[True] if single > 0.5 else layer_rr[False]) * (1.5 if beh else 1.0)
        return {
            "n_pairs": len(sub),
            "n_pairs_with_death": len(sub),
            "rr": rr,
            "rr_low": rr / 1.2,
            "rr_high": rr * 1.2,
            "se_log": 0.05,
            "min_death_count": 100.0,
        }

    monkeypatch.setattr(restraint_behaviour, "belt_rr", fake_belt_rr)
    monkeypatch.setattr(restraint_behaviour, "joint_log_ratio_se", lambda *a, **k: 0.07)
    contrasts, by_layer = restraint_behaviour.config_contrasts(elig, np.random.default_rng(0), 1)
    c = contrasts[contrasts["contrast"] == "driver speeding (any) vs not speeding"]
    pooled = c[
        (c["adjustment"] == "single vs multi-vehicle crash") & (c["layer"].str.startswith("pooled"))
    ]
    assert pooled["ratio_of_rrs"].item() == pytest.approx(1.5)
    assert pooled["n_layers_pooled"].item() == 2
    unstrat = c[c["adjustment"].str.startswith("none")]
    assert len(unstrat) == 1 and unstrat["ratio_low"].item() < unstrat["ratio_of_rrs"].item()
    assert {"adjustment", "layer", "rr_belted_vs_unbelted"} <= set(by_layer.columns)


def test_config_contrasts_drops_thin_layers_from_the_pool(monkeypatch):
    elig = _config_frame(40)

    def fake_belt_rr(el, mask, label, rng, n_boot):
        thin = "rollover" in label and "no rollover" not in label
        return {
            "n_pairs": 10,
            "n_pairs_with_death": 5,
            "rr": 0.3,
            "rr_low": 0.2,
            "rr_high": 0.4,
            "se_log": 0.1,
            "min_death_count": 5.0 if thin else 100.0,
        }

    monkeypatch.setattr(restraint_behaviour, "belt_rr", fake_belt_rr)
    monkeypatch.setattr(restraint_behaviour, "joint_log_ratio_se", lambda *a, **k: 0.1)
    contrasts, _ = restraint_behaviour.config_contrasts(elig, np.random.default_rng(0), 1)
    r = contrasts[
        (contrasts["adjustment"] == "rollover vs no rollover")
        & (contrasts["contrast"] == "driver speeding (any) vs not speeding")
    ].set_index("layer")
    assert not r.loc["rollover", "used_in_pooled"] and r.loc["no rollover", "used_in_pooled"]
    assert r.loc["pooled within layers", "n_layers_pooled"] == 1


def _shared_crash_frame(n_crash: int, shared: bool, seed: int = 0) -> pd.DataFrame:
    """Two-vehicle crashes; vehicle 1 is a reference-arm vehicle, vehicle 2 a behaviour-arm one.

    With ``shared`` vehicle 2 repeats vehicle 1's belts and deaths (the arms' belt RRs are then
    identical and perfectly correlated across crashes); otherwise each vehicle is drawn
    independently.
    """
    rng = np.random.default_rng(seed)

    def draw() -> list[tuple[str, int, int, int]]:
        belts = rng.random(2) < 0.5
        dead = rng.random() < 0.6
        out = []
        for ptype, seat, belted in (
            ("driver", matched.SEAT_POS_DRIVER, belts[0]),
            ("passenger", matched.SEAT_POS_RIGHT_FRONT, belts[1]),
        ):
            died = bool(dead and rng.random() < (0.3 if belted else 0.6))
            out.append((ptype, seat, int(belted), int(died)))
        return out

    rows = []
    for c in range(n_crash):
        first = draw()
        for veh, arm in ((1, "no"), (2, "exceeded_limit_or_racing")):
            for ptype, seat, belted, died in first if (shared or veh == 1) else draw():
                rows.append(
                    {
                        "crash_id": c,
                        "vehicle_id": c * 10 + veh,
                        "ptype": ptype,
                        "SEAT_POS": seat,
                        "belted": belted,
                        "killed": died,
                        "own_speeding_type": arm,
                    }
                )
    return pd.DataFrame(rows)


def test_joint_log_ratio_se_accounts_for_arms_sharing_crashes():
    """The joint crash bootstrap differs from combining independent arm SEs when the two arms
    contain vehicles of the same crashes, and equals it (up to noise) when they do not."""
    n_boot = 400
    out = {}
    for shared in (True, False):
        el = _shared_crash_frame(1500, shared)
        spd = (el["own_speeding_type"] != "no").to_numpy()
        joint = restraint_behaviour.joint_log_ratio_se(
            el, spd, ~spd, np.random.default_rng(1), n_boot
        )
        arms = [
            restraint_behaviour.belt_rr(el, m, "x", np.random.default_rng(2), n_boot)["se_log"]
            for m in (spd, ~spd)
        ]
        out[shared] = (joint, float(np.hypot(*arms)))
    assert all(np.isfinite(v) for pair in out.values() for v in pair)
    # identical arms in the same crashes: the difference is (almost) constant across replicates
    assert out[True][0] < 0.1 * out[True][1]
    # independent crashes within the same frame: close to the independent-arms value
    assert out[False][0] == pytest.approx(out[False][1], rel=0.2)


def test_nested_sequence_is_nested_and_uses_one_factor():
    names = list(restraint_behaviour.NESTED)
    sets = [set(restraint_behaviour.NESTED[n]) for n in names]
    assert sets[0] == set()
    assert all(a < b for a, b in itertools.pairwise(sets))  # each step adds covariates
    assert restraint_behaviour.UNBELTED.exposed == ("yes",)
    assert restraint_behaviour.UNBELTED.reference == ("no",)


# --------------------------------------------------------------------------------------
# multifactor
# --------------------------------------------------------------------------------------
def test_fill_labels_and_unknowns():
    df = pd.DataFrame(
        {
            "YEAR": [2019.0, 2020.0],
            "flag": [1.0, NAN],
            "ind": [0, 1],
            "cat": ["a", None],
        }
    )
    out = multifactor._fill(df.copy(), ["YEAR", "flag", "ind", "cat", "absent"])
    assert out["YEAR"].tolist() == ["2019", "2020"]
    assert out["flag"].tolist() == ["yes", "unknown"]
    assert out["ind"].tolist() == ["no", "yes"]
    assert out["cat"].tolist() == ["a", "unknown"]
    assert "absent" not in out


SPEED_TYPES = [
    "no",
    "exceeded_limit_or_racing",
    "too_fast_for_conditions",
    "speeding_unspecified",
    "unknown",
    "something_else",
]


def test_speeding_codings():
    s = pd.Series([*SPEED_TYPES, None], index=list("abcdefg"))
    three = multifactor.three_level_speeding(s)
    assert three.tolist() == ["no", "yes", "yes", "yes", "unknown", "unknown", "unknown"]
    assert three.index.tolist() == list("abcdefg")
    ex = multifactor.exceeded_levels(s)
    assert ex.tolist() == [
        "no",
        "yes",
        "other_speeding",
        "other_speeding",
        "unknown",
        "unknown",
        "unknown",
    ]


def test_lpv_selector():
    body = pd.Series(["car", "motorcycle", "suv", "unknown"])
    got = multifactor._lpv(body)
    assert got.dtype == bool
    assert got.tolist() == [b in multifactor.LPV_BODY_GROUPS for b in body]
    assert got[0] and not got[1]


def test_other_vehicle_behaviour_maps_no_other_vehicle_to_unknown():
    df = pd.DataFrame(
        {
            "lnk_other_speeding": ["yes", "no_other_vehicle", None],
            "lnk_other_alcohol_im": ["no", None, "no_other_vehicle"],
        }
    )
    out = multifactor._other_vehicle_behaviour(df)
    assert out["oth_speeding"].tolist() == ["yes", "unknown", "unknown"]
    assert out["oth_alcohol_im"].tolist() == ["no", "unknown", "unknown"]


def test_analysis_specifications_are_consistent():
    names = [a.name for a in multifactor.ANALYSES]
    assert len(names) == len(set(names))
    assert sum(a.registered for a in multifactor.ANALYSES) == 6  # the registered family
    for a in multifactor.ANALYSES:
        assert a.frame in {"crash", "driver", "person"}
        assert 2 <= len(a.factors) <= 4
        factor_cols = {f.column for f in a.factors}
        assert not factor_cols & set(a.covariates), a.name  # a factor is never also a covariate
        assert len(a.covariates) == len(set(a.covariates)), a.name
        for f in a.factors:
            assert not set(f.exposed) & set(f.reference)
    for v in multifactor.VICTIMS:
        assert v.frame in {"crash", "driver", "person"}
        assert len(v.behaviour_cols) == 2
    # Analyses with a time factor must not adjust for what night is made of.
    night = next(a for a in multifactor.ANALYSES if "night" in a.name)
    assert "tod" not in night.covariates and "light" not in night.covariates


def test_analysis_selectors_on_synthetic_frames():
    lpv = next(iter(multifactor.LPV_BODY_GROUPS))
    drv = pd.DataFrame(
        {
            "n_vehicles": ["1", "1", "2", "1"],
            "has_driver_record": [1, 0, 1, 1],
            "fatal": [1.0, 1.0, 0.0, NAN],
            "body": [lpv, lpv, lpv, "motorcycle"],
            "drv_restraint": ["belted", "none", "unknown", "belted"],
            "drv_killed": [1.0, 0.0, NAN, 0.0],
            "own_drugs_police": ["yes", "no", "unknown", "no"],
        }
    )
    by = {a.name: a for a in multifactor.ANALYSES}
    sv = by["sv_driver_exceeded_x_alcohol"].select(drv)
    assert sv.tolist() == [True, False, False, False]  # single-vehicle, has driver, known outcome
    lp = by["lpv_driver_speeding_x_alcohol_x_unbelted"].select(drv)
    assert lp.tolist() == [True, True, False, False]  # light vehicle, known death status
    drugs_known = by["lpv_driver_drugs_known_4way"].select(drv)
    assert drugs_known.tolist() == [True, True, False, False]
    assert (drugs_known <= lp).all()  # the drug-known subset is nested in the parent population

    per = pd.DataFrame(
        {
            "relation": ["passenger", "passenger", "driver", "passenger"],
            "body": [lpv] * 4,
            "restraint": ["belted", "none", "belted", "belted"],
            "age_band": ["25-34", "0-14", "25-34", "35-44"],
            "killed": [0.0, 0.0, 0.0, NAN],
        }
    )
    pas = by["passenger_driver_speeding_x_driver_alcohol_x_unbelted"].select(per)
    assert pas.tolist() == [True, False, False, False]  # passengers 15+, known outcome only


def _stub_factorial(monkeypatch, p_values):
    """Replace the model fit and table builders; keep the module's assembly and Holm logic."""
    calls = iter(range(10_000))

    class Res:
        n_events = 7
        meta = None  # set in __init__ (avoids a shared mutable class attribute)
        suppressed = None

        def __init__(self):
            self.meta = {"n_params": 3, "converged": True}
            self.suppressed = {"11"}

    monkeypatch.setattr(factorial, "fit_factorial", lambda *a, **k: Res())
    monkeypatch.setattr(
        factorial,
        "margins_table",
        lambda res: pd.DataFrame({"key": ["00", "11"], "adj_risk": [0.1, 0.2]}),
    )
    monkeypatch.setattr(factorial, "single_factor_table", lambda res: pd.DataFrame({"x": [1]}))

    def inter(res):
        i = next(calls)
        p = p_values[i % len(p_values)]
        return pd.DataFrame({"additive_contrast_p": [p], "multiplicative_ratio_p": [p / 2]})

    monkeypatch.setattr(factorial, "interaction_table", inter)


def test_run_analyses_assembly_and_holm_only_for_registered(monkeypatch):
    n = len(multifactor.ANALYSES)
    # One p-value per analysis, in order; the registered ones come first in ANALYSES.
    p = [0.001, 0.01, 0.02, 0.5, 0.04, 0.03] + [0.0001] * (n - 6)
    _stub_factorial(monkeypatch, p)
    frame = pd.DataFrame(
        {
            c: pd.Series(dtype=object)
            for c in (
                "n_vehicles",
                "has_driver_record",
                "fatal",
                "body",
                "drv_restraint",
                "drv_killed",
                "own_drugs_police",
                "night_period",
                "relation",
                "restraint",
                "age_band",
                "killed",
            )
        }
    )
    big = pd.DataFrame(index=range(3))
    for c in frame.columns:
        big[c] = ["x"] * 3

    class D:
        def subset(self, mask):
            return self

    # Each analysis' own selector would need realistic data; replace them with "all rows".
    monkeypatch.setattr(
        multifactor,
        "ANALYSES",
        [
            multifactor.Analysis(
                a.name,
                a.level,
                a.population,
                a.outcome_label,
                a.frame,
                lambda d: np.ones(len(d), bool),
                a.factors,
                a.covariates,
                a.outcome,
                a.registered,
                a.rationale,
            )
            for a in multifactor.ANALYSES
        ],
    )
    out = multifactor.run_analyses(
        {"crash": (big, D()), "driver": (big, D()), "person": (big, D())}
    )
    meta = out["analyses"]
    assert (
        len(meta) == n and meta["n_suppressed_cells"].eq(1).all() and meta["n_events"].eq(7).all()
    )
    inter_df = out["interactions"]
    assert inter_df.columns[:3].tolist() == ["analysis", "level", "registered"]
    assert out["margins"]["analysis"].nunique() == n
    reg = inter_df["registered"]
    assert reg.sum() == 6
    # Holm only over the registered family; exploratory rows stay NaN.
    assert inter_df.loc[~reg, "additive_contrast_p_holm"].isna().all()
    expected = factorial.holm(pd.Series(p[:6]))
    assert inter_df.loc[reg, "additive_contrast_p_holm"].to_numpy() == pytest.approx(
        expected.to_numpy()
    )
    assert (
        inter_df.loc[reg, "additive_contrast_p_holm"] >= inter_df.loc[reg, "additive_contrast_p"]
    ).all()
    assert inter_df.loc[reg, "multiplicative_ratio_p_holm"].notna().all()


def test_add_configuration_replaces_existing_columns_and_takes_vehicle_max(tmp_path, monkeypatch):
    import polars as pl

    from nhtsa_stats import config

    per = pl.DataFrame(
        {
            "YEAR": [2020, 2020, 2020],
            "case_id": [1, 1, 2],
            "VEH_NO": [1, 1, 1],
            "veh_rollover": [0, 1, None],
            "crash_type": ["mv_angle", "mv_angle", "sv_rollover_first"],
        }
    )
    per.write_parquet(tmp_path / "fars_person.parquet")
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    elig = pd.DataFrame(
        {
            "YEAR": [2020, 2020, 2020],
            "case_id": [1, 1, 2],
            "VEH_NO": [1, 1, 1],
            "veh_rollover": [0.0, 1.0, np.nan],  # already present: must not produce _x/_y columns
            "crash_type": ["x", "x", "x"],
        }
    )
    out = restraint_behaviour.add_configuration(elig)
    assert out["veh_rollover"].tolist()[:2] == [1.0, 1.0]  # vehicle-level max over occupants
    assert np.isnan(out["veh_rollover"].iloc[2])
    assert out["crash_type"].tolist() == ["mv_angle", "mv_angle", "sv_rollover_first"]
