"""W06 attack 0/1: reproduce 37.9% unhelmeted, +23.5% deaths, and decompose by BODY_TYP,
raw helmet codes by year (2019 code move), and HELM_MIS. Look at: totals, share by body type,
share by year under alt definitions (any recorded helmet-code non-helmet incl. 'other')."""
import polars as pl
from pathlib import Path
rows=[]
for y in range(2016,2025):
    p=pl.read_parquet(f"data/interim/FARS/person/{y}.parquet")
    for c in ["HELM_USE","HELM_MIS"]:
        if c not in p.columns: p=p.with_columns(pl.lit(None,dtype=pl.Int64).alias(c))
    p=p.select(["ST_CASE","VEH_NO","PER_NO","BODY_TYP","PER_TYP","INJ_SEV","SEAT_POS","REST_USE","HELM_USE","HELM_MIS","AGE","SEX"])
    a=pl.read_parquet(f"data/interim/FARS/per_aux/{y}.parquet",columns=["ST_CASE","VEH_NO","PER_NO","A_PTYPE","A_HELMUSE"])
    v=pl.read_parquet(f"data/interim/FARS/veh_aux/{y}.parquet",columns=["ST_CASE","VEH_NO","A_BODY"])
    d=p.join(a,on=["ST_CASE","VEH_NO","PER_NO"]).join(v,on=["ST_CASE","VEH_NO"]).with_columns(pl.lit(y).alias("Y"))
    rows.append(d)
d=pl.concat(rows,how="diagonal_relaxed")
d.write_parquet("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W06/person_all.parquet")
mc=d.filter((pl.col("A_BODY")==7)&pl.col("A_PTYPE").is_in([1,2])&(pl.col("INJ_SEV")==4))
print("killed mc occupants",mc.height)
print(mc.group_by("Y").len().sort("Y"))
print(mc.group_by("BODY_TYP").len().sort("BODY_TYP"))
k=mc.filter(pl.col("A_HELMUSE").is_in([1,2]))
print("known",k.height,"unhelm",k.filter(pl.col("A_HELMUSE")==2).height, k.filter(pl.col("A_HELMUSE")==2).height/k.height)
print(mc.with_columns(src=pl.when(pl.col("Y")<=2018).then(pl.col("REST_USE")).otherwise(pl.col("HELM_USE"))).group_by(["Y","src"]).agg(pl.len(),pl.col("A_HELMUSE").mean().alias("aux")).sort(["Y","src"]).to_pandas().pivot(index="src",columns="Y",values="len").fillna(0).astype(int))
# by body type share unhelmeted
print(k.group_by("BODY_TYP").agg(pl.len().alias("n"),(pl.col("A_HELMUSE")==2).mean().alias("unh")).sort("BODY_TYP"))
# year share, with 'other helmet' (16) treated as unprotected, vs published
print(k.group_by("Y").agg(pl.len().alias("n"),(pl.col("A_HELMUSE")==2).mean().alias("unh")).sort("Y"))
print("deaths 2019,2024:",mc.filter(pl.col("Y")==2019).height,mc.filter(pl.col("Y")==2024).height, mc.filter(pl.col("Y")==2024).height/mc.filter(pl.col("Y")==2019).height-1)
