"""G04: reproduce large-truck deaths/shares from raw FARS and test definition attacks.
Looks at: A_LT crash flag vs A_BODY==6 vs GVWR-based definition; year counts; role shares;
benchmark of 'not the driver of vehicle X' share for other body types (mass-disparity null)."""
import polars as pl, glob
Y=range(2016,2025)
def rd(t,y,cols=None):
    d=pl.read_parquet(f"data/interim/FARS/{t}/{y}.parquet")
    return d.select([c for c in cols if c in d.columns]) if cols else d
K=["ST_CASE"]
out=[]
for y in Y:
    per=rd("person",y,["ST_CASE","VEH_NO","PER_NO","INJ_SEV","PER_TYP"]).filter(pl.col("INJ_SEV")==4)
    pa=rd("per_aux",y,["ST_CASE","VEH_NO","PER_NO","A_PTYPE"])
    va=rd("veh_aux",y,["ST_CASE","VEH_NO","A_BODY"])
    ca=rd("acc_aux",y,["ST_CASE","A_LT"])
    v=rd("vehicle",y)
    vc=[c for c in ["ST_CASE","VEH_NO","BODY_TYP","GVWR","GVWR_FROM","GVWR_TO","TOW_VEH","UNITTYPE"] if c in v.columns]
    v=v.select(vc)
    d=per.join(pa,on=["ST_CASE","VEH_NO","PER_NO"],how="left").join(va,on=["ST_CASE","VEH_NO"],how="left").join(ca,on="ST_CASE",how="left").join(v,on=["ST_CASE","VEH_NO"],how="left").with_columns(pl.lit(y).alias("yr"))
    d=d.with_columns(pl.col("A_PTYPE").cast(pl.Int64,strict=False),pl.col("A_BODY").cast(pl.Int64,strict=False),pl.col("A_LT").cast(pl.Int64,strict=False))
    # crash-level: number of A_BODY==6 vehicles, number of vehicles, GVWR-based
    allv=rd("veh_aux",y,["ST_CASE","VEH_NO","A_BODY"]).join(v,on=["ST_CASE","VEH_NO"],how="left")
    g=allv.group_by("ST_CASE").agg((pl.col("A_BODY")==6).sum().alias("n_lt"),pl.len().alias("n_veh"),
        ((pl.col("A_BODY")==6)&(pl.col("TOW_VEH").cast(pl.Int64,strict=False)>=1)).sum().alias("n_lt_tow") if "TOW_VEH" in allv.columns else pl.lit(0).alias("n_lt_tow"),
        (pl.col("A_BODY").is_in([1,2,3,4,5])).sum().alias("n_pv"))
    d=d.join(g,on="ST_CASE",how="left")
    out.append(d)
D=pl.concat(out,how="diagonal_relaxed")
D.write_parquet("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/G04/deaths.parquet")
print("total deaths",D.height)
lt=D.filter(pl.col("A_LT")==1)
print("LT crash deaths",lt.height, "share",lt.height/D.height)
print(D.group_by("yr").agg(pl.len().alias("all"),(pl.col("A_LT")==1).sum().alias("lt")).sort("yr"))
r=lt.with_columns(pl.when((pl.col("A_PTYPE")==1)&(pl.col("A_BODY")==6)).then(pl.lit("risk_driver")).otherwise(pl.lit("other")).alias("r"))
print("not truck driver share",(r["r"]!="risk_driver").mean())
print("A_LT=1 but no A_BODY==6 vehicle in crash deaths:",lt.filter(pl.col("n_lt")==0).height, " A_LT!=1 but n_lt>0:",D.filter((pl.col("A_LT")!=1)&(pl.col("n_lt")>0)).height)
print(D.filter(pl.col("n_lt")>0).group_by("yr").agg(pl.len()).sort("yr"))
print("GVWR cols:",[c for c in D.columns if "GVWR" in c or c in("BODY_TYP","TOW_VEH")])
