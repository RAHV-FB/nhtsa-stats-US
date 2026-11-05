"""G04 attacks on saved deaths.parquet (from 01): (a) body-type/GVWR composition of A_BODY==6 by year (coding breaks);
(b) mass-disparity null: share of deaths 'not the driver of vehicle class X' for crashes with a class X vehicle;
(c) partner mix for truck crashes (single-vehicle, truck+PV, truck+truck, ped); (d) shares by year; (e) multi-truck crashes; (f) TOW/bus."""
import polars as pl
D=pl.read_parquet("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/G04/deaths.parquet")
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(20)
lt=D.filter(pl.col("A_LT")==1)
# (a) composition of vehicles of dead persons in truck
t=lt.filter(pl.col("A_BODY")==6)
print("BODY_TYP of occupants dying in A_BODY==6 veh:\n",t.group_by("BODY_TYP").len().sort("len",descending=True).head(15))
print("GVWR by year (occupants in A_BODY==6):\n",t.group_by(["yr","GVWR"]).len().sort(["yr","GVWR"]).pivot(on="GVWR",index="yr",values="len"))
print("GVWR_FROM:\n",t.group_by(["yr","GVWR_FROM"]).len().sort(["yr","GVWR_FROM"]).pivot(on="GVWR_FROM",index="yr",values="len"))
print("TOW_VEH:\n",t.group_by("TOW_VEH").len().sort("TOW_VEH"))
# (b) shares by year
lt=lt.with_columns(((pl.col("A_PTYPE")==1)&(pl.col("A_BODY")==6)).alias("tdrv"))
print(lt.group_by("yr").agg((~pl.col("tdrv")).mean().alias("not_truck_driver"),pl.len()).sort("yr"))
# (c) crash type
lt=lt.with_columns(pl.when(pl.col("n_veh")==1).then(pl.lit("single_veh_truck"))
  .when(pl.col("n_lt")>=2).then(pl.lit("2+trucks"))
  .when(pl.col("n_pv")>=1).then(pl.lit("truck+PV(+)"))
  .otherwise(pl.lit("truck+other/nonocc")).alias("ctype"))
print(lt.group_by("ctype").agg(pl.len().alias("deaths"),(~pl.col("tdrv")).mean().alias("not_truck_driver"),
  (pl.col("A_PTYPE").is_in([3,4])).mean().alias("ped_cyc"),((pl.col("A_PTYPE")==2)&(pl.col("A_BODY")==6)).mean().alias("truck_pass")).sort("deaths",descending=True))
# 2+ trucks: "risk" = any truck; driver of ANY truck vs of one
m=lt.filter(pl.col("n_lt")>=2); print("2+ truck crash deaths",m.height,"; deaths who were drivers of a truck:",m.filter(pl.col("tdrv")).height)
# (d) mass-disparity null: for each class X (A_BODY of a vehicle), deaths in crashes with a X vehicle: share not driver of an X vehicle
rows=[]
for x,name in [(6,"large truck"),(1,"A_BODY1"),(2,"A_BODY2"),(3,"A_BODY3"),(4,"A_BODY4"),(5,"A_BODY5"),(7,"motorcycle"),(8,"bus")]:
    # crashes containing a body x vehicle: need per-crash flag; build from vehicle-level info via deaths' own vehicle only is insufficient -> use all vehicles
    pass
import glob
vs=[]
for y in range(2016,2025):
    vs.append(pl.read_parquet(f"data/interim/FARS/veh_aux/{y}.parquet").select(["ST_CASE","VEH_NO","A_BODY"]).with_columns(pl.lit(y).alias("yr")))
V=pl.concat(vs).with_columns(pl.col("A_BODY").cast(pl.Int64,strict=False))
for x,name in [(6,"large truck"),(1,"body1"),(2,"body2"),(3,"body3"),(4,"body4"),(5,"body5"),(7,"motorcycle"),(8,"bus")]:
    cr=V.filter(pl.col("A_BODY")==x).select(["yr","ST_CASE"]).unique().with_columns(pl.lit(True).alias("has"))
    d=D.join(cr,on=["yr","ST_CASE"],how="left").filter(pl.col("has")==True)
    dr=((d["A_PTYPE"]==1)&(d["A_BODY"]==x))
    rows.append((name,d.height,1-dr.mean(), (d["A_PTYPE"].is_in([3,4])).mean()))
print(pl.DataFrame(rows,schema=["class","deaths","not_driver_of_class_X","ped_cyc_share"],orient="row"))
# (e) bus/other: dead in A_BODY==8 crashes
