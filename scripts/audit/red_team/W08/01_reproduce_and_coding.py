"""W08: reproduce 2019->2021 changes (all, invalid-licence crash, hit&run, urban, rural) from raw FARS
interim tables, and inspect coding: licence-status distribution/unknown by year, A_RU codes by year,
A_HR vs vehicle HIT_RUN, and disjoint-complement Poisson tests of 'steeper than all'. Look at printed tables."""
import polars as pl, numpy as np
from math import sqrt, log, exp
L=lambda t,cols:pl.concat([pl.read_parquet(f"data/interim/FARS/{t}/{y}.parquet").with_columns(YEAR=pl.lit(y)).select(cols) for y in range(2016,2025)])
acc=L("acc_aux",["YEAR","ST_CASE","FATALS","A_RU","A_HR"])
print("A_RU codes by year (deaths):");print(acc.group_by("YEAR","A_RU").agg(pl.col("FATALS").sum()).pivot(on="A_RU",index="YEAR",values="FATALS").sort("YEAR"))
d=acc.group_by("YEAR").agg(pl.col("FATALS").sum().alias("all"),
 pl.col("FATALS").filter(pl.col("A_RU")==1).sum().alias("rural"),pl.col("FATALS").filter(pl.col("A_RU")==2).sum().alias("urban"),
 pl.col("FATALS").filter(pl.col("A_HR")==1).sum().alias("hr"))
veh=L("vehicle",["YEAR","ST_CASE","VEH_NO","L_STATUS","HIT_RUN"]);per=L("person",["YEAR","ST_CASE","VEH_NO","PER_TYP"]).filter(pl.col("PER_TYP")==1)
dr=per.join(veh,on=["YEAR","ST_CASE","VEH_NO"],how="left")
print("L_STATUS by year (driver counts):");print(dr.group_by("YEAR","L_STATUS").len().pivot(on="L_STATUS",index="YEAR",values="len").sort("YEAR"))
print("share unknown (not 0-4,6) among drivers:");print(dr.group_by("YEAR").agg((~pl.col("L_STATUS").is_in([0,1,2,3,4,6])).mean().alias("unk"),pl.len().alias("n_drivers")).sort("YEAR"))
inv=dr.filter(pl.col("L_STATUS").is_in([0,1,2,3,4])).select("YEAR","ST_CASE").unique().with_columns(inv=pl.lit(True))
a=acc.join(inv,on=["YEAR","ST_CASE"],how="left").with_columns(pl.col("inv").fill_null(False))
d=d.join(a.group_by("YEAR").agg(pl.col("FATALS").filter(pl.col("inv")).sum().alias("inv")),on="YEAR").sort("YEAR")
print(d)
d.write_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W08/annual.csv")
p=d.to_pandas().set_index("YEAR")
print("pct 19->21:",((p.loc[2021]/p.loc[2019]-1)*100).round(1).to_dict())
print("pct 19->24:",((p.loc[2024]/p.loc[2019]-1)*100).round(1).to_dict())
# A_HR vs vehicle HIT_RUN
hv=veh.group_by("YEAR","ST_CASE").agg((pl.col("HIT_RUN")>0).any().alias("vhr"),pl.col("HIT_RUN").max().alias("mx"))
x=acc.join(hv,on=["YEAR","ST_CASE"]);print("A_HR==1 vs any vehicle HIT_RUN>0 (crash counts):");print(x.group_by("YEAR").agg((pl.col("A_HR")==1).sum().alias("A_HR"),pl.col("vhr").sum().alias("veh_any"),((pl.col("A_HR")==1)&pl.col("vhr")).sum().alias("both")).sort("YEAR"))
print(veh.group_by("HIT_RUN").len())
# Poisson tests: group vs complement (disjoint) log ratio of ratios 2019->2021
def test(name,g19,g21,t19,t21):
    c19,c21=t19-g19,t21-g21
    lr=log((g21/g19)/(c21/c19)); se=sqrt(1/g19+1/g21+1/c19+1/c21)
    print(f"{name}: group {g21/g19-1:+.3f}, complement {c21/c19-1:+.3f}, ratio-of-ratios {exp(lr):.3f} CI {exp(lr-1.96*se):.3f}-{exp(lr+1.96*se):.3f}")
for s in ["inv","hr","urban"]:
    test(s,p.loc[2019,s],p.loc[2021,s],p.loc[2019,"all"],p.loc[2021,"all"])
test("urban vs rural",p.loc[2019,"urban"],p.loc[2021,"urban"],p.loc[2019,"urban"]+p.loc[2019,"rural"],p.loc[2021,"urban"]+p.loc[2021,"rural"])
test("inv vs hr-free",p.loc[2019,"inv"],p.loc[2021,"inv"],p.loc[2019,"all"],p.loc[2021,"all"])
