import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300)
frames=[]
for src in ["FARS","CRSS"]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    for y in range(2016,2025):
        v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+["ROLLOVER","SPEEDREL","MOD_YEAR","IMPACT1","BUS_USE","BODY_TYP","DEFORMED"]+(["STATE"] if src=="FARS" else [])).collect()
        a = pl.scan_parquet(f"data/interim/{src}/veh_aux/{y}.parquet").select(key+["A_VROLL","A_SPVEH","A_MOD_YR","A_IMP1"]).collect()
        frames.append(v.join(a, on=key, how="left").with_columns(pl.lit(src).alias("source"), pl.lit(y).alias("year")).drop(key))
d = pl.concat(frames, how="diagonal")
for a,b in [("A_VROLL","ROLLOVER"),("A_SPVEH","SPEEDREL"),("A_IMP1","IMPACT1")]:
    t = d.group_by(a,b).len().pivot(on=b, index=a, values="len").sort(a)
    print(f"== {a} x {b} (pooled)"); print(t.select([a]+sorted([c for c in t.columns if c!=a], key=int)))
print("== A_MOD_YR vs MOD_YEAR: distinct A_MOD_YR values and relation")
print(d.group_by("source").agg(pl.col("A_MOD_YR").min().alias("min"), pl.col("A_MOD_YR").max().alias("max"), pl.col("A_MOD_YR").n_unique()))
print(d.with_columns(pl.when(pl.col("MOD_YEAR")>=9998).then(pl.lit("unk")).otherwise((pl.col("year")-pl.col("MOD_YEAR")).clip(-2,40).cast(pl.Utf8)).alias("age")).group_by("A_MOD_YR").agg(pl.len(), pl.col("age").unique().sort().head(12)).sort("A_MOD_YR"))
print("== BUS_USE=99 by body group & year (shares among non-bus BODY_TYP)")
print(d.with_columns(pl.col("BODY_TYP").is_in([50,51,52,55,58,59]).alias("isbus")).group_by("source","year","isbus").agg(pl.len(), (pl.col("BUS_USE")==99).mean().mul(100).round(2).alias("pct99"), (pl.col("BUS_USE")==0).mean().mul(100).round(2).alias("pct0")).pivot(on="isbus", index=["source","year"], values=["pct99","pct0"]).sort("source","year"))
print(d.filter((pl.col("BUS_USE")==99)&(pl.col("year")>=2019)).group_by("BODY_TYP").len().sort("len",descending=True).head(8))
print("== FARS DEFORMED=8 by state, 2018-2021 (top)")
f = d.filter((pl.col("source")=="FARS")&pl.col("year").is_between(2018,2022))
print(f.group_by("year","STATE").agg((pl.col("DEFORMED")==8).mean().mul(100).round(1).alias("p8")).pivot(on="year", index="STATE", values="p8").sort("2021",descending=True).head(8))
