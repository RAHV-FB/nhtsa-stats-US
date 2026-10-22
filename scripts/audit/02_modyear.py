import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300)
d = pl.read_csv("/tmp/nhtsa-audit/out/veh_dist.csv", infer_schema_length=0).with_columns(pl.col("n").cast(pl.Int64), pl.col("N").cast(pl.Int64), pl.col("year").cast(pl.Int64), pl.col("code").cast(pl.Int64,strict=False).alias("ci"))
for v in ["MOD_YEAR","MDLYR_IM"]:
    x = d.filter(pl.col("var")==v)
    print(v)
    print(x.filter(pl.col("ci")>=9000).select("source","year","code","label","n","N").with_columns((100*pl.col("n")/pl.col("N")).round(2).alias("pct")).sort("source","year","code"))
    # age stats among valid
    s = x.filter(pl.col("ci")<9000).with_columns((pl.col("year")-pl.col("ci")).alias("age"))
    print(s.group_by("source","year").agg(pl.col("ci").min().alias("min_my"), pl.col("ci").max().alias("max_my"),
        ((pl.col("age")*pl.col("n")).sum()/pl.col("n").sum()).round(2).alias("mean_age"),
        (pl.col("n").filter(pl.col("age")<0).sum()/pl.col("n").sum()*100).round(2).alias("pct_age_neg"),
        (pl.col("n").filter(pl.col("age")>=30).sum()/pl.col("n").sum()*100).round(2).alias("pct_age30p")).sort("source","year"))
    print(x.filter(pl.col("label").is_not_null() & (pl.col("ci")<9000)).group_by("source","year").agg(pl.col("label").first(), pl.col("code").first()).sort("source","year").head(3))
