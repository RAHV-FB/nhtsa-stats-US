"""Occupant vs non-occupant structure of the person table (FARS, CRSS).

* PER_TYP x (VEH_NO == 0) per year
* consistency of 'not an occupant' codes (SEAT_POS 0, REST_USE 96, AIR_BAG 97, REST_MIS 8, LOCATION 0,
  EJECTION 8, HELM_USE 96) with VEH_NO == 0
* join of occupant rows to vehicle (in-transport) and parkwork; STR_VEH of non-motorists -> vehicle
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

src = sys.argv[1]
K = ["ST_CASE"] if src == "FARS" else ["CASENUM"]
cols = K + ["VEH_NO", "PER_NO", "PER_TYP", "SEAT_POS", "REST_USE", "AIR_BAG", "REST_MIS", "LOCATION",
            "EJECTION", "HELM_USE", "STR_VEH", "INJ_SEV"]
p = load_table(src, "person", columns=cols)
p = p.with_columns((pl.col("VEH_NO") == 0).alias("veh0"))

with pl.Config(tbl_rows=200, tbl_cols=30, tbl_width_chars=250):
    print(f"\n### {src}: PER_TYP x VEH_NO==0 (pooled 2016-2024)")
    print(p.group_by(["PER_TYP", "veh0"]).len().pivot(on="veh0", index="PER_TYP", values="len").sort("PER_TYP"))
    print("PER_TYP 3 by year, VEH_NO==0 share:")
    print(p.filter(pl.col("PER_TYP") == 3).group_by("YEAR").agg(pl.len(), pl.col("veh0").mean()).sort("YEAR"))

    # consistency of non-occupant codes
    chk = p.group_by(["YEAR"]).agg(
        pl.len().alias("n"),
        pl.col("veh0").sum().alias("n_veh0"),
        ((pl.col("SEAT_POS") == 0) != pl.col("veh0")).sum().alias("seat0_mismatch"),
        ((pl.col("REST_USE") == 96) != pl.col("veh0")).sum().alias("rest96_mismatch"),
        ((pl.col("AIR_BAG") == 97) != pl.col("veh0")).sum().alias("ab97_mismatch"),
        ((pl.col("REST_MIS") == 8) != pl.col("veh0")).sum().alias("rmis8_mismatch"),
        ((pl.col("LOCATION") == 0) != (pl.col("veh0").not_())).sum().alias("loc0_mismatch"),
        ((pl.col("HELM_USE") == 96) != pl.col("veh0")).filter(pl.col("HELM_USE").is_not_null()).sum().alias("helm96_mismatch"),
        (pl.col("veh0") & (pl.col("EJECTION") != 8)).sum().alias("nonocc_eject_not8"),
        ((~pl.col("veh0")) & (pl.col("EJECTION") == 8)).sum().alias("occ_eject_8"),
        (pl.col("veh0") & (pl.col("STR_VEH") == 0)).sum().alias("nonocc_strveh0"),
        ((~pl.col("veh0")) & (pl.col("STR_VEH") != 0)).sum().alias("occ_strveh_nonzero"),
    ).sort("YEAR")
    print(f"\n### {src}: non-occupant code consistency")
    print(chk)

    # where PER_TYP 3 (parked vehicle occupants) sit
    print("PER_TYP=3 SEAT_POS/REST_USE codes (pooled):")
    print(p.filter(pl.col("PER_TYP") == 3).group_by(["veh0", "SEAT_POS"]).len().sort("len", descending=True).head(8))
    print(p.filter(pl.col("PER_TYP") == 3).group_by(["REST_USE"]).len().sort("len", descending=True).head(8))
    print("occupant EJECTION=8 by PER_TYP (pooled):")
    print(p.filter((~pl.col("veh0")) & (pl.col("EJECTION") == 8)).group_by("PER_TYP").len())

    # joins
    v = load_table(src, "vehicle", columns=K + ["VEH_NO"]).with_columns(pl.lit(1).alias("in_veh"))
    pw = load_table(src, "parkwork", columns=K + ["VEH_NO"]).with_columns(pl.lit(1).alias("in_pw"))
    occ = p.filter(~pl.col("veh0"))
    j = occ.join(v, on=["YEAR"] + K + ["VEH_NO"], how="left").join(pw, on=["YEAR"] + K + ["VEH_NO"], how="left")
    print(f"\n### {src}: occupant rows (VEH_NO>0) matched to vehicle / parkwork")
    print(j.group_by(["YEAR", "PER_TYP"]).agg(pl.len(), pl.col("in_veh").is_not_null().mean().alias("in_vehicle"),
                                              pl.col("in_pw").is_not_null().mean().alias("in_parkwork"))
          .filter(pl.col("len") > 0).sort(["PER_TYP", "YEAR"]).group_by("PER_TYP").agg(
              pl.col("len").sum(), pl.col("in_vehicle").min().alias("min_in_vehicle"), pl.col("in_vehicle").max().alias("max_in_vehicle"),
              pl.col("in_parkwork").min().alias("min_in_pw"), pl.col("in_parkwork").max().alias("max_in_pw")).sort("PER_TYP"))
    # non-motorist STR_VEH -> vehicle
    nm = p.filter(pl.col("veh0")).rename({"VEH_NO": "VEH0"}).with_columns(pl.col("STR_VEH").alias("VEH_NO"))
    jn = nm.join(v, on=["YEAR"] + K + ["VEH_NO"], how="left")
    print(f"### {src}: non-motorist STR_VEH -> in-transport vehicle match rate by year")
    print(jn.group_by("YEAR").agg(pl.len(), pl.col("in_veh").is_not_null().mean().alias("strveh_matches_vehicle"),
                                  (pl.col("STR_VEH") == 0).sum().alias("strveh0")).sort("YEAR"))
    # vehicles without any person row
    pv = occ.select(["YEAR"] + K + ["VEH_NO"]).unique()
    jv = v.join(pv.with_columns(pl.lit(1).alias("has_p")), on=["YEAR"] + K + ["VEH_NO"], how="left")
    print(f"### {src}: in-transport vehicles with >=1 person row")
    print(jv.group_by("YEAR").agg(pl.len(), pl.col("has_p").is_not_null().mean()).sort("YEAR"))
