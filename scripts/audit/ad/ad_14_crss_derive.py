"""CRSS derivations: VEH_ALCH vs driver DRINKING/BAC; ALCOHOL vs VEH_ALCH & non-motorist DRINKING; IM consistency; 2019 break by month; who is 'Not Reported'."""
import polars as pl
OUT = "/tmp/nhtsa-audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/crss_person.parquet")
drv = df.filter(pl.col("PER_TYP")==1).with_columns(
   pl.when(pl.col("ALC_RES")<=940).then(pl.when(pl.col("ALC_RES")>0).then(pl.lit("pos")).otherwise(pl.lit("zero"))).otherwise(pl.col("ALC_RES").cast(pl.Utf8)).alias("bac"),
   (pl.col("YEAR")<=2018).alias("early"))
print("VEH_ALCH x driver DRINKING (counts), early (2016-18) vs late (2019-24)")
print(drv.group_by(["early","DRINKING","VEH_ALCH"]).len().pivot(on="VEH_ALCH", index=["early","DRINKING"], values="len", sort_columns=True).sort(["early","DRINKING"]))
print("VEH_ALCH x bac among DRINKING in (0,8,9)")
print(drv.filter(pl.col("DRINKING")!=1).group_by(["early","bac","VEH_ALCH"]).len().pivot(on="VEH_ALCH", index=["early","bac"], values="len", sort_columns=True).sort(["early","bac"]))
rule = pl.when((pl.col("DRINKING")==1)|(pl.col("bac")=="pos")).then(1).when(pl.col("DRINKING")==0).then(2).otherwise(9)
r = drv.with_columns(rule.alias("r")).group_by("YEAR").agg((pl.col("r")==pl.col("VEH_ALCH")).mean().round(5).alias("agree_rule"), pl.len()).sort("YEAR")
print("rule VEH_ALCH = 1 if DRINKING=1 or BAC>0, 2 if DRINKING=0, else 9:"); print(r)
# vehicles with no driver person
v = pl.read_parquet(f"{OUT}/crss_vehicle.parquet")
nod = v.join(drv.select(["YEAR","CASENUM","VEH_NO"]), on=["YEAR","CASENUM","VEH_NO"], how="anti")
print("vehicles without driver record:", nod.height, nod["VEH_ALCH"].value_counts().sort("VEH_ALCH").to_dict(as_series=False))
# IM consistency
print("V_ALCH_IM vs VEH_ALCH:")
print(v.group_by(["VEH_ALCH","V_ALCH_IM"]).len().pivot(on="V_ALCH_IM", index="VEH_ALCH", values="len", sort_columns=True).sort("VEH_ALCH"))
print("PERALCH_IM vs DRINKING (all persons):")
print(df.group_by(["DRINKING","PERALCH_IM"]).len().pivot(on="PERALCH_IM", index="DRINKING", values="len", sort_columns=True).sort("DRINKING"))
print("PERALCH_IM vs DRINKING by PER_TYP class (drivers vs others):")
print(df.with_columns(pl.when(pl.col("PER_TYP")==1).then(pl.lit("driver")).when(pl.col("PER_TYP").is_in([2,3,4,9])).then(pl.lit("occupant")).otherwise(pl.lit("nonmotorist")).alias("pt")).group_by(["pt","DRINKING","PERALCH_IM"]).len().pivot(on="PERALCH_IM", index=["pt","DRINKING"], values="len", sort_columns=True).sort(["pt","DRINKING"]))
# PERALCH_IM for driver = V_ALCH_IM?
print("driver PERALCH_IM vs V_ALCH_IM:")
print(drv.group_by(["PERALCH_IM","V_ALCH_IM"]).len().sort(["PERALCH_IM","V_ALCH_IM"]))
# crash-level ALCOHOL vs vehicles & non-motorists
nm = df.filter(pl.col("PER_TYP").is_in([5,6,7,8,10,11,12,13,19]))
c = (v.group_by(["YEAR","CASENUM"]).agg((pl.col("VEH_ALCH")==1).any().alias("anyV1"), (pl.col("VEH_ALCH")==2).all().alias("allV2"),
        (pl.col("VEH_ALCH").is_in([2,8])).all().alias("allV28"), (pl.col("V_ALCH_IM")==1).any().alias("anyVim1"))
      .join(nm.group_by(["YEAR","CASENUM"]).agg((pl.col("DRINKING")==1).any().alias("anyNM1"), (pl.col("DRINKING")==0).all().alias("allNM0"), (pl.col("PERALCH_IM")==1).any().alias("anyNMim1"), pl.len().alias("n_nm")), on=["YEAR","CASENUM"], how="left")
      .join(pl.read_parquet(f"{OUT}/crss_crash.parquet").select(["YEAR","CASENUM","ALCOHOL","ALCHL_IM"]), on=["YEAR","CASENUM"]))
c = c.with_columns(pl.col("anyNM1").fill_null(False), pl.col("allNM0").fill_null(True), pl.col("anyNMim1").fill_null(False))
hyp = pl.when(pl.col("anyV1")|pl.col("anyNM1")).then(1).when(pl.col("allV28")&pl.col("allNM0")).then(2).otherwise(9)
c = c.with_columns(hyp.alias("hyp"))
print("ALCOHOL vs hyp(1 any veh/nonmotorist alcohol; 2 all vehicles no/no-driver and all NM no; 9 else):")
print(c.group_by(["ALCOHOL","hyp"]).len().pivot(on="hyp", index="ALCOHOL", values="len", sort_columns=True).sort("ALCOHOL"))
print("ALCHL_IM vs any V_ALCH_IM=1 or NM PERALCH_IM=1:")
print(c.with_columns((pl.col("anyVim1")|pl.col("anyNMim1")).alias("h")).group_by(["ALCHL_IM","h"]).len().sort(["ALCHL_IM","h"]))
print("ALCHL_IM vs ALCOHOL:")
print(c.group_by(["ALCOHOL","ALCHL_IM"]).len().pivot(on="ALCHL_IM", index="ALCOHOL", values="len", sort_columns=True).sort("ALCOHOL"))
# 2019 break by month
a = pl.read_parquet(f"{OUT}/crss_crash.parquet")
print("ALCOHOL=9 % by month, 2018-2020:")
print(a.filter(pl.col("YEAR").is_between(2018,2020)).group_by(["YEAR","MONTH"]).agg((pl.col("ALCOHOL")==9).mean().mul(100).round(1).alias("p9")).pivot(on="YEAR", index="MONTH", values="p9", sort_columns=True).sort("MONTH"))
print("driver DRINKING=8 % by month 2018-2020:")
print(drv.filter(pl.col("YEAR").is_between(2018,2020)).group_by(["YEAR","MONTH"]).agg((pl.col("DRINKING")==8).mean().mul(100).round(1).alias("p8")).pivot(on="YEAR", index="MONTH", values="p8", sort_columns=True).sort("MONTH"))
# who is 'Not Reported' (8) by PER_TYP and INJ_SEV, early vs late
print("DRINKING=8 % by PER_TYP group and year:")
x = df.with_columns(pl.when(pl.col("PER_TYP")==1).then(pl.lit("driver")).when(pl.col("PER_TYP").is_in([2,3,4,9])).then(pl.lit("occupant")).otherwise(pl.lit("nonmotorist")).alias("pt"))
print(x.group_by(["YEAR","pt"]).agg((pl.col("DRINKING")==8).mean().mul(100).round(1).alias("p8")).pivot(on="pt", index="YEAR", values="p8").sort("YEAR"))
print("DRUGS=8 % by PER_TYP group and year:")
print(x.group_by(["YEAR","pt"]).agg((pl.col("DRUGS")==8).mean().mul(100).round(1).alias("p8")).pivot(on="pt", index="YEAR", values="p8").sort("YEAR"))
