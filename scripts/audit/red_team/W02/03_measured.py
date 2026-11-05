"""W02 attack: how much of 'not the drunk driver' rests on imputation? Restrict to crashes with a driver whose
MEASURED BAC (person.ALC_RES 80..940 (thousandths; units verified in 04_alcres_check.py), tested) is >=.08 (no imputation). Also: does MIPER cover passengers?
Also: killed passengers of drunk driver / other occupants with measured BAC>=.08 (complicity), for deaths tested.
Look at: not-driver share under measured-only definition; MIPER coverage by PER_TYP; tested share among killed non-drivers."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
K=["YEAR","ST_CASE"]
per=load_table("FARS","person",None,["ST_CASE","VEH_NO","PER_NO","PER_TYP","INJ_SEV","ALC_RES"])
pa=load_table("FARS","per_aux",None,["ST_CASE","VEH_NO","PER_NO","A_PTYPE"])
mi=load_table("FARS","miper",None,["ST_CASE","VEH_NO","PER_NO","P1"])
p=per.join(pa,on=K+["VEH_NO","PER_NO"],how="left").join(mi,on=K+["VEH_NO","PER_NO"],how="left")
print("MIPER coverage by A_PTYPE (non-null P1 / n), killed only:")
print(p.filter(pl.col("INJ_SEV")==4).group_by("A_PTYPE").agg(n=pl.len(),mi=pl.col("P1").is_not_null().sum(),tested=((pl.col("ALC_RES")>=0)&(pl.col("ALC_RES")<=940)).sum()).sort("A_PTYPE"))
meas=((pl.col("ALC_RES")>=80)&(pl.col("ALC_RES")<=940))
drv=p.filter(pl.col("PER_TYP")==1).select(K+["VEH_NO",meas.alias("dm")])
cm=drv.group_by(K).agg(pl.col("dm").any().alias("crash_m"))
d=p.filter(pl.col("INJ_SEV")==4).join(drv,on=K+["VEH_NO"],how="left").join(cm,on=K,how="left")
x=d.filter(pl.col("crash_m").fill_null(False)).with_columns(
    drv=(pl.col("A_PTYPE")==1)&pl.col("dm").fill_null(False),
    pas=(pl.col("A_PTYPE")==2)&pl.col("dm").fill_null(False))
n=x.height
print("measured-only drunk crashes: deaths",n,"per year",n/9,"not-driver share",1-x["drv"].sum()/n,"third-party share (excl risk passengers)",1-(x["drv"].sum()+x["pas"].sum())/n)
# measured >=.08 among non-driver, tested occupants
nd=x.filter(~pl.col("drv"))
t=nd.filter((pl.col("ALC_RES")>=0)&(pl.col("ALC_RES")<=940))
print("non-driver deaths",nd.height,"tested",t.height,"of tested BAC>=.08",t.filter(meas).height)
print("by A_PTYPE among non-driver tested: ",t.group_by("A_PTYPE").agg(n=pl.len(),hi=meas.sum()).sort("A_PTYPE").rows())
print("risk-passengers tested",t.filter(pl.col("pas")).height,"BAC>=.08",t.filter(pl.col("pas")&meas).height)
# drivers killed in the crash: measured share among all drunk-crash drivers
print("drunk crash: ALC_RES coding of killed drivers in imputation-dependent crashes not shown")
