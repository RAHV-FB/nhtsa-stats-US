"""Driver / occupant linkage on synthetic frames: ``person_link``, ``driver_rows`` and the
CRSS / FARS driver builders (table loaders are replaced by in-memory frames)."""

from __future__ import annotations

import polars as pl
import pytest

from nhtsa_stats.processing import drivers as dv
from nhtsa_stats.processing import features as ft

KV = ["YEAR", "CASENUM", "VEH_NO"]


def _per() -> pl.DataFrame:
    """Case 1: veh 1 (driver + passenger), veh 2 (driver, killed), a pedestrian struck by veh 2,
    a pedestrian with unknown striking vehicle, a cyclist struck by veh 999 (unknown), and a
    parked-vehicle occupant (veh 3, not in the vehicle file).  Case 2: one lone driver."""
    rows = [
        # year, case, veh, per, per_typ, str_veh, killed
        (2020, 1, 1, 1, 1, 0, 0),
        (2020, 1, 1, 2, 2, 0, 0),
        (2020, 1, 2, 1, 1, 0, 1),
        (2020, 1, 0, 1, 5, 2, 1),  # pedestrian struck by veh 2
        (2020, 1, 0, 2, 5, 0, 0),  # pedestrian, striking vehicle not an in-transport one
        (2020, 1, 0, 3, 6, 999, 0),  # cyclist, unknown striking vehicle
        (2020, 1, 3, 1, 2, 0, 0),  # occupant of a parked vehicle
        (2020, 2, 1, 1, 1, 0, 0),
        (2021, 1, 1, 1, 1, 0, 0),  # same case number, other year: must not collide
    ]
    return pl.DataFrame(
        rows,
        schema=[*KV, "PER_NO", "PER_TYP", "STR_VEH", "killed"],
        orient="row",
    )


@pytest.fixture
def patched_loader(monkeypatch):
    per = _per()

    def fake_load(source, table, years=None, columns=None, **_):
        assert table == "person"
        case = ft.CASE[source]
        return per.rename({"CASENUM": case}).select(["YEAR", case, "VEH_NO", "PER_NO", "STR_VEH"])

    monkeypatch.setattr(dv, "load_table", fake_load)
    return per


def test_person_link_occupants_link_to_own_vehicle(patched_loader):
    link = dv.person_link("CRSS", [2020, 2021], patched_loader)
    occ = link.filter(pl.col("PER_TYP").is_in(dv.OCCUPANT_TYPES))
    assert occ.height == 6
    assert (occ["linked_veh_no"] == occ["VEH_NO"]).all()
    rel = {
        (r["YEAR"], r["case_id"], r["VEH_NO"], r["PER_NO"]): r["relation"]
        for r in occ.iter_rows(named=True)
    }
    assert rel[(2020, 1, 1, 1)] == "driver"
    assert rel[(2020, 1, 1, 2)] == "passenger"
    assert rel[(2020, 1, 3, 1)] == "passenger"


def test_person_link_one_row_per_person_and_all_persons_kept(patched_loader):
    link = dv.person_link("CRSS", [2020, 2021], patched_loader)
    keys = ["YEAR", "case_id", "VEH_NO", "PER_NO"]
    assert link.select(keys).is_duplicated().sum() == 0
    assert (
        link.height == patched_loader.height
    )  # every fixture person is an occupant or non-motorist
    assert link.columns == [*keys, "PER_TYP", "relation", "linked_veh_no"]


def test_person_link_non_motorists_use_striking_vehicle(patched_loader):
    link = dv.person_link("CRSS", [2020, 2021], patched_loader)
    nm = link.filter(pl.col("relation") == "non_motorist").sort("PER_NO")
    assert nm["PER_TYP"].to_list() == [5, 5, 6]
    assert nm["linked_veh_no"].to_list() == [2, None, None]  # 0 and 999 leave the link null


def test_person_link_excludes_other_person_types(patched_loader):
    per = pl.concat(
        [
            patched_loader,
            pl.DataFrame(
                [(2020, 1, 4, 1, 3, 0, 0)],  # PER_TYP 3 is neither occupant nor non-motorist
                schema=patched_loader.schema,
                orient="row",
            ),
        ]
    )
    link = dv.person_link("CRSS", [2020], per)
    assert 3 not in link["PER_TYP"].to_list()
    assert link.height == patched_loader.height


def test_driver_rows_one_driver_per_vehicle_lowest_per_no():
    per = pl.DataFrame(
        {
            "YEAR": [2020] * 5,
            "CASENUM": [1, 1, 1, 1, 1],
            "VEH_NO": [1, 1, 1, 2, 3],
            "PER_NO": [3, 1, 2, 1, 1],
            "PER_TYP": [1, 1, 2, 2, 1],  # veh 1: two driver records; veh 2: passenger only
            "age": [40, 30, 10, 20, 50],
        }
    )
    drv = dv.driver_rows(per, KV, ["PER_NO", "age"]).sort("VEH_NO")
    assert drv.columns == [*KV, "drv_PER_NO", "drv_age"]
    assert drv["VEH_NO"].to_list() == [1, 3]  # no driver record for veh 2: no row
    assert drv["drv_PER_NO"].to_list() == [1, 1]  # lowest PER_NO kept
    assert drv["drv_age"].to_list() == [30, 50]
    assert drv.select(KV).is_duplicated().sum() == 0


def _crss_inputs():
    per = pl.DataFrame(
        {
            "YEAR": [2020] * 5,
            "CASENUM": [1, 1, 1, 1, 2],
            "VEH_NO": [1, 1, 2, 3, 1],
            "PER_NO": [1, 2, 1, 1, 1],
            "PER_TYP": [1, 2, 1, 2, 1],
            "STR_VEH": [0] * 5,
            "killed": [0, 0, 1, 0, 0],
            "kabco": [0, 0, 4, 0, 0],
            "killed_or_serious": [0, 0, 1, 0, 0],
            "age": [30, 8, 45, 5, 60],
            "age_im": [30, 8, 45, 5, 60],
            "age_band": ["25-34", "0-14", "45-54", "0-14", "55-64"],
            "sex": ["male", "female", "male", "male", "female"],
            "restraint": ["belted", "belted", "none", "belted", "belted"],
            "helmet": [None] * 5,
            "pr_alcohol": [0, 0, 1, 0, None],
            "pr_drugs": [0, 0, 1, 0, 0],
            "seat": ["front"] * 5,
            "PERALCH_IM": [0, 0, 1, 0, 0],
        },
        schema_overrides={"helmet": pl.Int8},
    )
    # Veh 3 (parked) is absent from the in-transport vehicle file.
    veh = pl.DataFrame(
        {
            "YEAR": [2020, 2020, 2020],
            "CASENUM": [1, 1, 2],
            "VEH_NO": [1, 2, 1],
            "body": ["car", "suv", "car"],
            "veh_age_band": ["0-4"] * 3,
            "veh_speeding": [0, 1, 0],
            "veh_speeding_type": ["no", "exceeded_limit_or_racing", "no"],
            "veh_alcohol": [0, 1, None],
            "veh_alcohol_im": [0, 1, 0],
            "hit_and_run": [0, 0, 0],
            "distracted": [0, 0, 0],
            "speed_limit_mph": [35, 35, 55],
        }
    )
    cols = {c: [None] * 2 for c in dv.CRSS_CRASH_COLS if c not in ("YEAR", "case_id")}
    crash = pl.DataFrame({"YEAR": [2020, 2020], "case_id": [1, 2], **cols}).with_columns(
        pl.col("n_killed").cast(pl.Int64).fill_null(0)
    )
    crash = crash.with_columns(pl.Series("n_killed", [2, 0]))  # one death outside any vehicle
    return per, veh, crash


@pytest.fixture
def crss_build(monkeypatch):
    per, veh, crash = _crss_inputs()
    monkeypatch.setattr(ft, "vehicle_level", lambda source, years: veh)
    monkeypatch.setattr(ft, "person_level", lambda source, years: per.drop("STR_VEH"))
    monkeypatch.setattr(
        dv,
        "load_table",
        lambda source, table, years=None, columns=None, **_: per.select(
            ["YEAR", "CASENUM", "VEH_NO", "PER_NO", "STR_VEH"]
        ),
    )
    return dv.build_crss_driver([2020], crash)


def test_build_crss_driver_one_row_per_in_transport_vehicle(crss_build):
    out, _ = crss_build
    assert out.select(["YEAR", "case_id", "VEH_NO"]).is_duplicated().sum() == 0
    assert sorted(zip(out["case_id"], out["VEH_NO"], strict=True)) == [(1, 1), (1, 2), (2, 1)]
    assert (out["has_driver_record"] == 1).all()


def test_build_crss_driver_occupants_link_to_same_vehicle_driver(crss_build):
    out, link = crss_build
    drv = out.select(["YEAR", "case_id", "VEH_NO", "drv_PER_NO"])
    occ = link.filter(pl.col("relation") != "non_motorist")
    assert (occ["linked_veh_no"] == occ["VEH_NO"]).all()
    # Every occupant of an in-transport vehicle resolves to a driver row of that vehicle;
    # the parked vehicle's occupant has no driver row and no vehicle row.
    res = occ.join(
        drv.rename({"VEH_NO": "linked_veh_no"}), on=["YEAR", "case_id", "linked_veh_no"], how="left"
    )
    unresolved = res.filter(pl.col("drv_PER_NO").is_null())
    assert unresolved.select(["case_id", "VEH_NO"]).rows() == [(1, 3)]
    resolved = res.filter(pl.col("drv_PER_NO").is_not_null())
    assert resolved.height == 4
    assert link.select(["YEAR", "case_id", "VEH_NO", "PER_NO"]).is_duplicated().sum() == 0


def test_build_crss_driver_occupant_counts_and_deaths(crss_build):
    out, _ = crss_build
    r = {(x["case_id"], x["VEH_NO"]): x for x in out.iter_rows(named=True)}
    assert r[(1, 1)]["n_occupants_veh"] == 2 and r[(1, 1)]["n_passengers_veh"] == 1
    assert r[(1, 1)]["n_killed_veh"] == 0
    assert r[(1, 2)]["n_killed_veh"] == 1 and r[(1, 2)]["n_passengers_killed_veh"] == 0
    # Crash 1 has 2 deaths: one in veh 2, so one occurred outside it; veh 3's occupant is not
    # counted in any in-transport vehicle.
    assert r[(1, 1)]["n_killed_outside_veh"] == 2
    assert r[(1, 2)]["n_killed_outside_veh"] == 1
    assert r[(1, 1)]["drv_age"] == 30 and r[(1, 2)]["drv_age"] == 45


def test_build_crss_driver_own_versus_other_driver_flags(crss_build):
    out, _ = crss_build
    r = {(x["case_id"], x["VEH_NO"]): x for x in out.iter_rows(named=True)}
    # Multi-vehicle crash: veh 1's own driver did not speed, the other driver did.
    assert r[(1, 1)]["own_speeding_type"] == "no"
    assert r[(1, 1)]["other_speeding"] == "yes"
    assert r[(1, 1)]["other_exceeded"] == "yes"
    assert r[(1, 1)]["other_alcohol_im"] == "yes"
    assert r[(1, 1)]["n_other_vehicles"] == 1
    # The speeding driver's "other" flags describe veh 1, not themselves.
    assert r[(1, 2)]["own_speeding_type"] == "exceeded_limit_or_racing"
    assert r[(1, 2)]["other_speeding"] == "no"
    assert r[(1, 2)]["other_alcohol_im"] == "no"
    assert r[(1, 2)]["own_alcohol_police"] == "yes"
    assert r[(1, 2)]["own_drugs_police"] == "yes"
    # Single-vehicle crash: no other driver exists (not "no"); unknown police alcohol stays unknown.
    assert r[(2, 1)]["other_speeding"] == "no_other_vehicle"
    assert r[(2, 1)]["n_other_vehicles"] == 0
    assert r[(2, 1)]["own_alcohol_police"] == "unknown"


def test_build_crss_driver_vehicle_without_driver_keeps_null_fields(monkeypatch):
    per, veh, crash = _crss_inputs()
    no_driver = per.filter(~((pl.col("CASENUM") == 1) & (pl.col("VEH_NO") == 2)))
    monkeypatch.setattr(ft, "vehicle_level", lambda source, years: veh)
    monkeypatch.setattr(ft, "person_level", lambda source, years: no_driver.drop("STR_VEH"))
    monkeypatch.setattr(
        dv, "load_table", lambda *a, **k: no_driver.select([*KV, "PER_NO", "STR_VEH"])
    )
    out, _ = dv.build_crss_driver([2020], crash)
    row = out.filter((pl.col("case_id") == 1) & (pl.col("VEH_NO") == 2)).row(0, named=True)
    assert row["has_driver_record"] == 0 and row["drv_PER_NO"] is None
    assert row["n_occupants_veh"] == 0
    assert row["own_drugs_police"] == "unknown"
    # The vehicle's own vehicle-level flags are still present.
    assert row["own_speeding_type"] == "exceeded_limit_or_racing"


def test_build_fars_driver_links_and_other_driver_flags(monkeypatch):
    kp = ["YEAR", "ST_CASE", "VEH_NO", "PER_NO"]
    per = pl.DataFrame(
        {
            "YEAR": [2020] * 4,
            "ST_CASE": [1, 1, 1, 2],
            "VEH_NO": [1, 1, 2, 1],
            "PER_NO": [1, 2, 1, 1],
            "PER_TYP": [1, 2, 1, 1],
            "killed": [0, 1, 0, 1],
            "kabco": [0, 4, 0, 4],
            "killed_or_serious": [0, 1, 0, 1],
            "age": [30, 8, 45, 60],
            "age_band": ["25-34", "0-14", "45-54", "55-64"],
            "sex": ["male", "female", "male", "female"],
            "restraint": ["belted", "belted", "none", "none"],
            "helmet": pl.Series([None] * 4, dtype=pl.Int8),
            "pr_alcohol": [0, 0, 1, 0],
            "pr_drugs": [0, 0, 1, 0],
            "seat": ["front"] * 4,
        }
    )
    veh = pl.DataFrame(
        {
            "YEAR": [2020] * 3,
            "ST_CASE": [1, 1, 2],
            "VEH_NO": [1, 2, 1],
            "body": ["car", "suv", "car"],
            "veh_age_band": ["0-4"] * 3,
            "veh_speeding": [0, 1, 0],
            "veh_speeding_type": ["no", "exceeded_limit_or_racing", "no"],
            "veh_alcohol": [0, 1, 0],
            "hit_and_run": [0] * 3,
            "speed_limit_mph": [35, 35, 55],
            "DEATHS": [1, 0, 1],
            "L_STATUS": [1, 1, 1],
            "PREV_DWI": [0, 3, 99],
            "PREV_SPD": [1, 98, 0],
        }
    )
    extra = per.select(kp).with_columns(
        pl.Series("ALC_RES", [0, 0, 120, 996]), pl.Series("DSTATUS", [1, 1, 1, 1])
    )
    drugs = per.select(kp).with_columns(
        pl.lit("tested").alias("drug_test_status"),
        pl.lit(0, dtype=pl.Int8).alias("drug_any"),
        *[pl.lit(0, dtype=pl.Int8).alias(f"drug_{c}") for c in dv.DRUG_CLASSES],
        pl.lit(0, dtype=pl.Int8).alias("drug_presumptive_only"),
        pl.lit(0, dtype=pl.Int8).alias("drug_carboxy_thc_only"),
    )
    p08 = [0.0, 0.0, 1.0, 0.0]
    bac = per.select(kp).with_columns(
        pl.Series("p_p08", p08),
        pl.Series("p_p01", p08),
        *[pl.Series(f"p_P{i}", [0, 0, 12, 0]) for i in range(1, 11)],
    )
    crash = pl.DataFrame(
        {
            "YEAR": [2020, 2020],
            "case_id": [1, 2],
            **{c: [None, None] for c in dv.FARS_CRASH_COLS if c not in ("YEAR", "case_id")},
        }
    ).with_columns(pl.Series("n_killed", [2, 1]))
    monkeypatch.setattr(ft, "vehicle_level", lambda source, years: veh)
    monkeypatch.setattr(ft, "person_level", lambda source, years: per)
    monkeypatch.setattr(dv, "load_table", lambda *a, **k: extra)
    monkeypatch.setattr(dv, "fars_drug_results", lambda years: drugs)
    monkeypatch.setattr(ft, "mi_bac", lambda *a, **k: bac)

    out = dv.build_fars_driver([2020], crash)
    assert out.select(["YEAR", "case_id", "VEH_NO"]).is_duplicated().sum() == 0
    r = {(x["case_id"], x["VEH_NO"]): x for x in out.iter_rows(named=True)}
    assert set(r) == {(1, 1), (1, 2), (2, 1)}
    # Passenger death counts for the vehicle, the driver's own fields are the driver's.
    assert r[(1, 1)]["n_killed_veh"] == 1 and r[(1, 1)]["n_passengers_killed_veh"] == 1
    assert r[(1, 1)]["drv_killed"] == 0 and r[(1, 1)]["drv_PER_NO"] == 1
    assert r[(1, 1)]["n_killed_outside_veh"] == 1
    # Own versus other driver.
    assert r[(1, 1)]["other_speeding"] == "yes" and r[(1, 1)]["other_bac08"] == "yes"
    assert r[(1, 2)]["other_speeding"] == "no" and r[(1, 2)]["other_bac08"] == "no"
    assert r[(2, 1)]["other_speeding"] == "no_other_vehicle"
    assert r[(1, 2)]["drv_alc_test_status"] == "tested_result"
    assert r[(1, 2)]["drv_bac08_measured"] == 1 and r[(1, 1)]["drv_bac08_measured"] == 0
    assert r[(2, 1)]["drv_alc_test_status"] == "not_tested"
    # Convictions: 0-97 kept, 98 / 99 are not counts.
    assert r[(1, 1)]["prior_dwi_convictions"] == 0 and r[(1, 2)]["prior_dwi_convictions"] == 3
    assert r[(1, 2)]["prior_speeding_convictions"] is None
    assert r[(2, 1)]["prior_dwi_convictions"] is None
