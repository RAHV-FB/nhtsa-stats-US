import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(320)
frames=[]
for src in ["FARS","CRSS"]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    for y in range(2016,2025):
        cols = ["BODY_TYP"] + (["VPICBODYCLASS"] if y>=2020 else [])
        v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+cols).collect()
        a = pl.scan_parquet(f"data/interim/{src}/veh_aux/{y}.parquet").select(key+["A_BODY"]).collect()
        frames.append(v.join(a, on=key, how="left").with_columns(pl.lit(src).alias("source"), pl.lit(y).alias("year")).drop(key))
d = pl.concat(frames, how="diagonal")
print("== car codes (1-13,17): A_BODY distribution per BODY_TYP (pooled)")
x = d.filter(pl.col("BODY_TYP").is_between(1,17)).group_by("BODY_TYP","A_BODY").len().pivot(on="A_BODY", index="BODY_TYP", values="len").sort("BODY_TYP")
print(x.select(["BODY_TYP"]+sorted([c for c in x.columns if c!="BODY_TYP"], key=int)))
print("== BODY_TYP 6 & 9: A_BODY=3 share by source-year")
print(d.filter(pl.col("BODY_TYP").is_in([4,5,6,9])).group_by("source","year","BODY_TYP").agg((pl.col("A_BODY")==3).mean().mul(100).round(1).alias("pct_A3"), (pl.col("A_BODY")==9).mean().mul(100).round(1).alias("pct_A9")).pivot(on="BODY_TYP", index=["source","year"], values=["pct_A3","pct_A9"]).sort("source","year"))
print("== 2020+: BODY_TYP car codes x VPICBODYCLASS 7 (SUV/MPV) / 8 (CUV) share")
print(d.filter((pl.col("year")>=2020)&pl.col("BODY_TYP").is_between(1,17)).group_by("BODY_TYP").agg(pl.len(), pl.col("VPICBODYCLASS").is_in([7,8]).mean().mul(100).round(1).alias("pct_vpic_suv"), (pl.col("A_BODY")==3).mean().mul(100).round(1).alias("pct_A3")).sort("BODY_TYP"))
print("== A_BODY x BODY_TYP for 49/79/98/99/40-48/73")
print(d.filter(pl.col("BODY_TYP").is_in([40,42,45,48,49,73,79,98,99])).group_by("BODY_TYP","A_BODY").len().pivot(on="A_BODY", index="BODY_TYP", values="len").sort("BODY_TYP"))
print("== 2020+: BODY_TYP 49 / 98 / 99 / 79 with an informative VPICBODYCLASS (not 998/999):")
print(d.filter((pl.col("year")>=2020)&pl.col("BODY_TYP").is_in([49,79,98,99])).group_by("source","BODY_TYP").agg(pl.len(), (~pl.col("VPICBODYCLASS").is_in([998,999])).mean().mul(100).round(1).alias("pct_vpic_informative")).sort("source","BODY_TYP"))
