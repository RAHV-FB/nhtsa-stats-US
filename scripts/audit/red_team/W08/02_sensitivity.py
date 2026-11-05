"""W08: attacks on (a) licence definition (expired/cancelled status 3,4 during COVID extensions; unknown status as invalid),
(b) overlap (invalid-licence deaths excluding hit&run / BAC-positive-driver crashes via A_POSBAC), (c) baseline/endpoint choices,
(d) 'steepest' ranking against all committed segments with Poisson CIs. Read printed output."""
import polars as pl, numpy as np
from math import log, sqrt, exp
L=lambda t,cols:pl.concat([pl.read_parquet(f"data/interim/FARS/{t}/{y}.parquet").with_columns(YEAR=pl.lit(y)).select(cols) for y in range(2016,2025)])
acc=L("acc_aux",["YEAR","ST_CASE","FATALS","A_RU","A_HR","A_POSBAC","A_SPCRA"])
veh=L("vehicle",["YEAR","ST_CASE","VEH_NO","L_STATUS"]);per=L("person",["YEAR","ST_CASE","VEH_NO","PER_TYP"]).filter(pl.col("PER_TYP")==1)
dr=per.join(veh,on=["YEAR","ST_CASE","VEH_NO"],how="left")
def crashflag(codes,name):
    f=dr.filter(pl.col("L_STATUS").is_in(codes)).select("YEAR","ST_CASE").unique().with_columns(pl.lit(True).alias(name))
    return f
a=acc
for nm,codes in {"inv_all":[0,1,2,3,4],"inv_012":[0,1,2],"inv_34":[3,4],"inv_0":[0],"inv_12":[1,2],"inv_plus_unk":[0,1,2,3,4,9,7,8]}.items():
    a=a.join(crashflag(codes,nm),on=["YEAR","ST_CASE"],how="left").with_columns(pl.col(nm).fill_null(False))
print("A_POSBAC codes:",acc.group_by("A_POSBAC").len().sort("A_POSBAC").to_dicts())
cols=["inv_all","inv_012","inv_34","inv_0","inv_12","inv_plus_unk"]
t=a.group_by("YEAR").agg(pl.col("FATALS").sum().alias("all"),*[pl.col("FATALS").filter(pl.col(c)).sum().alias(c) for c in cols],
  pl.col("FATALS").filter(pl.col("inv_all")&(pl.col("A_HR")!=1)).sum().alias("inv_noHR"),
  pl.col("FATALS").filter(pl.col("inv_all")&(pl.col("A_HR")!=1)&(pl.col("A_POSBAC")!=1)).sum().alias("inv_noHR_noPosBAC"),
  pl.col("FATALS").filter(pl.col("inv_all")&(pl.col("A_HR")!=1)&(pl.col("A_SPCRA")!=1)).sum().alias("inv_noHR_noSpd"),
  pl.col("FATALS").filter(pl.col("A_HR")==1).sum().alias("hr"),
  pl.col("FATALS").filter((pl.col("A_HR")==1)&~pl.col("inv_all")).sum().alias("hr_noinv"),
  pl.col("FATALS").filter(pl.col("inv_all")&(pl.col("A_HR")==1)).sum().alias("inv_and_hr"),
  pl.col("FATALS").filter(pl.col("A_RU")==2).sum().alias("urban")).sort("YEAR").to_pandas().set_index("YEAR")
print(t)
pc=lambda a,b:(t.loc[b]/t.loc[a]-1)*100
print("\n% change 2019->2021:\n",pc(2019,2021).round(1).to_string())
print("\n% change 2019->2020:\n",pc(2019,2020).round(1).to_string())
print("\n% change 2019->2022:\n",pc(2019,2022).round(1).to_string())
base=t.loc[2016:2019].mean()
print("\n% change 2016-19 mean -> 2021:\n",((t.loc[2021]/base-1)*100).round(1).to_string())
print("\n% change 2016-19 mean -> 2020-21 mean:\n",((t.loc[2020:2021].mean()/base-1)*100).round(1).to_string())
print("\nunknown-adjusted: share of 2021 increase in inv_all from codes 3/4:",t.loc[2021,"inv_34"]-t.loc[2019,"inv_34"],"of",t.loc[2021,"inv_all"]-t.loc[2019,"inv_all"])
# Poisson CI of % change for each segment (single-year counts), and gap vs all via complement
seg=pd=None
import csv
rows=list(csv.DictReader(open("outputs/tables/deaths/segments.csv")))
A19,A21=36355,43230
print("\nsegment: pct19-21, ratio-of-ratios vs rest (disjoint complement), 95% CI")
out=[]
for r in rows:
    if r["segment"] in("all",):continue
    g19,g21=float(r["deaths_2019"]),float(r["deaths_2021"]); c19,c21=A19-g19,A21-g21
    if c19<=0: continue
    rr=(g21/g19)/(c21/c19); se=sqrt(1/g19+1/g21+1/c19+1/c21)
    out.append((r["segment"],round((g21/g19-1)*100,1),round(rr,3),round(exp(log(rr)-1.96*se),3),round(exp(log(rr)+1.96*se),3)))
for o in sorted(out,key=lambda x:-x[1]):print(o)
# pairwise: invalid vs hit&run vs alcohol difference
for a_,b_ in [("invalid_licence_crash","hit_and_run"),("hit_and_run","alcohol_impaired"),("invalid_licence_crash","alcohol_impaired"),("invalid_licence_crash","speeding")]:
    ra=[r for r in rows if r["segment"]==a_][0];rb=[r for r in rows if r["segment"]==b_][0]
    f=lambda r:(float(r["deaths_2019"]),float(r["deaths_2021"]))
    (a19,a21),(b19,b21)=f(ra),f(rb)
    d=log(a21/a19)-log(b21/b19);se=sqrt(1/a19+1/a21+1/b19+1/b21)  # ignores positive covariance from overlap (conservative)
    print(a_,"vs",b_,f"log-ratio diff {d:.3f}, z={d/se:.2f}")
t.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W08/sens.csv")
