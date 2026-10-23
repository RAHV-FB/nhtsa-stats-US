"""Code distributions per source-year for vehicle-table variables, with embedded labels."""
import polars as pl, re, sys
from nhtsa_stats.ingestion.cache import load_table
OUT = "outputs/cache/audit/out"
VARS = ["BODY_TYP","BDYTYP_IM","ICFINALBODY","VPICBODYCLASS","GVWR","GVWR_FROM","GVWR_TO","MOD_YEAR","MDLYR_IM",
 "NUMOCCS","UNITTYPE","HIT_RUN","HITRUN_IM","TOW_VEH","SPEC_USE","EMER_USE","BUS_USE","VSPD_LIM","VTRAFWAY","VNUM_LAN",
 "VALIGN","VPROFILE","VPAVETYP","VSURCOND","VTRAFCON","VTCONT_F","TRAV_SP","P_CRASH1","P_CRASH2","P_CRASH3","PCRASH1_IM",
 "PCRASH4","PCRASH5","ACC_TYPE","ACC_CONFIG","IMPACT1","IMPACT1_IM","ROLLOVER","ROLINLOC","DEFORMED","TOWED","FIRE_EXP",
 "M_HARM","VEVENT_IM","DR_PRES","DEATHS","MAX_VSEV","MXVSEV_IM","NUM_INJV","NUMINJ_IM","VEH_ALCH","V_ALCH_IM","SPEEDREL",
 "UNDERIDE","UNDEROVERRIDE","J_KNIFE","V_CONFIG","HARM_EV","MAN_COLL","VE_FORMS"]
rows=[]
for src in ["FARS","CRSS"]:
    for y in range(2016,2025):
        df = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet")
        have = df.collect_schema().names()
        cols = [v for v in VARS if v in have]
        d = df.select(cols).collect()
        n = d.height
        for v in cols:
            vc = d.group_by(v).len().rename({v:"code","len":"n"}).with_columns(pl.col("code").cast(pl.Utf8))
            for code,cnt in vc.iter_rows():
                rows.append((src,y,v,code,cnt,n))
out = pl.DataFrame(rows, schema=["source","year","var","code","n","N"],orient="row")
cb = pl.read_csv("outputs/audit/codebook.csv", infer_schema_length=0).filter(pl.col("table")=="vehicle").select(
    pl.col("source"),pl.col("year").cast(pl.Int64),pl.col("variable").alias("var"),pl.col("code"),pl.col("label"))
out = out.join(cb, on=["source","year","var","code"], how="left")
out.write_csv(f"{OUT}/veh_dist.csv")
print(out.height)
