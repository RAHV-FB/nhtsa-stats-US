import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300); pl.Config.set_fmt_str_lengths(70)
d = pl.read_csv("/tmp/nhtsa-audit/out/veh_dist.csv", infer_schema_length=0).with_columns(pl.col("n").cast(pl.Int64), pl.col("N").cast(pl.Int64), pl.col("year").cast(pl.Int64), pl.col("code").cast(pl.Int64,strict=False).alias("ci"))
x = d.filter(pl.col("var")=="TRAV_SP")
# labelled non-numeric-looking labels
lab = x.filter(pl.col("label").is_not_null() & ~pl.col("label").str.contains(r"^\d+ MPH$"))
print(lab.select("source","year","code","label").unique().sort("code","source","year").group_by("code","label").agg(pl.col("source").first(), pl.col("year").min().alias("y0"), pl.col("year").max().alias("y1")).sort("code"))
print(x.filter(pl.col("label").is_not_null()).filter(pl.col("ci").is_in([1,50,96,97,151,152])).select("source","year","code","label").sort("code","source","year"))
w = x.with_columns(pl.when(pl.col("ci")>=997).then(pl.col("code")).when(pl.col("ci")==0).then(pl.lit("0")).when(pl.col("ci")>151).then(pl.lit(">151")).otherwise(pl.lit("1-151")).alias("grp"))
p = w.group_by("source","year","grp").agg((100*pl.col("n").sum()/pl.col("N").first()).round(2).alias("pct")).pivot(on="grp", index=["source","year"], values="pct").sort("source","year")
print(p)
print(x.filter((pl.col("ci")>151)&(pl.col("ci")<997)).select("source","year","code","n").sort("source","year"))
