"""W05 attack 0: reproduce 17%, 72.6%, 19.9%, 23.1% from raw FARS interim tables with own code,
and inspect coding by year (LOCATION, HIT_RUN, VSPD_LIM, PER_TYP). Look at the per-year tables."""
import polars as pl, glob
def rd(t, cols=None):
    fs = sorted(glob.glob(f"data/interim/FARS/{t}/*.parquet"))
    out=[]
    for f in fs:
        d=pl.read_parquet(f); y=int(f.split('/')[-1].split('.')[0])
        d=d.with_columns(pl.lit(y).alias("Y"))
        if cols: d=d.select(["Y"]+[c for c in cols if c in d.columns])
        out.append(d)
    return pl.concat(out, how="diagonal_relaxed")
per=rd("person",["ST_CASE","VEH_NO","PER_NO","INJ_SEV","PER_TYP","LOCATION","STR_VEH","AGE"])
print(per.columns)
dead=per.filter(pl.col("INJ_SEV")==4)
print("deaths",dead.height); print(dead.group_by("PER_TYP").len().sort("PER_TYP"))
ped=dead.filter(pl.col("PER_TYP")==5)
print("PER_TYP==5 deaths",ped.height, ped.height/dead.height)
print(ped.group_by("LOCATION").len().sort("LOCATION"))
print("LOCATION by year (null/other share)")
print(ped.group_by("Y").agg(pl.len().alias("n"),
  (pl.col("LOCATION").is_in([10,11,13,16]).mean()).alias("mid"),
  (pl.col("LOCATION").is_in([1,2,3,9]).mean()).alias("int"),
  (pl.col("LOCATION").is_null()|pl.col("LOCATION").is_in([0,28,98,99])).mean().alias("unk")).sort("Y"))
acc=rd("accident",["ST_CASE","LGT_COND","HIT_RUN","RUR_URB","FUNC_SYS","HOUR","MONTH"])
print(acc.group_by("Y","HIT_RUN").len().sort("Y","HIT_RUN").pivot(on="HIT_RUN",index="Y",values="len"))
m=ped.join(acc,on=["Y","ST_CASE"],how="left")
print(m.group_by("LGT_COND").len().sort("LGT_COND"))
print("daylight",(m["LGT_COND"]==1).mean(),"hitrun1",(m["HIT_RUN"]==1).mean(),"hitrun>0",(m["HIT_RUN"]>0).mean())
print(m.group_by("Y").agg((pl.col("HIT_RUN")>0).mean().alias("hr_any"),(pl.col("HIT_RUN")==1).mean().alias("hr1"),(pl.col("LGT_COND")==1).mean().alias("day")).sort("Y"))
m.write_parquet("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W05/ped.parquet")
