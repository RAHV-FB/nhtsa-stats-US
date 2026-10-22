"""Missing/unknown rates per source-year and by severity group.
FARS: vehicle-level DEATHS>0 vs 0.  CRSS: MAX_VSEV (K,A,B,C,O,Unk) and crash MAX_SEV; unweighted and WEIGHT-weighted."""
import polars as pl
OUT="/tmp/nhtsa-audit/out"
MISS = {"BODY_TYP":[98,99], "BODY_TYP_CAT_UNK":None, "MOD_YEAR":[9998,9999], "NUMOCCS":[97,98,99], "HIT_RUN":[9], "TOW_VEH":[9],
 "SPEC_USE":[98,99], "EMER_USE":[8,9], "BUS_USE":[98,99], "VSPD_LIM":[98,99], "VTRAFWAY":[8,9], "VNUM_LAN":[8,9], "VALIGN":[8,9],
 "VPROFILE":[8,9], "VPAVETYP":[8,9], "VSURCOND":[98,99], "VTRAFCON":[97,99], "VTCONT_F":[8,9], "TRAV_SP":[998,999],
 "P_CRASH1":[99], "P_CRASH2":[99], "P_CRASH3":[99], "PCRASH4":[9], "PCRASH5":[9], "ACC_TYPE":[99], "IMPACT1":[98,99],
 "DEFORMED":[8,9], "DEFORMED_EXT":[7,8,9], "TOWED":[8,9], "M_HARM":[98,99], "SPEEDREL":[9], "VEH_ALCH":[9], "GVWR_FROM":[98,99],
 "GVWR":[8,9], "VPICBODYCLASS":[998,999], "UNDEROVERRIDE":[8,9]}
BASE = sorted({k.split("_EXT")[0] for k in MISS if k!="BODY_TYP_CAT_UNK"} - {"DEFORMED_EXT"})
res=[]
for src in ["FARS","CRSS"]:
    for y in range(2016,2025):
        lf = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet")
        have = lf.collect_schema().names()
        cols = [c for c in BASE if c in have]
        extra = ["DEATHS"] if src=="FARS" else ["MAX_VSEV","WEIGHT","CASENUM"]
        df = lf.select(cols+extra).collect()
        if src=="CRSS":
            acc = pl.scan_parquet(f"data/interim/CRSS/accident/{y}.parquet").select("CASENUM","MAX_SEV").collect()
            df = df.join(acc, on="CASENUM", how="left")
            sevmap = {0:"O",1:"C",2:"B",3:"A",4:"K",5:"Inj_unk",6:"Died_prior",8:"No_person",9:"Unknown"}
            df = df.with_columns(pl.col("MAX_VSEV").replace_strict(sevmap, default="?").alias("sev"),
                                 pl.col("MAX_SEV").replace_strict(sevmap, default="?").alias("crash_sev"))
        else:
            df = df.with_columns(pl.when(pl.col("DEATHS")>0).then(pl.lit("veh_death")).otherwise(pl.lit("no_veh_death")).alias("sev"),
                                 pl.lit("fatal_crash").alias("crash_sev"), pl.lit(1.0).alias("WEIGHT"))
        exprs=[]
        for v,codes in MISS.items():
            if v=="BODY_TYP_CAT_UNK":
                if "BODY_TYP" in cols: exprs.append(pl.col("BODY_TYP").is_in([49,79,97,98,99]).alias(v))
                continue
            base = v.replace("_EXT","")
            if base in cols: exprs.append(pl.col(base).is_in(codes).alias(v))
        m = df.select(["sev","crash_sev","WEIGHT"]+exprs)
        vs = [c for c in m.columns if c not in ("sev","crash_sev","WEIGHT")]
        for grpcol in ["ALL","sev","crash_sev"]:
            g = m.with_columns(pl.lit("ALL").alias("ALL")) if grpcol=="ALL" else m
            agg = g.group_by(grpcol).agg([pl.len().alias("n")]+[pl.col(v).mean().alias(f"{v}__u") for v in vs]+
                                          [((pl.col(v).cast(pl.Float64)*pl.col("WEIGHT")).sum()/pl.col("WEIGHT").sum()).alias(f"{v}__w") for v in vs])
            for r in agg.iter_rows(named=True):
                for v in vs:
                    res.append((src,y,grpcol,r[grpcol],r["n"],v,round(100*r[f"{v}__u"],3),round(100*r[f"{v}__w"],3)))
out = pl.DataFrame(res, schema=["source","year","grouping","group","n","var","pct_unw","pct_w"], orient="row")
out.write_csv(f"{OUT}/diffmiss.csv")
print(out.height)
