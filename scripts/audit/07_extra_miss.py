import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300)
OUT="/tmp/nhtsa-audit/out"
d = pl.read_csv(f"{OUT}/diffmiss.csv")
# severity x year for key vars
for src, groups, col in [("CRSS",["K","A","O"],"pct_w"),("FARS",["veh_death","no_veh_death"],"pct_unw")]:
    x = d.filter((pl.col("source")==src)&(pl.col("grouping")=="sev")&pl.col("group").is_in(groups)&pl.col("var").is_in(["VSPD_LIM","VSURCOND","VTRAFCON","TRAV_SP","MOD_YEAR","VTRAFWAY","VEH_ALCH","PCRASH4"]))
    x = x.with_columns((pl.col("var")+"|"+pl.col("group")).alias("vg"))
    print(f"== {src} {col} by severity x year"); print(x.pivot(on="year", index="vg", values=col).sort("vg"))
# missingness by HIT_RUN
for src in ["FARS","CRSS"]:
    df = pl.concat([pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(pl.lit(y).alias("YEAR"),"HIT_RUN","BODY_TYP","MOD_YEAR","NUMOCCS","TRAV_SP","VSPD_LIM").collect() for y in range(2016,2025)])
    print(src, df.group_by("HIT_RUN").agg(pl.len(), (pl.col("BODY_TYP").is_in([98,99]).mean()*100).round(2).alias("body_miss"),
        (pl.col("MOD_YEAR").is_in([9998,9999]).mean()*100).round(2).alias("my_miss"), (pl.col("NUMOCCS")==99).mean().mul(100).round(2).alias("nocc_miss"),
        (pl.col("TRAV_SP").is_in([998,999]).mean()*100).round(2).alias("sp_miss"), (pl.col("VSPD_LIM").is_in([98,99]).mean()*100).round(2).alias("lim_miss")).sort("HIT_RUN"))
    # share of all body/my missing that is hit-run
    print(src, "share of BODY_TYP 98/99 among hit-run vehicles:", round(df.filter(pl.col("BODY_TYP").is_in([98,99]))["HIT_RUN"].eq(1).mean()*100,2),
          "MOD_YEAR 9998/9999:", round(df.filter(pl.col("MOD_YEAR").is_in([9998,9999]))["HIT_RUN"].eq(1).mean()*100,2))
# FARS VTRAFCON not reported by state 2016 vs 2024
f = pl.concat([pl.scan_parquet(f"data/interim/FARS/vehicle/{y}.parquet").select(pl.lit(y).alias("YEAR"),"STATE","VTRAFCON").collect() for y in (2016,2019,2021,2024)])
s = f.group_by("YEAR","STATE").agg(((pl.col("VTRAFCON")==97).mean()*100).round(1).alias("p97"), pl.len().alias("n")).pivot(on="YEAR", index="STATE", values="p97").sort("2024", descending=True)
print("FARS VTRAFCON=97 % by STATE"); print(s.head(25))
print("states with >50% in 2024:", s.filter(pl.col("2024")>50).height, " states with 0 in 2024:", s.filter(pl.col("2024")==0).height, "of", s.height)
