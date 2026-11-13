"""Tests of the tables added after the November 2026 red-team review (docs/red_team_2026-11.md):
four-factor overlap treatments, common-specification unit RRs, same-driver drug ORs,
non-differential drug bounds, the drug-definition reconciliation, the police-versus-BAC
selection tables and the alcohol-strata comparison with crash configuration."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import polars as pl
import pytest

from nhtsa_stats import config
from nhtsa_stats.analysis import (
    confounding,
    contributions,
    data,
    drugs,
    measurement,
    multifactor,
    speeding,
)
from nhtsa_stats.analysis.survey import SurveyDesign

NAN = np.nan


# --------------------------------------------------------------------------------------
# contributions: overlap treatments, determinacy columns, labels
# --------------------------------------------------------------------------------------
def _death_flags_stub():
    """Four deaths: (1) speeding + drug-positive crash with an undetermined second driver,
    (2) undetermined crash, (3) unbelted occupant in a determinate negative crash, (4) nothing
    except an alcohol-positive driver in 5 of the 10 implicates (determinate negative)."""
    flags = pd.DataFrame(
        {
            "speeding": [True, False, False, False],
            "unbelted": [False, False, True, False],
            "drug_positive": [True, False, False, False],
            "drug_undetermined": [False, True, False, False],
            "fully_determinate": [False, False, True, True],
        }
    )
    alc = np.zeros((4, 10), bool)
    alc[3, :5] = True
    return flags, alc


def test_overlap_treatments_floor_ceiling_determinate_and_no_drugs(monkeypatch):
    monkeypatch.setattr(contributions, "_death_flags", _death_flags_stub)
    out = contributions.overlap_treatments().set_index("drug_status_handling")
    floor = out.loc["undetermined = no drug"]
    ceil = out.loc["undetermined = drug"]
    known = out.loc[
        "undetermined deaths dropped (a driver positive, or every driver determinate negative)"
    ]
    det = out.loc[
        "undetermined deaths and positive crashes with an undetermined driver dropped "
        "(every driver's result known)"
    ]
    nod = out.loc["drugs not used"]
    # floor: deaths 1 and 3 always, death 4 half the time
    assert floor["share_with_any_factor"] == pytest.approx((1 + 0 + 1 + 0.5) / 4)
    assert floor["mean_factors_per_death"] == pytest.approx((2 + 0 + 1 + 0.5) / 4)
    # sum / union per implicate, averaged: 4/3 where death 4 is alcohol-positive, 3/2 otherwise
    assert floor["mean_factors_per_death_with_any"] == pytest.approx((4 / 3 + 3 / 2) / 2)
    # ceiling: the undetermined death now has a drug; never lower than the floor
    assert ceil["share_with_any_factor"] == pytest.approx((1 + 1 + 1 + 0.5) / 4)
    assert ceil["share_with_any_factor"] >= floor["share_with_any_factor"]
    assert ceil["mean_factors_per_death"] > floor["mean_factors_per_death"]
    # drug factor determinate: deaths 1, 3 and 4 (the undetermined death 2 is dropped)
    assert known["deaths_n"] == 3 and known["share_deaths_undetermined_drug_status"] == 0
    assert known["share_with_any_factor"] == pytest.approx((1 + 1 + 0.5) / 3)
    # fully determinate crashes only: deaths 3 and 4, no undetermined by construction
    assert det["deaths_n"] == 2 and det["share_deaths_undetermined_drug_status"] == 0
    assert det["share_with_any_factor"] == pytest.approx((1 + 0.5) / 2)
    # no drugs: death 1 keeps speeding, so its count drops from 2 to 1
    assert not nod["drugs_in_factor_set"]
    assert nod["mean_factors_per_death"] == pytest.approx((1 + 0 + 1 + 0.5) / 4)
    assert nod["share_deaths_undetermined_drug_status"] == pytest.approx(0.25)
    assert (out["deaths_n"] > 0).all()


def test_overlap_summary_reports_determinate_crashes_and_new_label():
    combos = pd.DataFrame(
        {
            "speeding": [0, 0, 1, 0, 0],
            "alcohol_bac08": [0, 0, 0, 1, 0],
            "unbelted_victim": [0, 0, 0, 0, 1],
            "drugs": ["yes", "undetermined", "no", "no", "no"],
            "deaths": [30.0, 40.0, 10.0, 10.0, 10.0],
        }
    )
    combos["n_factors"] = (
        combos["speeding"]
        + combos["alcohol_bac08"]
        + (combos["drugs"] == "yes")
        + combos["unbelted_victim"]
    )
    det = {"deaths_fully_determinate": 25.0, "deaths_drug_positive_fully_determinate": 15.0}
    out = contributions.overlap_summary(combos, 100, det).set_index("factor")
    assert contributions.DRUG_OVERLAP_LABEL in out.index
    assert "determinate crashes only" not in contributions.DRUG_OVERLAP_LABEL
    assert out.loc[contributions.DRUG_OVERLAP_LABEL, "deaths"] == 30
    assert (out["deaths_in_fully_determinate_crashes"] == 25).all()
    assert (out["share_deaths_in_fully_determinate_crashes"] == 0.25).all()
    assert (out["deaths_drug_positive_in_fully_determinate_crashes"] == 15).all()
    # without the argument the original columns are unchanged
    plain = contributions.overlap_summary(combos, 100)
    assert "deaths_in_fully_determinate_crashes" not in plain.columns


def test_rank_uncertainty_note_says_sampling_only():
    assert "sampling error only" in contributions.RANK_UNCERTAINTY_NOTE


# --------------------------------------------------------------------------------------
# drugs
# --------------------------------------------------------------------------------------
def _drivers(rows: list[dict]) -> pd.DataFrame:
    base = {
        "survival": "killed",
        "drv_drug_test_status": "tested",
        "drv_pr_drugs": NAN,
        "drv_pr_alcohol": NAN,
        "drv_bac08_measured": NAN,
        "drv_drug_any": NAN,
    }
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["drug_tested"] = (df["drv_drug_test_status"] == "tested").astype(float)
    return df


def test_prevalence_ratio_arithmetic():
    pr, lo, hi = drugs._prevalence_ratio(8, 2, 3, 7)
    assert pr == pytest.approx((8 / 10) / (3 / 10))
    se = np.sqrt(1 / 8 - 1 / 10 + 1 / 3 - 1 / 10)
    assert lo == pytest.approx(pr * np.exp(-1.96 * se)) and hi == pytest.approx(
        pr * np.exp(1.96 * se)
    )
    assert np.isnan(drugs._prevalence_ratio(0, 5, 3, 7)[0])


def test_same_driver_cooccurrence_uses_one_driver_set_for_both_sources():
    full = {"drv_bac08_measured": 1, "drv_drug_any": 1.0, "drv_pr_alcohol": 1, "drv_pr_drugs": 1}
    rows = (
        [full] * 4
        + [{**full, "drv_drug_any": 0.0, "drv_pr_drugs": 0}] * 2
        + [{**full, "drv_bac08_measured": 0, "drv_pr_alcohol": 0}] * 1
        + [
            {
                **full,
                "drv_bac08_measured": 0,
                "drv_pr_alcohol": 0,
                "drv_drug_any": 0.0,
                "drv_pr_drugs": 0,
            }
        ]
        * 3
        # excluded: no police drug field, no BAC, drug test not given, drug result indeterminate
        + [{**full, "drv_pr_drugs": NAN}] * 5
        + [{**full, "drv_bac08_measured": NAN}] * 5
        + [{**full, "drv_drug_test_status": "not_tested"}] * 5
        + [{**full, "drv_drug_any": NAN}] * 5
    )
    out = drugs.same_driver_cooccurrence(_drivers(rows))
    k = out[out["survival"] == "killed"].set_index("measure")
    assert (k["n"] == 10).all()  # one set, identical n for every measure
    tox = k.loc["toxicology: BAC >= .08 and any psychoactive drug"]
    assert tox["odds_ratio"] == pytest.approx(4 * 3 / (2 * 1))
    pol = k.loc["police report: alcohol and drugs both recorded"]
    # police fields are copies of the toxicology fields here, so the two ORs coincide
    assert pol["odds_ratio"] == pytest.approx(tox["odds_ratio"])
    assert tox["prevalence_ratio_drug_by_alcohol"] == pytest.approx((4 / 6) / (1 / 4))
    assert len(k) == len(drugs.SAME_DRIVER_MEASURES)
    assert out[out["survival"] == "survived"]["n"].eq(0).all()


def _fake_crash_frame():
    rows = [
        (2017, 1.0, 1, 10.0),
        (2017, 1.0, 0, 90.0),
        (2017, 0.0, 1, 20.0),
        (2017, 0.0, 0, 880.0),
        (2017, NAN, 1, 30.0),
        (2017, NAN, 0, 270.0),
    ]
    rows += [(2020, *r[1:]) for r in rows]
    df = pd.DataFrame(rows, columns=["YEAR", "drugs", "fatal", "WEIGHT"])
    design = SurveyDesign.from_arrays(df["WEIGHT"], np.zeros(len(df)), np.arange(len(df)))
    return df, design


def test_nondifferential_bounds_are_the_diagonal_and_nest_in_the_published_grid(monkeypatch):
    monkeypatch.setattr(data, "crss_crash", lambda outcome="fatal": _fake_crash_frame())
    out = drugs.crss_bounds_nondifferential()
    full = drugs.crss_bounds()
    p = out[(out["period"] == "2016-2018")]
    prop = p[p["parameter"] == "k"].set_index("parameter_value")["rr"]
    f = full[(full["period"] == "2016-2018") & (full["scenario"] == "k scenario")]
    for k in drugs.K_GRID:
        pub = f[(f["k_fatal"] == k) & (f["k_nonfatal"] == k)]["rr"].iloc[0]
        assert prop.loc[k] == pytest.approx(pub)
    # absolute prevalence 0 / 1 are the 'all unknown negative / positive' limits
    absolute = p[p["parameter"] == "e"].set_index("parameter_value")["rr"]
    neg = full[(full["period"] == "2016-2018") & (full["scenario"] == "all unknown negative")]
    pos = full[(full["period"] == "2016-2018") & (full["scenario"] == "all unknown positive")]
    assert absolute.loc[0.0] == pytest.approx(neg["rr"].iloc[0])
    assert absolute.loc[1.0] == pytest.approx(pos["rr"].iloc[0])
    # range rows: non-differential families sit inside the full published grid
    rng = p[p["row_type"] == "range"].set_index("allocation")
    grid = rng.loc["published grid (k_fatal, k_nonfatal in 0-3, any combination)"]
    nd = rng.loc["non-differential, proportional (k_fatal = k_nonfatal = k)"]
    assert grid["rr_min"] <= nd["rr_min"] < nd["rr_max"] <= grid["rr_max"]
    assert nd["rr_min"] == pytest.approx(prop.min()) and nd["rr_max"] == pytest.approx(prop.max())
    assert set(out["period"]) == {"2016-2018", "2019-2024", "2016-2024"}


def test_drug_definition_reconciliation_counts_and_ratio(monkeypatch, tmp_path):
    # crash: (FATALS, police field, driver results)
    crashes = {
        1: (2, 1, [1.0, None]),  # A and B (B partly undetermined)
        2: (3, 0, [1.0]),  # B not A
        3: (1, 1, [0.0]),  # A not B
        4: (4, None, [0.0, 0.0]),  # neither, determinate negative
        5: (5, 0, [0.0, None]),  # neither, undetermined
    }
    drv = [
        {"YEAR": 2020, "case_id": c, "drv_drug_any": r}
        for c, (_, _, rs) in crashes.items()
        for r in rs
    ]
    cr = [{"YEAR": 2020, "case_id": c, "FATALS": f, "drugs": p} for c, (f, p, _) in crashes.items()]
    pl.DataFrame(drv, schema_overrides={"drv_drug_any": pl.Float64}).write_parquet(
        tmp_path / "fars_driver.parquet"
    )
    pl.DataFrame(cr, schema_overrides={"drugs": pl.Int8}).write_parquet(
        tmp_path / "fars_crash.parquet"
    )
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    out = drugs.drug_definition_reconciliation()
    d = out.set_index("definition")
    a = d.loc["A: police crash-level drugs field = yes"]
    b = d.loc["B: any driver drug-positive on toxicology"]
    assert (a["deaths"], a["crashes"]) == (3, 2)
    assert (b["deaths"], b["crashes"]) == (5, 2)
    assert b["deaths_ratio_to_A"] == pytest.approx(5 / 3)
    ov = out[out["row_type"] == "overlap"].set_index("definition")
    assert ov.loc["A and B", "deaths"] == 2
    assert ov.loc["A not B", "deaths"] == 1
    assert ov.loc["B not A", "deaths"] == 3
    cross = out[out["row_type"] == "cross-tab"]
    assert cross["deaths"].sum() == 15 and cross["crashes"].sum() == 5


# --------------------------------------------------------------------------------------
# measurement: who is tested, and police sensitivity by testing breadth
# --------------------------------------------------------------------------------------
def test_wilson_interval_properties():
    lo, hi = measurement._wilson(50, 100)
    assert lo < 0.5 < hi and hi - lo == pytest.approx(0.19, abs=0.01)
    lo0, hi0 = measurement._wilson(0, 20)
    assert lo0 == pytest.approx(0.0, abs=1e-12) and hi0 > 0
    assert np.isnan(measurement._wilson(0, 0)[0])


def _drv_frame() -> pd.DataFrame:
    """Three states; survivors are tested rarely in state 1 (20%), half the time in state 3 and
    widely in state 2 (80%).  Police sensitivity among tested survivors: state 1 100%, state 2
    50%, state 3 100%."""
    rows = []

    def add(state, status, tested, bac, police, n=1):
        for _ in range(n):
            rows.append(
                {
                    "ptype": "driver",
                    "STATE": state,
                    "YEAR": 2020,
                    "driver_status": status,
                    "killed": 1.0 if status == "killed" else 0.0,
                    "alc_tested": tested,
                    "bac_measured": bac,
                    "pr_alcohol": police,
                }
            )

    # state 1: 10 survivors, 2 tested (both BAC .10 and police yes)
    add(1, "survived", 1.0, 0.10, 1, 2)
    add(1, "survived", 0.0, NAN, 0, 8)
    # state 2: 10 survivors, 8 tested; of them 4 with BAC .10 of which 2 reported
    add(2, "survived", 1.0, 0.10, 1, 2)
    add(2, "survived", 1.0, 0.10, 0, 2)
    add(2, "survived", 1.0, 0.01, 0, 4)
    add(2, "survived", 0.0, NAN, 0, 2)
    # state 3: 10 survivors, 5 tested (all BAC .10 and reported)
    add(3, "survived", 1.0, 0.10, 1, 5)
    add(3, "survived", 0.0, NAN, 0, 5)
    # killed drivers in every state: 10 tested, 5 with BAC .10, 4 reported
    for st in (1, 2, 3):
        add(st, "killed", 1.0, 0.10, 1, 4)
        add(st, "killed", 1.0, 0.10, 0, 1)
        add(st, "killed", 1.0, 0.0, 0, 5)
    return pd.DataFrame(rows)


def test_alcohol_testing_share_and_sample():
    out = measurement.alcohol_testing_share(_drv_frame()).set_index("driver_status")
    s = out.loc["survived"]
    assert s["n_drivers"] == 30 and s["n_alcohol_tested"] == 15
    assert s["share_alcohol_tested"] == pytest.approx(0.5)
    assert s["n_in_sensitivity_sample"] == 15
    assert s["bac08_prevalence_in_sample"] == pytest.approx(11 / 15)
    k = out.loc["killed"]
    assert k["share_alcohol_tested"] == 1.0 and k["n_in_sensitivity_sample"] == 30
    assert out.loc["all (killed + survived)", "n_drivers"] == 60


def test_police_vs_bac_selection_sensitivity_falls_as_testing_broadens():
    out = measurement.police_vs_bac_selection(_drv_frame())
    surv = out[(out["driver_status"] == "survived") & (out["scheme"] == "all")].iloc[0]
    assert surv["police_sensitivity_vs_bac08"] == pytest.approx(9 / 11)
    assert surv["n_in_sample"] == 15 and surv["sensitivity_low"] < 9 / 11 < surv["sensitivity_high"]
    t = out[
        (out["scheme"] == "state-year survivor test-rate tercile")
        & (out["driver_status"] == "survived")
    ].set_index("group")
    # state 1 (20% tested) is the low group with 100% sensitivity, state 2 (80%) the high group
    assert t.loc["low", "police_sensitivity_vs_bac08"] == pytest.approx(1.0)
    assert t.loc["middle", "police_sensitivity_vs_bac08"] == pytest.approx(1.0)
    assert t.loc["high", "police_sensitivity_vs_bac08"] == pytest.approx(0.5)
    assert (
        t.loc["low", "group_survivor_test_rate_max"] < t.loc["high", "group_survivor_test_rate_min"]
    )
    cum = out[
        out["scheme"].str.startswith("cumulative") & (out["driver_status"] == "survived")
    ].set_index("group")
    assert cum.loc["0%", "n_drivers"] == 30 and cum.loc["50%", "n_drivers"] == 20
    assert cum.loc["50%", "police_sensitivity_vs_bac08"] == pytest.approx(7 / 9)
    # killed drivers are reported for the same places
    assert (out["driver_status"] == "killed").sum() == (out["driver_status"] == "survived").sum()


# --------------------------------------------------------------------------------------
# multifactor: common-specification victims and strata with crash configuration
# --------------------------------------------------------------------------------------
def test_common_spec_is_identical_across_units_and_published_rows_use_unit_covariates(monkeypatch):
    seen = []

    def fake_record(v, df, design, covariates):
        seen.append((v.name, tuple(covariates), "age_band" in df))
        return {"victim": v.name, "n": 1}

    monkeypatch.setattr(multifactor, "_victim_record", fake_record)
    frames = {
        "crash": (pd.DataFrame({"x": [1]}), None),
        "driver": (pd.DataFrame({"age": ["25-34"]}), None),
        "person": (pd.DataFrame({"age_band": ["25-34"]}), None),
    }
    out = multifactor.victims_common_spec_table(frames)
    assert len(out) == 3 * (len(multifactor.VICTIMS) - 1)
    assert "crash fatal (any driver's behaviour)" not in set(out["victim"])
    by_spec = out.groupby("specification")["covariates"].nunique()
    assert by_spec["common: environment + victim age band + sex"] == 1
    assert by_spec["common + crash configuration"] == 1
    assert by_spec["unit-specific (published)"] == len(multifactor.VICTIMS) - 1  # all differ
    common = out[out["specification"].str.startswith("common:")]["covariates"].iloc[0].split(",")
    assert common == [*multifactor.ENV, "age_band", "sex"]
    assert all(has_band for _, _, has_band in seen)  # the driver frame is given an age band
    # the published rows use exactly the unit-specific covariates minus the behaviours
    pub = {v.name: v for v in multifactor.VICTIMS}
    for _, r in out[out["specification"] == "unit-specific (published)"].iterrows():
        v = pub[r["victim"]]
        assert r["covariates"].split(",") == [c for c in v.covariates if c not in v.behaviour_cols]


def test_victims_table_uses_unit_specific_covariates(monkeypatch):
    got = []
    monkeypatch.setattr(
        multifactor,
        "_victim_record",
        lambda v, df, design, covs: got.append(list(covs)) or {"victim": v.name},
    )
    frames = {k: (pd.DataFrame(), None) for k in ("crash", "driver", "person")}
    multifactor.victims_table(frames)
    assert got == [list(v.covariates) for v in multifactor.VICTIMS]


def test_strata_configuration_adds_only_the_configuration_block(monkeypatch):
    n = 40
    df = pd.DataFrame(
        {
            "alcohol_im": pd.Categorical(["no"] * 30 + ["yes"] * 10),
            "speeding_type": pd.Categorical(["no", "exceeded_limit_or_racing"] * 20),
            "speeding": pd.Categorical(["no", "yes"] * 20),
            "fatal": np.tile([0.0, 1.0, 0.0, 0.0], 10),
            "ka": np.tile([0.0, 1.0, 1.0, 0.0], 10),
        }
    )
    design = SurveyDesign.from_arrays(np.ones(n), np.zeros(n), np.arange(n))
    monkeypatch.setattr(speeding, "load_frame", lambda: (df, design))
    monkeypatch.setattr(
        speeding,
        "strata_definitions",
        lambda d: {
            "alcohol_imputed": (
                {
                    "no alcohol": (d["alcohol_im"] == "no").to_numpy(),
                    "alcohol": (d["alcohol_im"] == "yes").to_numpy(),
                },
                ("alcohol",),
            )
        },
    )
    monkeypatch.setattr(
        confounding, "cluster_design", lambda d: SimpleNamespace(tcrit=lambda: 2.0, df=42)
    )
    calls = []

    def fake_fit(sub, sd, ex, blocks, outcome):
        calls.append((ex.name, tuple(blocks), outcome))
        return SimpleNamespace(log_rr=np.log(3.0), t_log_rr=0.0, m_exposed=0.03, m_reference=0.01)

    monkeypatch.setattr(confounding, "fit_subset", fake_fit)
    monkeypatch.setattr(multifactor, "MarginSet", lambda *a, **k: None)
    monkeypatch.setattr(confounding, "linear_contrast", lambda ms, coefs: (np.log(3.0), 0.1))
    out = multifactor.speeding_alcohol_strata_configuration(outcomes=("fatal",))
    base = [
        b for b in speeding.EXPOSURES["exceeded"].blocks if b not in ("configuration", "alcohol")
    ]
    published = [c for c in calls if c[0] == "exceeded" and "configuration" not in c[1]]
    with_cfg = [c for c in calls if c[0] == "exceeded" and "configuration" in c[1]]
    assert published and with_cfg
    assert all(list(c[1]) == base for c in published)
    assert all(list(c[1]) == [*base, "configuration"] for c in with_cfg)
    assert all("alcohol" not in c[1] for c in calls)  # alcohol is the stratifier
    assert set(out["specification"]) == {
        "published strata specification (no crash configuration)",
        "+ crash configuration",
    }
    # one ratio per (exposure, outcome, specification), carried on the second stratum row
    assert out["ratio_alcohol_to_no_alcohol"].notna().sum() == 4
    assert np.allclose(out["rr"], 3.0)
