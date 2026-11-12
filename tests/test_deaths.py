"""Deaths module: MI aggregation, overlap, victim roles, licence, restraint, vehicle age."""

from __future__ import annotations

import math

import polars as pl
import pytest

from nhtsa_stats.analysis import deaths as D


def _frame(rows: list[dict]) -> pl.DataFrame:
    base = {
        "YEAR": 2020,
        "ST_CASE": 1,
        "STATE": 1,
        "ptype": 1,
        "body": 1,
        "spd": False,
        "unbelted": False,
        "unhelmeted": False,
        "risk_spd": False,
        "risk_lt": False,
        "A_LT": 2,
        **{f"alc_{m}": False for m in D.IMPLICATES},
        **{f"risk_alc_{m}": False for m in D.IMPLICATES},
    }
    return pl.DataFrame([{**base, **r} for r in rows])


def test_mi_mean_and_se():
    df = pl.DataFrame({f"c{i}": [float(i)] for i in range(10)})
    cols = [pl.col(f"c{i}") for i in range(10)]
    mean = df.select(D.mi_mean(cols)).item()
    se = df.select(D.mi_se(cols)).item()
    b = sum((i - 4.5) ** 2 for i in range(10)) / 9
    assert mean == pytest.approx(4.5)
    assert se == pytest.approx(math.sqrt(1.1 * b))
    assert df.select(D.mi_se(cols[:1])).item() == 0.0


def test_agg_sums_and_all_counts_rows():
    df = _frame([{}, {}, {"ptype": 3}])
    out = D.long_counts(df, [], {"all": [D.ALL], "ped": [pl.col("ptype") == 3]})
    assert dict(zip(out["segment"], out["deaths"], strict=True)) == {"all": 3.0, "ped": 1.0}


def test_alcohol_segment_is_mi_mean():
    rows = [{f"alc_{m}": True for m in D.IMPLICATES}, {}]
    out = D.long_counts(_frame(rows), [], {"a": D._alc()})
    assert out["deaths"].item() == 1.0 and out["mi_se"].item() == 0.0
    rows = [{"alc_1": True}, {}]
    out = D.long_counts(_frame(rows), [], {"a": D._alc()})
    assert out["deaths"].item() == pytest.approx(0.1)
    assert out["mi_se"].item() > 0


def test_overlap_counts_all_flags_and_16_rows():
    rows = [
        {
            **{f"alc_{m}": True for m in D.IMPLICATES},
            "spd": True,
            "unbelted": True,
            "unhelmeted": True,
        },
        {},
        {"spd": True},
    ]
    t = D.overlap_table(_frame(rows))
    assert t.height == 16
    assert t["deaths"].sum() == pytest.approx(3.0)
    full = t.filter(
        (pl.col("alcohol") == 1)
        & (pl.col("speeding") == 1)
        & (pl.col("unbelted") == 1)
        & (pl.col("unhelmeted") == 1)
    )
    assert full["deaths"].item() == 1.0
    s = D.summary_table(_frame(rows)).to_dicts()
    by = {r["row"]: r for r in s}
    assert D.summary_table(_frame(rows)).columns[0] == "row"
    assert (
        by["exactly_1"]["deaths"],
        by["exactly_2"]["deaths"],
        by["three_or_more"]["deaths"],
    ) == (
        1.0,
        0.0,
        1.0,
    )
    seg = D.long_counts(
        _frame(rows),
        [],
        {
            k: v
            for k, v in D.segment_items().items()
            if k in ("alcohol_and_speeding", "two_or_more")
        },
    ).to_dicts()
    seg = {r["segment"]: r["deaths"] for r in seg}
    assert seg["alcohol_and_speeding"] == 1.0 and seg["two_or_more"] == 1.0
    assert by["any"]["deaths"] == 2.0 and by["none"]["deaths"] == 1.0
    assert by["sum_of_factors"]["deaths"] == 5.0
    assert by["sum_of_factors"]["overcount_ratio"] == pytest.approx(2.5)
    assert by["speeding"]["deaths_no_other_factor"] == 1.0


def test_victim_roles_each_group():
    all_a = {f"alc_{m}": True for m in D.IMPLICATES}
    risk_a = {f"risk_alc_{m}": True for m in D.IMPLICATES}
    rows = [
        {**all_a, **risk_a, "ptype": 1},
        {**all_a, **risk_a, "ptype": 2},
        {**all_a, "ptype": 1},
        {**all_a, "ptype": 3},
        {**all_a, "ptype": 5},
        {"spd": True, "risk_spd": True, "ptype": 1},
        {"spd": True, "ptype": 4},
        {"A_LT": 1, "risk_lt": True, "ptype": 2},
        {"A_LT": 1, "ptype": 1},
    ]
    t = D.victim_roles_table(_frame(rows))

    def get(g, r):
        return t.filter((pl.col("group") == g) & (pl.col("role") == r))["deaths"].item()

    assert get("alcohol_impaired", "risk_driver") == 1
    assert get("alcohol_impaired", "risk_passenger") == 1
    assert get("alcohol_impaired", "other_vehicle_occupant") == 1
    assert get("alcohol_impaired", "pedestrian_or_cyclist") == 1
    assert get("alcohol_impaired", "other_nonoccupant") == 1
    assert get("alcohol_impaired", "not_risk_driver") == 4
    assert get("speeding", "risk_driver") == 1 and get("speeding", "pedestrian_or_cyclist") == 1
    assert (
        get("large_truck", "risk_passenger") == 1
        and get("large_truck", "other_vehicle_occupant") == 1
    )


def test_driver_records_share_excludes_unknown():
    cols = {f"P{m}": 0 for m in D.IMPLICATES}
    rows = [
        {"YEAR": 2020, "L_STATUS": 0, "PREV_DWI": 1, "spveh": 2, **cols},
        {"YEAR": 2020, "L_STATUS": 6, "PREV_DWI": 0, "spveh": 2, **cols},
        {"YEAR": 2020, "L_STATUS": 9, "PREV_DWI": 99, "spveh": 1, **cols},
    ]
    extra = {f"PREV_{k}": 0 for k in ("SPD", "ACC", "SUS1", "SUS2", "SUS3")}
    df = pl.DataFrame([{**extra, **r} for r in rows])
    t = D.driver_records_table(df).filter(pl.col("group") == "all")
    lic = t.filter(pl.col("indicator") == "licence_invalid").row(0, named=True)
    assert lic["share"] == pytest.approx(0.5) and lic["n_known"] == 2
    dwi = t.filter(pl.col("indicator") == "prior_dwi").row(0, named=True)
    assert dwi["share"] == pytest.approx(0.5) and dwi["n_known"] == 2
    sus = t.filter(pl.col("indicator") == "prior_suspension").row(0, named=True)
    assert sus["n_known"] == 3


def test_use_table_bounds():
    df = pl.DataFrame({"use": [1, 1, 2, 2, 2, 3, 4], "g": ["a"] * 7})
    t = D.use_table(df, "use", "unbelted", {"grp": (pl.col("g"), ["a", "b"])})
    a = t.filter(pl.col("level") == "a").row(0, named=True)
    assert a["killed"] == 7 and a["known"] == 5 and a["unbelted"] == 3
    assert a["unbelted_share"] == pytest.approx(0.6)
    assert a["unknown_share"] == pytest.approx(2 / 7)
    assert a["share_if_unknown_protected"] == pytest.approx(3 / 7)
    assert a["share_if_unknown_unprotected"] == pytest.approx(5 / 7)
    assert (
        a["share_if_unknown_protected"] <= a["unbelted_share"] <= a["share_if_unknown_unprotected"]
    )
    assert a["flag"] == "" or a["flag"] is None or a["flag"] == "small"
    assert t.filter(pl.col("level") == "b")["killed"].item() == 0


def test_vehicle_age_bands_with_unknown_model_year():
    df = pl.DataFrame({"YEAR": [2020] * 7, "mod_year": [2019, 2015, 2010, 2005, 1990, 9999, 9998]})
    got = (
        df.with_columns(D.h.vehicle_age("mod_year", "YEAR").alias("a"))
        .select(D.h.vehicle_age_band("a").alias("b"))["b"]
        .to_list()
    )
    assert got == ["0-3", "4-7", "8-12", "13-17", "18+", "unknown", "unknown"]


def test_potential_lives_arithmetic():
    t = D.potential_lives_table(
        [("seat_belts", "as_recorded", 0.5, 0.4, 0.6)], {"seat_belts": 1000.0}, 9
    )
    r = t.row(0, named=True)
    assert (
        r["lives"] == 500
        and r["lives_low"] == pytest.approx(400)
        and r["lives_high"] == pytest.approx(600)
    )
    assert r["lives_per_year"] == pytest.approx(500 / 9)
    assert r["estimate_type"].startswith("hypothetical")


@pytest.mark.data
def test_pooled_totals_on_real_cache():
    drivers = D.build_driver_frame()
    d = D.build_death_frame(drivers)
    s = {r["segment"]: r["deaths"] for r in D.segments_table(d).to_dicts()}
    assert s["all"] == 353706
    assert s["speeding"] == 98693 and s["unbelted"] == 94400 and s["belted"] == 99879
    assert s["unhelmeted"] == 18789 and s["helmeted"] == 30800
    assert s["pedestrians"] == 60876 and s["cyclists"] == 8706
    assert s["pv_occupants"] == 215277 and s["motorcyclists"] == 51254
    assert s["alcohol_impaired"] == pytest.approx(105821.1, abs=0.1)


def _drivers(rows: list[dict]) -> pl.DataFrame:
    base = {
        "YEAR": 2020,
        "ST_CASE": 1,
        "VEH_NO": 1,
        "PER_NO": 1,
        "L_STATUS": 6,
        "PREV_DWI": 0,
        "PREV_SPD": 0,
        "PREV_ACC": 0,
        "PREV_SUS1": 0,
        "PREV_SUS2": 0,
        "PREV_SUS3": 0,
        "spveh": 2,
    }
    return pl.DataFrame([{**base, **r} for r in rows])


def _with_p(value: int | None) -> dict:
    return {f"P{m}": value for m in D.IMPLICATES}


def _measured_inputs():
    """Three drivers: measured .10, imputed .09 (in 4 of 10 implicates >= .08 only), measured .05."""
    imputed = {f"P{m}": 9 if m <= 4 else 2 for m in D.IMPLICATES}
    drivers = _drivers(
        [
            {"ST_CASE": 1, **_with_p(10), "PREV_DWI": 1},
            {"ST_CASE": 2, **imputed},
            {"ST_CASE": 3, **_with_p(5)},
            {"ST_CASE": 4, **_with_p(0)},
        ]
    )
    alc = pl.DataFrame(
        {
            "YEAR": [2020] * 4,
            "ST_CASE": [1, 2, 3, 4],
            "VEH_NO": [1] * 4,
            "PER_NO": [1] * 4,
            "ALC_RES": [100, 995, 50, 0],  # 995 = not reported: BAC imputed
        }
    )
    return D.add_measured_bac(drivers, alc)


def test_add_measured_bac_flags():
    d = _measured_inputs().sort("ST_CASE")
    assert d["bac_measured"].to_list() == [True, False, True, True]
    assert d["m_bac08"].to_list() == [True, False, False, False]


def test_add_measured_bac_counts_940_as_a_measured_result():
    """ALC_RES 940 means '.94 or greater': a measured (and >= .08) result, not a missing one."""
    drivers = _drivers([{"ST_CASE": i, **_with_p(5)} for i in range(1, 6)])
    alc = pl.DataFrame(
        {
            "YEAR": [2020] * 5,
            "ST_CASE": [1, 2, 3, 4, 5],
            "VEH_NO": [1] * 5,
            "PER_NO": [1] * 5,
            "ALC_RES": [939, 940, 995, 996, 79],
        }
    )
    d = D.add_measured_bac(drivers, alc).sort("ST_CASE")
    assert d["bac_measured"].to_list() == [True, True, False, False, True]
    assert d["m_bac08"].to_list() == [True, True, False, False, False]


def test_driver_bac_imputed_share_and_measured_records():
    d = _measured_inputs()
    t = (
        D.driver_bac_imputed_share_table(d)
        .filter(pl.col("period") == "2016-2024")
        .row(0, named=True)
    )
    assert t["n_measured"] == pytest.approx(1.0)  # driver 1
    assert t["n_imputed"] == pytest.approx(0.4)  # driver 2 is >= .08 in 4 of 10 implicates
    assert t["n_bac_08_plus"] == pytest.approx(1.4)
    assert t["share_imputed"] == pytest.approx(
        sum((1 / 2 if m <= 4 else 0.0) for m in D.IMPLICATES) / 10
    )
    assert t["mi_se"] > 0
    rec = D.driver_records_measured_table(d)
    dwi = rec.filter(pl.col("indicator") == "prior_dwi")

    def share(g: str) -> float:
        return dwi.filter(pl.col("group") == g)["share"].item()

    assert share("bac_08_plus_measured_only") == pytest.approx(1.0)  # the one measured driver
    assert share("bac_08_plus_imputed_only") == pytest.approx(0.0)
    assert dwi.filter(pl.col("group") == "bac_08_plus_measured_only")["n_group"].item() == 1


def test_victim_roles_bac_basis_splits_passengers_from_outsiders():
    all_a = {f"alc_{m}": True for m in D.IMPLICATES}
    risk_a = {f"risk_alc_{m}": True for m in D.IMPLICATES}
    meas = {"crash_m_alc": True}
    rows = [
        {**all_a, **risk_a, **meas, "ptype": 1},
        {**all_a, **risk_a, **meas, "ptype": 2},
        {**all_a, **meas, "ptype": 1},  # other vehicle's driver
        {**all_a, **meas, "ptype": 3},
        {**all_a, "ptype": 5},  # impaired only by imputation: not in the measured group
    ]
    base = {"crash_m_alc": False, "risk_m_alc": False}
    frame = _frame(
        [{**base, **r, **({"risk_m_alc": True} if "risk_alc_1" in r else {})} for r in rows]
    )
    t = D.victim_roles_bac_basis_table(frame)

    def get(b, r):
        return t.filter((pl.col("basis") == b) & (pl.col("role") == r))

    assert get("all_bac_measured_and_imputed", "total")["deaths"].item() == 5
    assert get("all_bac_measured_and_imputed", "outside_risk_vehicle")["deaths"].item() == 3
    assert get("measured_bac_only", "total")["deaths"].item() == 4
    assert get("measured_bac_only", "risk_passenger")["deaths"].item() == 1
    assert get("measured_bac_only", "outside_risk_vehicle")["deaths"].item() == 2
    assert get("measured_bac_only", "not_risk_driver")["share_of_group"].item() == pytest.approx(
        3 / 4
    )
    assert (
        get("measured_bac_only", "outside_risk_vehicle")["estimate_type"]
        .item()
        .startswith("observed")
    )
    assert get("all_bac_measured_and_imputed", "total")["estimate_type"].item() == D.ESTIMATED


def test_potential_lives_context_counts():
    rows = [
        {"unbelted": True, "pv": True, "n_occ": 1},
        {"unbelted": True, "pv": True, "n_occ": 1},
        {"unbelted": True, "pv": True, "n_occ": 3},
        {"belted": True, "pv": True, "n_occ": 2},
        {"restraint_unknown": True, "pv": True, "n_occ": 1},
        {"unhelmeted": True, "mc": True, "n_occ": 1},
        {"helmet_unknown": True, "mc": True, "n_occ": 2},
    ]
    base = {
        "unbelted": False,
        "belted": False,
        "restraint_unknown": False,
        "unhelmeted": False,
        "helmet_unknown": False,
        "pv": False,
        "mc": False,
    }
    d = pl.DataFrame([{**base, **r} for r in rows])
    t = D.potential_lives_context_table(d)
    get = lambda m: t.filter(pl.col("metric") == m).row(0, named=True)  # noqa: E731
    assert get("unbelted_deaths")["deaths"] == 3
    assert get("unknown_belt_use_deaths")["deaths"] == 1
    assert get("unknown_belt_use_deaths")["share"] == pytest.approx(1 / 5)
    assert get("unbelted_deaths_single_occupant_vehicle")["share"] == pytest.approx(2 / 3)
    assert get("unbelted_deaths_two_plus_occupant_vehicle")["deaths"] == 1
    assert get("unknown_helmet_use_deaths")["share"] == pytest.approx(1 / 2)


def test_read_effectiveness_raises_when_matched_tables_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(D.config, "TABLES_DIR", tmp_path)
    with pytest.raises(D.MatchedInputsError, match="nhtsa analyze matched"):
        D.read_effectiveness()
    (tmp_path / "matched").mkdir()
    pl.DataFrame({"estimand": ["x"], "estimate": [0.5], "low": [0.4], "high": [0.6]}).write_csv(
        tmp_path / "matched" / "belt_effect.csv"
    )
    pl.DataFrame({"analysis": ["a"]}).write_csv(tmp_path / "matched" / "double_pair_comparison.csv")
    with pytest.raises(D.MatchedInputsError, match="belt_effect"):
        D.read_effectiveness()


# --------------------------------------------------------------------------------------
# Red-team follow-up tables
# --------------------------------------------------------------------------------------
def test_large_truck_crash_types_split_by_vehicle_mix():
    veh = pl.DataFrame(
        {
            "YEAR": [2020] * 6,
            "ST_CASE": [1, 2, 2, 3, 3, 4],
            "A_BODY": [6, 6, 1, 6, 6, 6],
            "VEH_NO": [1, 1, 2, 1, 2, 1],
        }
    )
    mix = D.crash_vehicle_mix(veh)
    lt = {"A_LT": 1, "risk_lt": False}
    deaths = _frame(
        [
            # crash 1: single truck; the truck driver and a struck pedestrian die
            {"ST_CASE": 1, **lt, "ptype": 1, "risk_lt": True, "body": 6},
            {"ST_CASE": 1, **lt, "ptype": 3, "body": None},
            # crash 2: truck + car; the car driver, the car passenger and the truck driver die
            {"ST_CASE": 2, **lt, "ptype": 1, "body": 1},
            {"ST_CASE": 2, **lt, "ptype": 2, "body": 1},
            {"ST_CASE": 2, **lt, "ptype": 1, "risk_lt": True, "body": 6},
            # crash 3: two trucks only
            {"ST_CASE": 3, **lt, "ptype": 1, "risk_lt": True, "body": 6},
            {"ST_CASE": 3, **lt, "ptype": 1, "risk_lt": True, "body": 6},
            # crash 4: another single truck, the truck passenger dies
            {"ST_CASE": 4, **lt, "ptype": 2, "risk_lt": True, "body": 6},
            # not a large-truck crash: ignored
            {"ST_CASE": 5, "ptype": 1},
        ]
    )
    t = D.large_truck_crash_types_table(deaths, mix).to_dicts()
    by = {r["crash_type"]: r for r in t}
    assert by["single_truck"]["deaths"] == 3 and by["single_truck"]["not_truck_driver"] == 2
    assert by["single_truck"]["share_not_truck_driver"] == pytest.approx(2 / 3)
    assert by["single_truck"]["pedestrian_or_cyclist"] == 1
    assert by["single_truck"]["truck_passenger"] == 1
    tp = by["truck_and_passenger_vehicle"]
    assert tp["deaths"] == 3 and tp["not_truck_driver"] == 2 and tp["crashes"] == 1
    assert by["other_multi_vehicle_truck"]["share_not_truck_driver"] == 0.0
    assert by["all"]["deaths"] == 8 and by["all"]["not_truck_driver"] == 4
    assert sum(by[k]["deaths"] for k in D.TRUCK_CRASH_TYPES) == by["all"]["deaths"]
    two = by[D.TWO_VEHICLE_TRUCK_PV]  # a non-exclusive subset row: crash 2 only
    assert not two["exclusive_row"] and two["deaths"] == 3 and two["not_truck_driver"] == 2


def test_prior_dwi_by_state_flags_small_states_and_range():
    rows = []
    for i in range(120):  # state 1: 120 measured BAC >= .08 drivers, 60 with a prior DWI
        rows.append({"ST_CASE": i, "STATE": 1, **_with_p(10), "PREV_DWI": 1 if i < 60 else 0})
    for i in range(1000, 1010):  # state 2: 10 drivers, 10 with a prior DWI
        rows.append({"ST_CASE": i, "STATE": 2, **_with_p(10), "PREV_DWI": 2})
    for i in range(2000, 2005):  # state 4: PREV_DWI unknown for 5 of 105 drivers
        rows.append({"ST_CASE": i, "STATE": 4, **_with_p(10), "PREV_DWI": 99})
    for i in range(3000, 3100):
        rows.append({"ST_CASE": i, "STATE": 4, **_with_p(10), "PREV_DWI": 0})
    drivers = _drivers(rows)
    alc = drivers.select("YEAR", "ST_CASE", "VEH_NO", "PER_NO").with_columns(
        pl.lit(100).alias("ALC_RES")
    )
    dm = D.add_measured_bac(drivers, alc)
    t = D.prior_dwi_by_state_table(dm).filter(pl.col("bac_basis") == "all")
    r = {x["state"]: x for x in t.to_dicts()}
    assert r["AL"]["share"] == pytest.approx(0.5) and r["AL"]["n_group"] == pytest.approx(120)
    assert not r["AL"]["small"] and r["AK"]["small"]
    assert r["AK"]["share"] == pytest.approx(1.0)
    assert r["AZ"]["n_group"] == pytest.approx(105) and r["AZ"]["n_known"] == pytest.approx(100)
    assert r["AZ"]["share"] == 0.0
    meas = D.prior_dwi_by_state_table(dm).filter(pl.col("bac_basis") == "measured_only")
    assert meas["share"].to_list() == t["share"].to_list()  # every driver is measured here
    rng = D.prior_dwi_state_range_table(D.prior_dwi_by_state_table(dm))
    big = rng.filter((pl.col("bac_basis") == "all") & (pl.col("states") != "all states")).row(
        0, named=True
    )
    assert big["n_states"] == 2 and big["min_state"] == "AZ" and big["max_state"] == "AL"
    alls = rng.filter((pl.col("bac_basis") == "all") & (pl.col("states") == "all states")).row(
        0, named=True
    )
    assert alls["n_states"] == 3 and alls["max_state"] == "AK" and alls["max_share"] == 1.0
    assert alls["n_states_small"] == 1


def test_licence_trend_with_and_without_expired_cancelled():
    def drv(year, case, status):
        return {"YEAR": year, "ST_CASE": case, "L_STATUS": status}

    drivers = _drivers(
        [
            drv(2019, 1, 1),  # suspended
            drv(2019, 2, 6),  # valid
            drv(2019, 3, 3),  # expired
            drv(2021, 4, 1),
            drv(2021, 5, 1),
            drv(2021, 6, 4),  # cancelled
            drv(2021, 7, 3),  # expired
            drv(2021, 8, 6),
            drv(2024, 9, 99),  # unknown status: not in the denominator
            drv(2024, 10, 6),
        ]
    )
    deaths = _frame(
        [{"YEAR": y, "ST_CASE": c} for y, c in [(2019, 1), (2019, 1), (2019, 2), (2019, 3)]]
        + [{"YEAR": 2021, "ST_CASE": c} for c in (4, 5, 6, 7, 8)]
        + [{"YEAR": 2024, "ST_CASE": 10}]
    )
    t = D.licence_trend_table(deaths, drivers)

    def row(definition, measure):
        return t.filter((pl.col("definition") == definition) & (pl.col("measure") == measure)).row(
            0, named=True
        )

    a = row("invalid_incl_expired_cancelled", "deaths_in_invalid_licence_crashes")
    assert (a["value_2019"], a["value_2021"]) == (3, 4)
    assert a["pct_change_2019_2021"] == pytest.approx(4 / 3 - 1)
    b = row("invalid_excl_expired_cancelled", "deaths_in_invalid_licence_crashes")
    assert (b["value_2019"], b["value_2021"]) == (2, 2)
    assert b["pct_change_2019_2021"] == pytest.approx(0.0)
    c = row("invalid_incl_expired_cancelled", "driver_share")
    assert c["value_2019"] == pytest.approx(2 / 3) and c["value_2021"] == pytest.approx(4 / 5)
    assert c["value_2024"] == pytest.approx(0.0)  # one valid driver of known status
    assert row("expired_or_cancelled_only", "drivers")["value_2021"] == 2
