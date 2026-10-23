"""Build FARS person-level analysis file (all persons) with alcohol/drug fields, aux, MI implicates, DR_DRINK, impairment flags.
Output: out_ad/fars_person.parquet"""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
OUT = "outputs/cache/audit/out_ad"
K = ["YEAR","ST_CASE","VEH_NO","PER_NO"]
p = load_table("FARS","person",years=None,columns=["ST_CASE","VEH_NO","PER_NO","STATE","PER_TYP","INJ_SEV","AGE","SEX","DOA",
     "DRINKING","ALC_STATUS","ATST_TYP","ALC_RES","ALC_DET","DRUGS","DRUG_DET","DRUGTST1","DRUGTST2","DRUGTST3","DRUGRES1","DRUGRES2","DRUGRES3"])
pa = load_table("FARS","per_aux",years=None,columns=["ST_CASE","VEH_NO","PER_NO","A_ALCTES","A_PTYPE","A_PERINJ"])
mi = load_table("FARS","miper",years=None,columns=["ST_CASE","VEH_NO","PER_NO"]+[f"P{i}" for i in range(1,11)])
mi = mi.with_columns(pl.lit(1).alias("in_miper"))
v = load_table("FARS","vehicle",years=None,columns=["ST_CASE","VEH_NO","DR_DRINK"])
di = load_table("FARS","drimpair",years=None,columns=["ST_CASE","VEH_NO","DRIMPAIR"])
di = di.group_by(["YEAR","ST_CASE","VEH_NO"]).agg((pl.col("DRIMPAIR")==9).any().alias("drimp_9"),
        pl.col("DRIMPAIR").is_in([98,99]).all().alias("drimp_unk"), (pl.col("DRIMPAIR")==95).any().alias("drimp_95"))
ni = load_table("FARS","nmimpair",years=None,columns=["ST_CASE","VEH_NO","PER_NO","NMIMPAIR"])
ni = ni.group_by(K).agg((pl.col("NMIMPAIR")==9).any().alias("nmimp_9"), pl.col("NMIMPAIR").is_in([98,99]).all().alias("nmimp_unk"))
a = load_table("FARS","accident",years=None,columns=["ST_CASE","DRUNK_DR","FATALS"])
aa = load_table("FARS","acc_aux",years=None,columns=["ST_CASE","A_POSBAC"])
df = (p.join(pa, on=K, how="left").join(mi, on=K, how="left").join(v, on=["YEAR","ST_CASE","VEH_NO"], how="left")
       .join(di, on=["YEAR","ST_CASE","VEH_NO"], how="left").join(ni, on=K, how="left")
       .join(a, on=["YEAR","ST_CASE"], how="left").join(aa, on=["YEAR","ST_CASE"], how="left"))
print(df.height, p.height, pa.height, mi.height)
# miper rows not matched to person
print("miper rows without person:", mi.join(p.select(K), on=K, how="anti").height)
df.write_parquet(f"{OUT}/fars_person.parquet")
