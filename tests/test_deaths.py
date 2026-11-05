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


def test_licence_categories_with_unknown():
    df = pl.DataFrame({"L_STATUS": [0, 1, 2, 3, 4, 6, 7, 9, None]})
    got = df.select(D.licence_category().alias("c"))["c"].to_list()
    assert got == [
        "unlicensed",
        "suspended_or_revoked",
        "suspended_or_revoked",
        "expired_or_cancelled",
        "expired_or_cancelled",
        "valid",
        "unknown",
        "unknown",
        "unknown",
    ]


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
