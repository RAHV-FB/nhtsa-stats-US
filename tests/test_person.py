"""Tests of the CRSS person-level module (software tests on synthetic data + a real smoke test).

Synthetic data here only exercise the code; they are never findings.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
import pytest

from nhtsa_stats import config
from nhtsa_stats.analysis import data, person, specs
from nhtsa_stats.analysis.survey import ModelSpec, SurveyDesign, SurveyLogit


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(11)


def _synthetic_people(rng: np.random.Generator, n: int = 6000) -> tuple[pd.DataFrame, SurveyDesign]:
    strata = rng.integers(0, 4, n)
    psu = strata * 10 + rng.integers(0, 3, n)
    w = rng.uniform(5, 50, n)
    df = pd.DataFrame(
        {
            "restraint": rng.choice(["belted", "none"], n, p=[0.85, 0.15]),
            "age_band": rng.choice(["25-34", "15-20", "75+"], n),
            "sex": rng.choice(["male", "female"], n),
            "light": rng.choice(["daylight", "dark_lighted"], n),
        }
    )
    eta = (
        -4.0
        + 1.6 * (df["restraint"] == "none")
        + 0.9 * (df["age_band"] == "75+")
        - 0.3 * (df["age_band"] == "15-20")
        + 0.2 * (df["sex"] == "female")
        + 0.5 * (df["light"] == "dark_lighted")
        + 0.6 * ((df["restraint"] == "none") & (df["age_band"] == "75+"))
    )
    df["y"] = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(float)
    return df, SurveyDesign.from_arrays(w, strata, psu)


SPEC_LEVELS = {
    "restraint": ["belted", "none"],
    "age_band": ["25-34", "15-20", "75+"],
    "sex": ["male", "female"],
    "light": ["daylight", "dark_lighted"],
}


@pytest.mark.parametrize("use_domain", [False, True])
def test_lean_margins_identical_to_parent(rng, use_domain):
    df, design = _synthetic_people(rng)
    spec = ModelSpec(categorical=SPEC_LEVELS, interactions=[("restraint", "age_band")])
    base = SurveyLogit(spec, ridge=0.01).fit(df, df["y"].to_numpy(), design)
    lean = person.LeanSurveyLogit(spec, ridge=0.01, chunk_rows=777).fit(
        df, df["y"].to_numpy(), design
    )
    np.testing.assert_allclose(lean.coef_, base.coef_)
    domain = (df["sex"] == "female").to_numpy() if use_domain else None
    for setter in (None, lambda d: d.assign(restraint="none", age_band="75+")):
        m0, z0 = base.margin_influence(df, setter, domain)
        m1, z1 = lean.margin_influence(df, setter, domain)
        assert m1 == pytest.approx(m0, rel=1e-12)
        np.testing.assert_allclose(z1, z0, rtol=1e-9, atol=1e-15)


def test_interaction_table_measures_are_consistent(rng):
    df, design = _synthetic_people(rng)
    spec = ModelSpec(categorical=SPEC_LEVELS, interactions=[("restraint", "age_band")])
    model = person.LeanSurveyLogit(spec).fit(df, df["y"].to_numpy(), design)
    tab = person.interaction_table(
        model, df, "y", "restraint", "belted", "none", "age_band", SPEC_LEVELS["age_band"]
    )
    assert list(tab["b_level"]) == SPEC_LEVELS["age_band"]
    ref = tab.iloc[0]
    for _, r in tab.iloc[1:].iterrows():
        ic = (
            r["risk_a_exposed"]
            - ref["risk_a_exposed"]
            - r["risk_a_reference"]
            + ref["risk_a_reference"]
        )
        assert r["ic"] == pytest.approx(ic, rel=1e-6)
        assert r["reri"] == pytest.approx(ic / ref["risk_a_reference"], rel=1e-5)
        assert r["ratio_of_rr"] == pytest.approx(r["rr"] / ref["rr"], rel=1e-5)
        assert r["ic_low"] < r["ic"] < r["ic_high"]
    # within-stratum RR equals the ratio of the two standardised risks
    np.testing.assert_allclose(tab["rr"], tab["risk_a_exposed"] / tab["risk_a_reference"])
    # cell counts are the observed persons in each (a, b) cell
    cell = (df["restraint"] == "none") & (df["age_band"] == "75+")
    assert int(tab.loc[tab["b_level"] == "75+", "n_a_exposed"].iloc[0]) == int(cell.sum())


def test_check_features_blocks_post_crash_and_design_vars():
    person.check_features(["restraint", "age_band", "other_vehicle_body", "YEAR", "rider"])
    for bad in (["ejected"], ["airbag_deployed"], ["WEIGHT"], ["killed"], ["not_a_var"]):
        with pytest.raises(ValueError):
            person.check_features(bad)


def test_holm_matches_hand_computation():
    p = np.array([0.01, 0.04, 0.03, np.nan])
    out = person.holm(p)
    # sorted 0.01, 0.03, 0.04 -> 3*0.01, max(0.03, 2*0.03), max(0.06, 1*0.04)
    np.testing.assert_allclose(out[:3], [0.03, 0.06, 0.06])
    assert np.isnan(out[3])


def _nullable(rng: np.random.Generator, values: list, n: int, dtype: pl.DataType) -> pl.Series:
    """Random column drawn from ``values`` where None becomes a null of ``dtype``."""
    idx = rng.integers(0, len(values), n)
    return pl.Series([values[i] for i in idx], dtype=dtype)


def _write_synthetic_processed(tmp_path, rng: np.random.Generator, n: int = 400) -> None:
    cases = rng.integers(1, 120, n)
    years = rng.choice([2019, 2020], n)
    strat = (cases % 5).astype(int)
    psu = strat * 3 + (cases % 3)
    per = pl.DataFrame(
        {
            "YEAR": years,
            "case_id": cases,
            "PER_TYP": rng.choice([1, 2, 3, 5, 9], n),
            "WEIGHT": rng.uniform(10, 90, n),
            "PSUSTRAT": strat,
            "PSU_VAR": psu,
            "STRATUM": strat,
            "age": _nullable(rng, [5, 30, 70, None], n, pl.Int64),
            "age_band": rng.choice(["0-14", "25-34", "65-74", "unknown"], n),
            "sex": rng.choice(["male", "female", "unknown"], n),
            "role": rng.choice(["driver", "front_passenger", "rear_passenger"], n),
            "restraint": rng.choice(["belted", "none", "unknown", "not_applicable"], n),
            "helmet": rng.choice(["helmet", "none", "not_applicable"], n),
            "body": rng.choice(["car", "suv", "motorcycle", "bus"], n),
            "veh_age_band": rng.choice(["0-3", "8-12"], n),
            "other_vehicle_body": rng.choice(["none_or_multi", "car"], n),
            "crash_type": rng.choice(["mv_angle", "sv_off_roadway"], n),
            "n_vehicles": rng.choice(["1", "2"], n),
            "killed": _nullable(rng, [0, 1, None], n, pl.Int8),
            "killed_or_serious": _nullable(rng, [0, 1, None], n, pl.Int8),
            "region": rng.choice(["south", "west"], n),
            "urbanicity": rng.choice(["urban", "rural"], n),
            "tod": rng.choice(["10-15", "20-23"], n),
            "weekend": _nullable(rng, [0, 1, None], n, pl.Int8),
            "light": rng.choice(["daylight", "dark_lighted"], n),
            "weather": rng.choice(["clear", "rain"], n),
            "surface": rng.choice(["dry", "wet"], n),
            "speed_limit": rng.choice(["30-35", "50-55"], n),
            "interstate": _nullable(rng, [0, 1], n, pl.Int8),
            "junction": rng.choice(["non_junction", "intersection"], n),
            "work_zone": _nullable(rng, [0, None], n, pl.Int8),
            "any_motorcycle": _nullable(rng, [0, 1], n, pl.Int8),
            "any_heavy_truck": _nullable(rng, [0, 1], n, pl.Int8),
            "speeding": _nullable(rng, [0, 1, None], n, pl.Int8),
            "alcohol_im": _nullable(rng, [0, 1], n, pl.Int8),
        }
    )
    crash = (
        per.select("YEAR", "case_id")
        .unique()
        .with_columns(
            pl.lit(1, dtype=pl.Int8).alias("young_driver"),
            pl.lit(None, dtype=pl.Int8).alias("older_driver"),
        )
    )
    per.write_parquet(tmp_path / "crss_person.parquet")
    crash.write_parquet(tmp_path / "crss_crash.parquet")


@pytest.mark.parametrize("outcome", ["killed", "killed_or_serious"])
def test_load_occupants_equals_shared_loader(tmp_path, monkeypatch, rng, outcome):
    _write_synthetic_processed(tmp_path, rng)
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    ref, ref_design = data.crss_person(outcome=outcome, occupants_only=True)
    mine, design = person.load_occupants(outcome)
    assert len(mine) == len(ref)
    np.testing.assert_array_equal(design.weight, ref_design.weight)
    np.testing.assert_array_equal(design.cluster, ref_design.cluster)
    np.testing.assert_array_equal(design.cluster_stratum, ref_design.cluster_stratum)
    for c in ["case_id", "age", "body", "restraint", outcome]:
        a = mine[c].astype(object).where(mine[c].notna(), None).tolist()
        b = ref[c].astype(object).where(ref[c].notna(), None).tolist()
        assert a == b, c
    # tri-state conversion and attached crash-level columns
    assert set(pd.unique(mine["speeding"].astype(object))) <= {"yes", "no", "unknown"}
    assert (mine["young_driver"].astype(object) == "yes").all()
    assert (mine["older_driver"].astype(object) == "unknown").all()


def test_build_populations_rules(tmp_path, monkeypatch, rng):
    _write_synthetic_processed(tmp_path, rng, n=800)
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    df, design = person.load_occupants("killed")
    pops = person.build_populations(df, design)
    lpv, mc = pops["lpv"].df, pops["motorcycle"].df
    assert set(lpv["body"].astype(object)) <= set(person.LPV_BODIES)
    assert (lpv["age"] >= person.MIN_RESTRAINT_AGE).all()
    assert "0-14" not in set(lpv["age_band"].astype(object))
    assert set(mc["rider"].astype(object)) <= {"operator", "passenger"}
    assert "not_applicable" not in set(mc["helmet"].astype(object))
    # designs keep the full cluster universe of the person file
    assert pops["lpv"].design.n_clusters == design.n_clusters
    assert pops["lpv"].design.n == len(lpv)


def test_population_flow_counts(tmp_path, monkeypatch, rng):
    _write_synthetic_processed(tmp_path, rng, n=800)
    monkeypatch.setattr(config, "PROCESSED_DIR", tmp_path)
    df, design = person.load_occupants("killed")
    flow = person.population_flow(df, design, "killed").set_index("step")["n_persons"]
    lpv = flow["  light passenger vehicle occupants"]
    parts = (
        flow["    age unknown (excluded)"]
        + flow[f"    age < {person.MIN_RESTRAINT_AGE} (excluded)"]
        + flow[f"    LPV analysis population (age {person.MIN_RESTRAINT_AGE}+)"]
    )
    assert lpv == parts


def test_specs_levels_cover_person_levels():
    assert person.LPV_LEVELS["age_band"][0] == "25-34"
    assert set(person.LPV_LEVELS["restraint"]) <= set(specs.PERSON_LEVELS["restraint"])
    assert person.MC_LEVELS["rider"] == ["operator", "passenger"]


# --------------------------------------------------------------------------------------
# Real data smoke test
# --------------------------------------------------------------------------------------
@pytest.mark.processed
def test_real_data_motorcycle_smoke():
    df, design = person.load_occupants("killed")
    flow = person.population_flow(df, design, "killed")
    assert flow["n_persons"].iloc[0] > 900_000
    pops = person.build_populations(df, design)
    assert len(pops["lpv"].df) > 800_000
    res, coef = person.crude_vs_adjusted(pops["motorcycle"], "killed", factors=["helmet"])
    none = res.loc[res["level"] == "none"].iloc[0]
    assert none["n"] >= config.MIN_CELL_N
    assert np.isfinite([none["A_adj_rr"], none["A_adj_rr_low"], none["A_adj_rr_high"]]).all()
    assert none["A_adj_rr_low"] < none["A_adj_rr"] < none["A_adj_rr_high"]
    assert coef.attrs["meta"]["converged_A"]
