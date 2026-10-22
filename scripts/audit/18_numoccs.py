import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(250)
for src in ["FARS","CRSS"]:
    d = pl.concat([pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(pl.lit(y).alias("YEAR"),"HIT_RUN","NUMOCCS").collect() for y in (2016,2017,2018,2024)])
    hr = d.filter(pl.col("HIT_RUN")==1)
    print(src, "hit-run vehicles NUMOCCS dist (top 4) by year:")
    for y in (2016,2017,2018,2024):
        x = hr.filter(pl.col("YEAR")==y).group_by("NUMOCCS").len().with_columns((100*pl.col("len")/pl.col("len").sum()).round(1).alias("p")).sort("len",descending=True).head(4)
        print("  ", y, x.rows())
    print(src, "NUMOCCS=99 share among non-hit-run:", d.filter(pl.col("HIT_RUN")!=1).group_by("YEAR").agg((pl.col("NUMOCCS")==99).mean().mul(100).round(2)).sort("YEAR").rows())
