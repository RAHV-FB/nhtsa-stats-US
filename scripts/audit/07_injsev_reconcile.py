"""INJ_SEV reconciliation.

FARS: count(INJ_SEV==4) per crash vs accident.FATALS; per vehicle vs vehicle.DEATHS; INJ_SEV vs
      DOA / DEATH_* / LAG_HRS / HOSPITAL; INJ_SEV==6 rows.
CRSS: MAX_SEV vs max(person INJ_SEV); NUM_INJ vs count(INJ_SEV in 1..5); INJSEV_IM vs INJ_SEV.
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(80)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
src = sys.argv[1]

if src == "FARS":
    p = load_table("FARS", "person", columns=["ST_CASE", "VEH_NO", "PER_NO", "PER_TYP", "INJ_SEV", "DOA", "DEATH_DA", "DEATH_MO", "DEATH_YR",
                                              "DEATH_HR", "DEATH_MN", "DEATH_TM", "LAG_HRS", "LAG_MINS", "HOSPITAL", "WORK_INJ", "HISPANIC"])
    a = load_table("FARS", "accident", columns=["ST_CASE", "FATALS", "PERSONS", "PERMVIT", "PERNOTMVIT"])
    k = p.group_by(["YEAR", "ST_CASE"]).agg((pl.col("INJ_SEV") == 4).sum().alias("n_k"), pl.len().alias("n_p"),
                                            (pl.col("VEH_NO") == 0).sum().alias("n_nm"))
    j = a.join(k, on=["YEAR", "ST_CASE"], how="full", coalesce=True)
    print("### FARS crash reconciliation: sum(INJ_SEV==4) vs FATALS")
    print(j.group_by("YEAR").agg(pl.len().alias("crashes"), pl.col("FATALS").sum().alias("sum_FATALS"), pl.col("n_k").sum().alias("sum_K"),
                                 (pl.col("FATALS") != pl.col("n_k")).sum().alias("crashes_mismatch"),
                                 pl.col("n_k").is_null().sum().alias("acc_without_person"), pl.col("FATALS").is_null().sum().alias("person_without_acc"),
                                 (pl.col("n_k") == 0).sum().alias("crashes_with_0_K"),
                                 (pl.col("PERNOTMVIT") != pl.col("n_nm")).sum().alias("pernotmvit_mismatch")).sort("YEAR"))
    mm = j.filter(pl.col("FATALS") != pl.col("n_k"))
    if mm.height:
        print(mm.head(20))
        # describe mismatching persons
        pm = p.join(mm.select(["YEAR", "ST_CASE"]), on=["YEAR", "ST_CASE"])
        print(pm.group_by(["YEAR", "INJ_SEV"]).len().sort(["YEAR", "INJ_SEV"]))
    # vehicle DEATHS
    v = load_table("FARS", "vehicle", columns=["ST_CASE", "VEH_NO", "DEATHS", "NUMOCCS"])
    kv = p.filter(pl.col("VEH_NO") > 0).group_by(["YEAR", "ST_CASE", "VEH_NO"]).agg((pl.col("INJ_SEV") == 4).sum().alias("n_k"),
                                                                                    pl.len().alias("n_occ_rows"))
    jv = v.join(kv, on=["YEAR", "ST_CASE", "VEH_NO"], how="left").with_columns(pl.col("n_k").fill_null(0), pl.col("n_occ_rows").fill_null(0))
    print("### FARS vehicle reconciliation: DEATHS vs occupants with INJ_SEV==4; NUMOCCS vs occupant rows")
    print(jv.group_by("YEAR").agg(pl.len(), (pl.col("DEATHS") != pl.col("n_k")).sum().alias("deaths_mismatch"),
                                  (pl.col("NUMOCCS") == pl.col("n_occ_rows")).mean().alias("numoccs_eq_rows"),
                                  pl.col("NUMOCCS").is_in([97, 98, 99]).sum().alias("numoccs_97_99"),
                                  ((pl.col("NUMOCCS") < 90) & (pl.col("NUMOCCS") != pl.col("n_occ_rows"))).sum().alias("numoccs_known_ne_rows")).sort("YEAR"))
    print("NUMOCCS codes >= 90 (pooled):", jv.filter(pl.col("NUMOCCS") >= 90).group_by("NUMOCCS").len().sort("NUMOCCS").to_dicts())
    # INJ_SEV vs death fields
    p = p.with_columns((pl.col("INJ_SEV") == 4).alias("K"))
    print("### FARS: DOA x INJ_SEV (pooled)")
    print(p.group_by(["INJ_SEV", "DOA"]).len().pivot(on="DOA", index="INJ_SEV", values="len").sort("INJ_SEV"))
    print("### FARS: DEATH_YR class x INJ_SEV (pooled)")
    dy = pl.when(pl.col("DEATH_YR") == 8888).then(pl.lit("8888 NA")).when(pl.col("DEATH_YR") == 9999).then(pl.lit("9999 unk")).when(
        pl.col("DEATH_YR") == 9997).then(pl.lit("9997 redacted")).when(pl.col("DEATH_YR") == pl.col("YEAR")).then(pl.lit("same yr")).when(
        pl.col("DEATH_YR") == pl.col("YEAR") + 1).then(pl.lit("next yr")).otherwise(pl.lit("other"))
    print(p.with_columns(dy.alias("dy")).group_by(["INJ_SEV", "dy"]).len().pivot(on="dy", index="INJ_SEV", values="len").sort("INJ_SEV"))
    print("### FARS: LAG_HRS among K: distribution / special codes by year")
    kk = p.filter(pl.col("K"))
    print(kk.group_by("YEAR").agg(pl.len(), (pl.col("LAG_HRS") == 999).sum().alias("lag999"), (pl.col("LAG_HRS") == 99).sum().alias("lag99"),
                                  (pl.col("LAG_HRS") == 0).mean().alias("p_lag0"), (pl.col("LAG_HRS") <= 720).mean().alias("p_le720"),
                                  pl.col("LAG_HRS").filter(pl.col("LAG_HRS") < 999).max().alias("max_lag<999"),
                                  (pl.col("LAG_HRS") > 720).filter(pl.col("LAG_HRS") < 997).sum().alias("lag_gt720"),
                                  (pl.col("LAG_HRS") >= 997).sum().alias("lag_ge997"),
                                  (pl.col("DEATH_YR") == 9997).sum().alias("redacted")).sort("YEAR"))
    print("non-K LAG_HRS values:", p.filter(~pl.col("K")).group_by("LAG_HRS").len().sort("len", descending=True).head(5).to_dicts())
    print("K LAG_HRS top values:", kk.group_by("LAG_HRS").len().sort("len", descending=True).head(8).to_dicts())
    print("### FARS: HOSPITAL x INJ_SEV (pooled)")
    print(p.group_by(["INJ_SEV", "HOSPITAL"]).len().pivot(on="HOSPITAL", index="INJ_SEV", values="len", sort_columns=True).sort("INJ_SEV"))
    print("### FARS: INJ_SEV==6 rows by year and PER_TYP")
    print(p.filter(pl.col("INJ_SEV") == 6).group_by(["YEAR"]).len().sort("YEAR").to_dicts())
    print("### FARS: HISPANIC==0 ('not a fatality') vs INJ_SEV")
    print(p.group_by([(pl.col("HISPANIC") == 0).alias("hisp0"), "INJ_SEV"]).len().pivot(on="hisp0", index="INJ_SEV", values="len").sort("INJ_SEV"))
    print(p.group_by([(pl.col("WORK_INJ") == 8).alias("work8"), "INJ_SEV"]).len().pivot(on="work8", index="INJ_SEV", values="len").sort("INJ_SEV"))
else:
    p = load_table("CRSS", "person", columns=["CASENUM", "VEH_NO", "PER_TYP", "INJ_SEV", "INJSEV_IM", "HOSPITAL", "WEIGHT"])
    a = load_table("CRSS", "accident", columns=["CASENUM", "MAX_SEV", "MAXSEV_IM", "NUM_INJ", "NO_INJ_IM", "WEIGHT"])
    rank = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 0.5}  # 5 injured unknown sits between O and C for 'max'
    agg = p.group_by(["YEAR", "CASENUM"]).agg(
        pl.col("INJ_SEV").filter(pl.col("INJ_SEV").is_in([0, 1, 2, 3, 4])).max().alias("max_known"),
        pl.col("INJ_SEV").is_in([5]).any().alias("any5"), pl.col("INJ_SEV").is_in([9]).any().alias("any9"),
        pl.col("INJ_SEV").is_in([1, 2, 3, 5]).sum().alias("n_inj"), pl.col("INJ_SEV").eq(4).sum().alias("n_k"),
        pl.col("INJSEV_IM").max().alias("max_im"), pl.len().alias("n_p"))
    j = a.join(agg, on=["YEAR", "CASENUM"], how="left")
    print("### CRSS: MAX_SEV vs max known person INJ_SEV (0-4)")
    print(j.group_by(["MAX_SEV"]).agg(pl.len(), (pl.col("MAX_SEV") == pl.col("max_known")).mean().alias("eq_max_known"),
                                      pl.col("any9").mean().alias("any9"), pl.col("any5").mean().alias("any5"),
                                      pl.col("n_p").is_null().sum().alias("no_person")).sort("MAX_SEV"))
    print(j.filter(pl.col("MAX_SEV").is_in([0, 1, 2, 3, 4]) & (pl.col("MAX_SEV") != pl.col("max_known"))).group_by(["YEAR"]).len().sort("YEAR"))
    print("### CRSS: NUM_INJ vs count(INJ_SEV in 1,2,3,5) (non-fatal injured)")
    print(j.group_by("YEAR").agg(pl.len(), (pl.col("NUM_INJ") == pl.col("n_inj")).mean().alias("eq_n_inj_1235"),
                                 (pl.col("NUM_INJ") == pl.col("n_inj") + pl.col("n_k")).mean().alias("eq_incl_K"),
                                 (pl.col("NUM_INJ") >= 98).sum().alias("num_inj_ge98")).sort("YEAR"))
    print("NUM_INJ special values:", j.filter(pl.col("NUM_INJ") >= 90).group_by("NUM_INJ").len().to_dicts())
    print("### CRSS: INJSEV_IM vs INJ_SEV (pooled, unweighted counts)")
    print(p.group_by(["INJ_SEV", "INJSEV_IM"]).len().pivot(on="INJSEV_IM", index="INJ_SEV", values="len", sort_columns=True).sort("INJ_SEV"))
    print("### CRSS: HOSPITAL x INJ_SEV (pooled, unweighted)")
    print(p.group_by(["INJ_SEV", "HOSPITAL"]).len().pivot(on="HOSPITAL", index="INJ_SEV", values="len", sort_columns=True).sort("INJ_SEV"))
    print("### CRSS: MAX_SEV vs MAXSEV_IM")
    print(a.group_by(["MAX_SEV", "MAXSEV_IM"]).len().pivot(on="MAXSEV_IM", index="MAX_SEV", values="len", sort_columns=True).sort("MAX_SEV"))
