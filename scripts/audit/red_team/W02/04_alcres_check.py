"""W02 helper: check ALC_RES coding/units (is >=8 'measured BAC .08+'?), and compare measured-driver BAC>=.08 with MIPER-based driver flags
(P_m>=8), to see how many MIPER-drunk drivers are actually measured. Look at distribution by year and the measured share."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
K=["YEAR","ST_CASE"]
per=load_table("FARS","person",None,["ST_CASE","VEH_NO","PER_NO","PER_TYP","INJ_SEV","ALC_RES","ALC_DET"])
mi=load_table("FARS","miper",None,["ST_CASE","VEH_NO","PER_NO"]+[f"P{m}" for m in range(1,11)])
p=per.filter(pl.col("PER_TYP")==1).join(mi,on=K+["VEH_NO","PER_NO"],how="left")
print(p.group_by("YEAR").agg(n=pl.len(),mx=pl.col("ALC_RES").max(),t=((pl.col("ALC_RES")>=0)&(pl.col("ALC_RES")<=94)).sum(),ge8=((pl.col("ALC_RES")>=8)&(pl.col("ALC_RES")<=94)).sum()).sort("YEAR"))
print(p.group_by("ALC_RES").len().sort("len",descending=True).head(15))
p=p.with_columns(meas=(pl.col("ALC_RES")>=8)&(pl.col("ALC_RES")<=94),nimp=sum((pl.col(f"P{m}")>=8).cast(pl.Int32) for m in range(1,11)))
print("drivers MIPER-drunk in >=1 implicate, by nimp and measured:")
print(p.filter(pl.col("nimp")>0).group_by("nimp").agg(n=pl.len(),meas=pl.col("meas").sum()).sort("nimp"))
print("measured>=.08 drivers n",p["meas"].sum(),"of which nimp==10:",p.filter(pl.col("meas")&(pl.col("nimp")==10)).height)
print("avg drunk drivers/implicate",sum(p.filter(pl.col(f'P{m}')>=8).height for m in range(1,11))/10)
