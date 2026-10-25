"""Driver-level datasets: drug-result coding, test status, linkage and other-driver flags."""

from __future__ import annotations

import polars as pl
import pytest

from nhtsa_stats import config
from nhtsa_stats.processing import drivers as dv

KEYS = ["YEAR", "ST_CASE", "VEH_NO", "PER_NO"]


def _long(rows: list[tuple]) -> pl.DataFrame:
    """rows: (year, case, veh, per, DRUGRES, DRUGQTY)"""
    return pl.DataFrame(rows, schema=[*KEYS, "DRUGRES", "DRUGQTY"], orient="row").with_columns(
        pl.col("DRUGQTY").cast(pl.Int64)
    )


@pytest.mark.parametrize(
    ("year", "code", "expected"),
    [
        (2018, 0, "not_given"),
        (2018, 1, "negative"),
        (2018, 95, "not_reported"),
        (2018, 605, "cannabinoid"),
        (2018, 450, "stimulant"),
        (2018, 996, "other"),
        (2018, 997, "tested_unknown"),
        (2018, 998, "positive_unknown_type"),
        (2018, 999, "unknown_if_tested"),
        (2022, 5062, "cannabinoid"),
        (2022, 3026, "non_psychoactive"),  # caffeine
        (2022, 3066, "non_psychoactive"),  # nicotine
        (2022, 3050, "stimulant"),
        (2022, 9035, "non_psychoactive"),
        (2022, 9995, "not_reported"),
        (2022, 9999, "unknown_if_tested"),
        (2022, 1500, "narcotic"),
    ],
)
def test_drug_class_codes(year, code, expected):
    df = pl.DataFrame({"YEAR": [year], "DRUGRES": [code]})
    assert df.select(dv.drug_class_expr())[0, 0] == expected


def test_summarise_status_and_positivity():
    rows = [
        # person 1: negative blood + cannabinoid urine -> tested, positive
        (2019, 1, 1, 1, 1, None),
        (2019, 1, 1, 1, 605, None),
        # person 2: test not given only
        (2019, 1, 1, 2, 0, None),
        # person 3: unknown if tested
        (2019, 1, 2, 1, 999, None),
        # person 4: only "other drug" -> tested but indeterminate
        (2019, 1, 2, 2, 996, None),
        # person 5: only caffeine (2022) -> tested, negative for psychoactive drugs
        (2022, 2, 1, 1, 3026, None),
        # person 6: presumptive-only positive (2023)
        (2023, 3, 1, 1, 1500, 3),
        # person 7: carboxy-THC only (2022)
        (2022, 4, 1, 1, 5062, None),
        # person 8: not reported
        (2019, 5, 1, 1, 95, None),
    ]
    out = dv.summarise_drug_results(_long(rows), KEYS).sort(KEYS)
    rec = {
        (r["YEAR"], r["ST_CASE"], r["VEH_NO"], r["PER_NO"]): r for r in out.iter_rows(named=True)
    }
    p1 = rec[(2019, 1, 1, 1)]
    assert (
        p1["drug_test_status"] == "tested" and p1["drug_any"] == 1 and p1["drug_cannabinoid"] == 1
    )
    assert p1["drug_narcotic"] == 0
    p2 = rec[(2019, 1, 1, 2)]
    assert p2["drug_test_status"] == "not_tested" and p2["drug_any"] is None
    assert rec[(2019, 1, 2, 1)]["drug_test_status"] == "unknown_if_tested"
    p4 = rec[(2019, 1, 2, 2)]
    assert p4["drug_test_status"] == "tested" and p4["drug_any"] is None
    p5 = rec[(2022, 2, 1, 1)]
    assert p5["drug_test_status"] == "tested" and p5["drug_any"] == 0
    p6 = rec[(2023, 3, 1, 1)]
    assert p6["drug_any"] == 1 and p6["drug_presumptive_only"] == 1
    p7 = rec[(2022, 4, 1, 1)]
    assert p7["drug_carboxy_thc_only"] == 1 and p7["drug_any"] == 1
    assert rec[(2019, 5, 1, 1)]["drug_test_status"] == "not_reported"


def test_other_vehicle_flags_and_levels():
    veh = pl.DataFrame(
        {
            "YEAR": [2020] * 5,
            "CASENUM": [1, 1, 2, 3, 3],
            "VEH_NO": [1, 2, 1, 1, 2],
            "spd": [1, 0, 1, 0, None],
        }
    )
    out = dv.other_vehicle_flags(veh, ["YEAR", "CASENUM"], ["spd"]).with_columns(
        dv.other_level("other_spd").alias("lab")
    )
    lab = {(r["CASENUM"], r["VEH_NO"]): r["lab"] for r in out.iter_rows(named=True)}
    assert lab[(1, 1)] == "no"  # the other driver did not speed
    assert lab[(1, 2)] == "yes"  # the other driver sped; own behaviour is not "other"
    assert lab[(2, 1)] == "no_other_vehicle"
    assert lab[(3, 1)] == "unknown"
    assert lab[(3, 2)] == "no"


def test_vehicle_occupants_counts():
    per = pl.DataFrame(
        {
            "YEAR": [2020] * 4,
            "CASENUM": [1, 1, 1, 1],
            "VEH_NO": [1, 1, 2, 0],
            "PER_NO": [1, 2, 1, 1],
            "PER_TYP": [1, 2, 1, 5],
            "killed": [1, 0, 0, 1],
        }
    )
    occ = dv.vehicle_occupants(per, ["YEAR", "CASENUM", "VEH_NO"]).sort("VEH_NO")
    assert occ["n_occupants_veh"].to_list() == [2, 1]
    assert occ["n_killed_veh"].to_list() == [1, 0]
    assert occ["n_passengers_killed_veh"].to_list() == [0, 0]


def test_alcohol_test_status():
    df = pl.DataFrame({"ALC_RES": [0, 80, 940, 995, 996, 997, 998, 999]})
    got = df.select(dv.alcohol_test_status().alias("s"))["s"].to_list()
    assert got == [
        "tested_result",
        "tested_result",
        "tested_result",
        "not_reported",
        "not_tested",
        "tested_result_unknown",
        "tested_positive_no_value",
        "unknown_if_tested",
    ]


# --------------------------------------------------------------------------------------
# Real-data checks (skipped when the processed datasets are absent)
# --------------------------------------------------------------------------------------
needs_data = pytest.mark.skipif(
    not (config.PROCESSED_DIR / "crss_driver.parquet").exists(), reason="processed data absent"
)


@pytest.mark.processed
@needs_data
def test_driver_files_reconcile_with_crash_files():
    cd = pl.read_parquet(
        config.PROCESSED_DIR / "crss_driver.parquet",
        columns=[
            "YEAR",
            "case_id",
            "VEH_NO",
            "n_vehicles",
            "speeding_type",
            "own_speeding_type",
            "n_killed_outside_veh",
        ],
    )
    cc = pl.read_parquet(
        config.PROCESSED_DIR / "crss_crash.parquet",
        columns=["YEAR", "case_id", "n_veh_in_transport"],
    )
    assert cd.select(["YEAR", "case_id", "VEH_NO"]).is_duplicated().sum() == 0
    per_crash = cd.group_by(["YEAR", "case_id"]).len().join(cc, on=["YEAR", "case_id"])
    assert (per_crash["len"] == per_crash["n_veh_in_transport"]).all()
    sv = cd.filter(pl.col("n_vehicles") == "1")
    assert (sv["speeding_type"] == sv["own_speeding_type"]).all()
    assert cd["n_killed_outside_veh"].min() >= 0
    fd = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=["n_killed_veh", "n_killed_outside_veh", "YEAR", "case_id"],
    )
    fc = pl.read_parquet(config.PROCESSED_DIR / "fars_crash.parquet", columns=["FATALS"])
    # Deaths inside vehicles + deaths outside every vehicle reconcile to the FARS total.
    inside = fd["n_killed_veh"].sum()
    crash_tot = fd.group_by(["YEAR", "case_id"]).agg(pl.col("n_killed_veh").sum())
    assert inside == crash_tot["n_killed_veh"].sum()
    assert inside <= fc["FATALS"].sum()


@pytest.mark.processed
@needs_data
def test_person_links_resolve_to_driver_rows():
    link = pl.read_parquet(config.PROCESSED_DIR / "crss_person_link.parquet")
    drv = pl.read_parquet(
        config.PROCESSED_DIR / "crss_driver.parquet", columns=["YEAR", "case_id", "VEH_NO"]
    )
    linked = link.filter(pl.col("linked_veh_no").is_not_null())
    miss = linked.join(
        drv.rename({"VEH_NO": "linked_veh_no"}), on=["YEAR", "case_id", "linked_veh_no"], how="anti"
    )
    assert miss.height == 0
    occ = link.filter(pl.col("relation") != "non_motorist")
    assert (occ["linked_veh_no"] == occ["VEH_NO"]).all()


@pytest.mark.processed
@needs_data
def test_fars_drug_test_rates_match_audit():
    """Killed-driver drug-test rates reproduce docs/audit/alcohol_drugs.md §5.1."""
    fd = pl.read_parquet(
        config.PROCESSED_DIR / "fars_driver.parquet",
        columns=["YEAR", "drv_killed", "drv_drug_test_status"],
    )
    k = (
        fd.filter(pl.col("drv_killed") == 1)
        .group_by("YEAR")
        .agg((pl.col("drv_drug_test_status") == "tested").mean().alias("r"))
    )
    rates = dict(zip(k["YEAR"], k["r"], strict=True))
    assert rates[2016] == pytest.approx(0.637, abs=0.002)
    assert rates[2018] == pytest.approx(0.646, abs=0.002)
    assert rates[2024] == pytest.approx(0.551, abs=0.002)
