"""G04: (a) heavy-GVWR vehicles NOT counted as large trucks (buses, HD pickups) -> missed deaths; light vehicles counted;
(b) parked/not-in-transport trucks (UNITTYPE); (c) truck-vs-PV two-vehicle crashes: deaths per vehicle by side (mass disparity);
(d) sensitivity: define 'not truck occupant' (excl. truck passengers) and 'not driver of any vehicle in truck'."""
import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_cols(20)
Dd=pl.read_parquet("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/G04/deaths.parquet")
vs=[]
for y in range(2016,2025):
    v=pl.read_parquet(f"data/interim/FARS/vehicle/{y}.parquet")
    cols=[c for c in ["ST_CASE","VEH_NO","BODY_TYP","GVWR","GVWR_FROM","GVWR_TO","UNITTYPE","DEATHS","NUMOCCS"] if c in v.columns]
    a=pl.read_parquet(f"data/interim/FARS/veh_aux/{y}.parquet").select(["ST_CASE","VEH_NO","A_BODY"])
    vs.append(v.select(cols).join(a,on=["ST_CASE","VEH_NO"]).with_columns(pl.lit(y).alias("yr")))
V=pl.concat(vs,how="diagonal_relaxed").with_columns(pl.col("A_BODY").cast(pl.Int64,strict=False))
heavy=((pl.col("yr")<=2019)&pl.col("GVWR").is_in([2,3]))|((pl.col("yr")>=2020)&(pl.col("GVWR_FROM")>=13)&(pl.col("GVWR_FROM")<=18))
V=V.with_columns(heavy.alias("heavy"))
print("A_BODY x heavy (vehicle counts):\n",V.group_by(["A_BODY","heavy"]).len().sort(["A_BODY","heavy"]))
print("heavy but A_BODY!=6 by BODY_TYP:\n",V.filter(pl.col("heavy")&(pl.col("A_BODY")!=6)).group_by(["A_BODY","BODY_TYP"]).len().sort("len",descending=True).head(12))
print("A_BODY==6 but not heavy:",V.filter((pl.col("A_BODY")==6)&~pl.col("heavy")).height,"of",V.filter(pl.col("A_BODY")==6).height)
# deaths in crashes with a heavy vehicle that is non-A_BODY6 and no A_BODY6
cr=V.group_by(["yr","ST_CASE"]).agg((pl.col("A_BODY")==6).any().alias("lt"),(pl.col("heavy")&(pl.col("A_BODY")!=6)).any().alias("h_other"),(pl.col("heavy")&(pl.col("A_BODY")==8)).any().alias("h_bus"),
   ((pl.col("A_BODY")==6)&(pl.col("UNITTYPE")!=1)).any().alias("lt_notrans") if "UNITTYPE" in V.columns else pl.lit(False).alias("lt_notrans"))
D=Dd.join(cr,on=["yr","ST_CASE"],how="left",suffix="_c")
print("deaths: LT",D.filter(pl.col("lt")).height,"| heavy non-LT only",D.filter(~pl.col("lt")&pl.col("h_other")).height,"| of which bus",D.filter(~pl.col("lt")&pl.col("h_bus")).height)
print("deaths in LT crashes where a truck is UNITTYPE!=1:",D.filter(pl.col("lt_notrans")).height)
print(V.filter(pl.col("A_BODY")==6).group_by("UNITTYPE").len())
# (c) two-vehicle truck + PV
tv=V.group_by(["yr","ST_CASE"]).agg(pl.len().alias("n"),(pl.col("A_BODY")==6).sum().alias("nt"),(pl.col("A_BODY").is_in([1,2,3,4,5])).sum().alias("npv"))
two=tv.filter((pl.col("n")==2)&(pl.col("nt")==1)&(pl.col("npv")==1))
dd=D.join(two.select(["yr","ST_CASE"]).with_columns(pl.lit(1).alias("k")),on=["yr","ST_CASE"],how="inner")
print("2-veh truck+PV crashes",two.height,"deaths",dd.height,"truck-occ deaths",dd.filter(pl.col("A_BODY")==6).height,"PV-occ deaths",dd.filter(pl.col("A_BODY")!=6).height)
vv=V.join(two.select(["yr","ST_CASE"]),on=["yr","ST_CASE"],how="inner")
print("avg DEATHS field per vehicle by class:",vv.group_by(pl.col("A_BODY")==6).agg(pl.col("DEATHS").mean(),pl.col("NUMOCCS").mean()))
# two-veh PV+PV crashes for symmetry baseline
pp=tv.filter((pl.col("n")==2)&(pl.col("npv")==2))
vp=V.join(pp.select(["yr","ST_CASE"]),on=["yr","ST_CASE"],how="inner")
print("2-veh PV+PV mean DEATHS per vehicle",vp["DEATHS"].mean(),"NUMOCCS",vp["NUMOCCS"].mean())
# (d) sensitivities
lt=D.filter(pl.col("lt"))
print("share who were truck occupants (any role):",(lt["A_BODY"]==6).mean(), " share neither occupant nor ped/cyc (other-vehicle occ):",lt.filter(pl.col("A_PTYPE").is_in([1,2])&(pl.col("A_BODY")!=6)).height/lt.height)
print("2019->2021 / 2024 vs all deaths: LT crash deaths 2019,2021,2024:",[lt.filter(pl.col("yr")==y).height for y in (2019,2021,2024)],"all:",[Dd.filter(pl.col("yr")==y).height for y in (2019,2021,2024)])
