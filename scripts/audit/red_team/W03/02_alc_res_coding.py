"""Check ALC_RES scale/codes vs MI P1 so measured BAC can be defined correctly."""
import polars as pl
from nhtsa_stats.analysis import deaths as D
per=D.load_table("FARS","person",None,["YEAR","ST_CASE","VEH_NO","PER_NO","PER_TYP","ALC_RES","ALC_STATUS"]).filter(pl.col("PER_TYP")==1)
mi=D.load_table("FARS","miper",None,["YEAR","ST_CASE","VEH_NO","PER_NO","P1","P2"])
x=per.join(mi,on=["YEAR","ST_CASE","VEH_NO","PER_NO"])
print(x.group_by("ALC_STATUS").agg(pl.len(),pl.col("ALC_RES").min().alias("mn"),pl.col("ALC_RES").max().alias("mx")).sort("ALC_STATUS"))
print(x.filter(pl.col("ALC_RES").is_between(70,100)).group_by("ALC_RES").agg(pl.len(),pl.col("P1").mean()).sort("ALC_RES").head(40))
print(x.filter(pl.col("ALC_RES")>=900).group_by("ALC_RES").agg(pl.len()).sort("ALC_RES"))
print(x.filter(pl.col("ALC_RES").is_between(80,81)).select("YEAR","ALC_RES","P1").head(10))
