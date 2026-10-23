"""Build CRSS person/vehicle/crash alcohol-drug analysis files. Output: out_ad/crss_person.parquet, crss_crash.parquet"""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
OUT = "outputs/cache/audit/out_ad"
p = load_table("CRSS","person",years=None,columns=["CASENUM","VEH_NO","PER_NO","PER_TYP","INJ_SEV","DRINKING","ALC_STATUS","ATST_TYP","ALC_RES","DRUGS","PERALCH_IM","DRUGTST1","DRUGRES1","DRUGRES2","DRUGRES3"])
v = load_table("CRSS","vehicle",years=None,columns=["CASENUM","VEH_NO","VEH_ALCH","V_ALCH_IM"])
a = load_table("CRSS","accident",years=None,columns=["CASENUM","ALCOHOL","ALCHL_IM","MAX_SEV","MAXSEV_IM","MONTH","WEIGHT","PSU","PSU_VAR","PSUSTRAT","STRATUM","PJ","REGION","URBANICITY"])
di = load_table("CRSS","drimpair",years=None,columns=["CASENUM","VEH_NO","DRIMPAIR"])
di = di.group_by(["YEAR","CASENUM","VEH_NO"]).agg((pl.col("DRIMPAIR")==9).any().alias("drimp_9"), pl.col("DRIMPAIR").is_in([98,99]).all().alias("drimp_unk"))
df = p.join(v, on=["YEAR","CASENUM","VEH_NO"], how="left").join(a, on=["YEAR","CASENUM"], how="left").join(di, on=["YEAR","CASENUM","VEH_NO"], how="left")
print(df.height, p.height)
df.write_parquet(f"{OUT}/crss_person.parquet")
a.write_parquet(f"{OUT}/crss_crash.parquet")
v2 = v.join(a.select(["YEAR","CASENUM","WEIGHT","MAX_SEV","MONTH"]), on=["YEAR","CASENUM"]).join(di, on=["YEAR","CASENUM","VEH_NO"], how="left")
v2.write_parquet(f"{OUT}/crss_vehicle.parquet")
