"""Build a vehicle/driver-level audit frame per source (scratch output, not a project dataset).

One row per in-transport vehicle (vehicle table). Adds: driver person row (PER_TYP==1), crash-level severity,
and per-vehicle pivots of the multi-row factor tables (n rows, presence of none/substantive/unknown/not-reported/
no-driver codes, plus specific indicator flags). Writes OUT/frame_{SRC}.parquet.
"""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT, lt

# code classes per multi-row table: value -> class.  'S' = substantive (anything not listed).
CLASSES = {
    "distract": {0: "none", 16: "nodrv", 96: "nr", 99: "unk"},
    "drimpair": {0: "none", 95: "nodrv", 98: "nr", 99: "unk"},
    "factor": {0: "none", 98: "nr", 99: "unk"},
    "maneuver": {0: "none", 95: "nodrv", 98: "nr", 99: "unk"},
    "violatn": {0: "none", 95: "nodrv", 97: "nr", 99: "unk"},
    "vision": {0: "none", 95: "nodrv", 99: "unk"},
    "driverrf": {0: "none", 999: "unk"},
}
COL = {
    "distract": ["MDRDSTRD", "DRDISTRACT"], "drimpair": ["DRIMPAIR"], "factor": ["MFACTOR", "VEHICLECC"],
    "maneuver": ["MDRMANAV", "MANEUVER"], "violatn": ["MVIOLATN", "VIOLATION"], "vision": ["MVISOBSC", "VISION"],
    "driverrf": ["DRIVERRF"],
}
# specific substantive flags: name -> (table, codes)
SPEC_FLAGS = {
    "dis_any_subst_excl1": ("distract", [3, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15, 17, 18, 19, 92, 93, 97, 98]),
    "dis_lookedbutdidnotsee": ("distract", [1]),
    "dis_phone": ("distract", [5, 6, 15]),
    "imp_asleep": ("drimpair", [2]),
    "imp_ill": ("drimpair", [1]),
    "imp_emotional": ("drimpair", [8]),
    "imp_influence": ("drimpair", [9]),
    "imp_physical": ("drimpair", [3, 4, 5, 6, 7, 10, 96]),
    "vio_speed": ("violatn", [21, 22, 23, 24, 25, 26, 29]),
    "vio_dwi": ("violatn", [11, 12, 13, 14, 16, 18, 19]),
    "vio_license": ("violatn", [71, 72, 73]),
    "vio_hitrun": ("violatn", [7, 8]),
    "vio_homicide": ("violatn", [1, 9]),
    "vio_reckless_careless": ("violatn", [2, 3, 4, 5, 6, 10]),
    # moving violations relevant to crash causation (rules of the road)
    "vio_moving_rules": ("violatn", [31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42, 43, 45, 46, 48, 49, 51, 52, 53,
                                     54, 55, 56, 58, 59, 61, 62, 63, 66, 69, 93, 98]),
    "vis_obscured": ("vision", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 97, 98]),
    "man_avoid": ("maneuver", [1, 2, 3, 4, 5, 92]),
    "fac_any": ("factor", list(range(1, 18)) + [97]),
}


def pivot(src: str, table: str, years=None) -> pl.DataFrame:
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    cols = COL[table]
    df = lt(src, table, k + ["VEH_NO"] + cols, years)
    if src == "FARS" and table in ("distract", "drimpair"):
        pass
    df = df.unique()  # defensive: exact duplicate rows
    code = pl.coalesce([pl.col(c) for c in cols]).alias("code")
    df = df.select(k + ["VEH_NO", code])
    cls = CLASSES[table]
    df = df.with_columns(
        pl.col("code").replace_strict(cls, default="S", return_dtype=pl.Utf8).alias("cls"))
    p = table[:3] if table != "driverrf" else "drf"
    p = {"distract": "dis", "drimpair": "imp", "factor": "fac", "maneuver": "man", "violatn": "vio",
         "vision": "vis", "driverrf": "drt"}[table]
    aggs = [pl.len().alias(f"{p}_nrows")]
    for c in ["none", "S", "unk", "nr", "nodrv"]:
        aggs.append((pl.col("cls") == c).any().alias(f"{p}_has_{c}"))
    aggs.append(pl.col("code").min().alias(f"{p}_mincode"))
    for name, (t, codes) in SPEC_FLAGS.items():
        if t == table:
            aggs.append(pl.col("code").is_in(codes).any().alias(name))
    return df.group_by(k + ["VEH_NO"]).agg(aggs)


def driverrf_flags(src):
    """driver-related factors: 2016-19 DR_SF1-4 (vehicle), 2020+ driverrf table; returned as long codes."""
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    v = lt(src, "vehicle", k + ["VEH_NO", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"], years=[2016, 2017, 2018, 2019])
    long = v.unpivot(index=k + ["VEH_NO"], on=["DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"],
                     variable_name="slot", value_name="code").drop("slot")
    # DR_SF unknown code is 99; empty slots carry 0 (None) -> keep all, then classify
    long = long.with_columns(pl.col("code").cast(pl.Int64))
    d = lt(src, "driverrf", k + ["VEH_NO", "DRIVERRF"], years=[2020, 2021, 2022, 2023, 2024]).rename(
        {"DRIVERRF": "code"}).with_columns(pl.col("code").cast(pl.Int64))
    long = pl.concat([long, d.select(long.columns)])
    unk = ((pl.col("YEAR") <= 2019) & (pl.col("code") == 99)) | ((pl.col("YEAR") >= 2020) & (pl.col("code") == 999))
    long = long.with_columns(
        pl.when(pl.col("code") == 0).then(pl.lit("none")).when(unk).then(pl.lit("unk")).otherwise(pl.lit("S"))
        .alias("cls"))
    culp_codes = [6, 8, 10, 26, 27, 28, 29, 30, 31, 33, 34, 35, 36, 38, 39, 40, 41, 42, 45, 47, 48, 50, 51, 58, 102,
                  103]
    aggs = [
        pl.col("code").filter(pl.col("code") != 0).len().alias("drf_n_nonzero"),
        (pl.col("cls") == "S").any().alias("drf_has_S"),
        (pl.col("cls") == "unk").any().alias("drf_has_unk"),
        pl.col("code").is_in(culp_codes).any().alias("drf_culp_codes"),
        pl.col("code").is_in([6]).any().alias("drf_careless"),
        pl.col("code").is_in([38]).any().alias("drf_fty"),
        pl.col("code").is_in([39]).any().alias("drf_disobey"),
        pl.col("code").is_in([10]).any().alias("drf_lbdns"),
        pl.col("code").is_in([8, 102, 103]).any().alias("drf_aggr"),
        pl.col("code").is_in([37, 104]).any().alias("drf_pursued"),
    ]
    return long.group_by(k + ["VEH_NO"]).agg(aggs)


def build(src):
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    vcols = ["VEH_NO", "SPEEDREL", "TRAV_SP", "VSPD_LIM", "DR_PRES", "HIT_RUN", "BODY_TYP", "VE_FORMS"]
    if src == "FARS":
        vcols += ["DEATHS", "L_STATUS", "L_COMPL", "CDL_STAT", "L_TYPE", "L_RESTRI", "L_ENDORS", "PREV_ACC",
                  "PREV_SUS", "PREV_SUS1", "PREV_SUS2", "PREV_SUS3", "PREV_DWI", "PREV_SPD", "PREV_OTH", "DR_HGT",
                  "DR_WGT", "DR_ZIP", "STATE", "DR_DRINK", "FIRST_YR", "LAST_YR"]
    else:
        vcols += ["MAX_VSEV", "WEIGHT", "PSU", "PSUSTRAT", "PSU_VAR", "STRATUM", "DR_ZIP", "REGION", "URBANICITY",
                  "PJ"]
    v = lt(src, "vehicle", k + vcols)
    acols = ["VE_TOTAL", "VE_FORMS", "PEDS"] + (["FATALS", "STATE"] if src == "FARS" else ["MAX_SEV"])
    a = lt(src, "accident", k + [c for c in acols if c not in ("STATE",)] + (["STATE"] if src == "FARS" else []))
    a = a.rename({"VE_FORMS": "ACC_VE_FORMS", "VE_TOTAL": "ACC_VE_TOTAL"})
    if src == "FARS":
        a = a.drop("STATE")
    v = v.join(a, on=k, how="left")
    p = lt(src, "person", k + ["VEH_NO", "PER_NO", "PER_TYP", "INJ_SEV", "AGE"])
    drv = p.filter(pl.col("PER_TYP") == 1)
    ndrv = drv.group_by(k + ["VEH_NO"]).len().filter(pl.col("len") > 1)
    print(src, "vehicles with >1 driver person row:", ndrv.height)
    drv = drv.sort("PER_NO").unique(subset=k + ["VEH_NO"], keep="first").select(
        k + ["VEH_NO", pl.col("INJ_SEV").alias("DRV_INJ_SEV"), pl.col("AGE").alias("DRV_AGE")])
    v = v.join(drv, on=k + ["VEH_NO"], how="left")
    for t in ["distract", "drimpair", "factor", "maneuver", "violatn", "vision"]:
        v = v.join(pivot(src, t), on=k + ["VEH_NO"], how="left")
    v = v.join(pivot(src, "driverrf", years=[2020, 2021, 2022, 2023, 2024]), on=k + ["VEH_NO"], how="left")
    v = v.join(driverrf_flags(src), on=k + ["VEH_NO"], how="left")
    aux = ["A_SPVEH"] + (["A_DRDIS", "A_DRDRO", "A_LIC_S", "A_LIC_C", "A_CDL_S", "A_MC_L_S"] if src == "FARS" else [])
    v = v.join(lt(src, "veh_aux", k + ["VEH_NO"] + aux), on=k + ["VEH_NO"], how="left")
    acx = ["A_SPCRA", "A_DIST"] + (["A_DROWSY"] if src == "FARS" else [])
    v = v.join(lt(src, "acc_aux", k + acx), on=k, how="left")
    v.write_parquet(f"{OUT}/frame_{src}.parquet")
    print(src, v.shape)
    print(v.null_count().transpose(include_header=True).filter(pl.col("column_0") > 0))


if __name__ == "__main__":
    for s in sys.argv[1:] or ["FARS", "CRSS"]:
        build(s)
