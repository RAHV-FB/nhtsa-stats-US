"""Misc FARS checks: 2024 provisional toxicology by month; vitreous jump by state; FARS crash-level alcohol comparable to CRSS ALCOHOL; MIDRVACC prevalence."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
OUT = "/tmp/nhtsa-audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_person.parquet")
acc = load_table("FARS","accident",years=None,columns=["ST_CASE","MONTH"])
dr = pl.read_parquet(f"{OUT}/fars_drivers.parquet").join(acc, on=["YEAR","ST_CASE"])
print("killed drivers: % ALC_RES=995 (not reported) by month, 2022-2024")
print(dr.filter((pl.col("sev")=="killed")&(pl.col("YEAR")>=2022)).group_by(["YEAR","MONTH"]).agg((pl.col("ALC_RES")==995).mean().mul(100).round(1).alias("p")).pivot(on="YEAR", index="MONTH", values="p", sort_columns=True).sort("MONTH"))
dp = pl.read_parquet(f"{OUT}/fars_drug_person.parquet")
dr2 = dr.join(dp.select(["YEAR","ST_CASE","VEH_NO","PER_NO","drug_test_status"]).rename({"drug_test_status":"dts"}), on=["YEAR","ST_CASE","VEH_NO","PER_NO"], how="left")
print("killed drivers: % drug unknown_if_tested by month 2023-2024")
print(dr2.filter((pl.col("sev")=="killed")&(pl.col("YEAR")>=2023)).group_by(["YEAR","MONTH"]).agg((pl.col("dts")=="unknown_if_tested").mean().mul(100).round(1).alias("p")).pivot(on="YEAR", index="MONTH", values="p", sort_columns=True).sort("MONTH"))
print("2024 vs 2023 killed-driver ALC 995 by state (top 8 increases):")
s = dr.filter((pl.col("sev")=="killed")&pl.col("YEAR").is_in([2023,2024])).group_by(["STATE","YEAR"]).agg((pl.col("ALC_RES")==995).mean().mul(100).round(1).alias("p"), pl.len()).pivot(on="YEAR", index="STATE", values=["p","len"], sort_columns=True)
print(s.with_columns((pl.col("p_2024")-pl.col("p_2023")).alias("d")).sort("d", descending=True).head(8))
# vitreous by state
v = df.filter(pl.col("ATST_TYP")==4).group_by(["STATE","YEAR"]).len().pivot(on="YEAR", index="STATE", values="len", sort_columns=True).fill_null(0).sort("2020", descending=True)
print("ATST_TYP=4 (vitreous) counts by state x year, top 6:"); print(v.head(6))
# FARS crash-level police-reported alcohol (CRSS ALCOHOL analogue): any driver or non-motorist with DRINKING=1 or measured BAC>0
nm = [5,6,7,8,10,11,12,13,19]
x = df.filter(pl.col("PER_TYP").is_in([1]+nm))
c = x.group_by(["YEAR","ST_CASE"]).agg(((pl.col("DRINKING")==1)|pl.col("ALC_RES").is_between(1,940)).any().alias("any_alc_crss_def"),
                                      ((pl.col("DRINKING")==1)).any().alias("any_drinking1"),
                                      ((pl.col("PER_TYP")==1)&(pl.col("DRINKING")==1)).any().alias("drv_drinking1"))
mi = load_table("FARS","midrvacc",years=None,columns=["ST_CASE"]+[f"A{i}" for i in range(1,11)])
mi = mi.with_columns(pl.mean_horizontal([(pl.col(f"A{i}")>=8).cast(pl.Float64) for i in range(1,11)]).alias("mi08"), pl.mean_horizontal([(pl.col(f"A{i}")>=1).cast(pl.Float64) for i in range(1,11)]).alias("mi01"))
aa = load_table("FARS","acc_aux",years=None,columns=["ST_CASE","A_POSBAC"])
c = acc.select(["YEAR","ST_CASE"]).join(c, on=["YEAR","ST_CASE"], how="left").join(mi.select(["YEAR","ST_CASE","mi08","mi01"]), on=["YEAR","ST_CASE"], how="left").join(aa, on=["YEAR","ST_CASE"])
print("FARS crash-level alcohol measures (% of all fatal crashes):")
print(c.group_by("YEAR").agg(pl.col("any_alc_crss_def").fill_null(False).mean().mul(100).round(1).alias("CRSS-ALCOHOL-analogue"), pl.col("drv_drinking1").fill_null(False).mean().mul(100).round(1).alias("any drv DRINKING=1"),
     (pl.col("A_POSBAC")==1).mean().mul(100).round(1).alias("A_POSBAC=1"), pl.col("mi08").mean().mul(100).round(1).alias("MIDRVACC>=.08"), pl.col("mi01").mean().mul(100).round(1).alias("MIDRVACC>=.01")).sort("YEAR"))
