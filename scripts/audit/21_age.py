import polars as pl
for src in ["FARS","CRSS"]:
    d = pl.concat([pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(pl.lit(y).alias("YEAR"),"MOD_YEAR").collect() for y in range(2016,2025)])
    k = d.filter(pl.col("MOD_YEAR")<9000).with_columns((pl.col("YEAR")-pl.col("MOD_YEAR")).alias("age"))
    print(src, "n_known", k.height, "age<=-2:", k.filter(pl.col("age")<=-2).height, "age==-1:", k.filter(pl.col("age")==-1).height, "age>=30:", k.filter(pl.col("age")>=30).height,
          "median age by year:", k.group_by("YEAR").agg(pl.col("age").median()).sort("YEAR")["age"].to_list(),
          "p90:", k.group_by("YEAR").agg(pl.col("age").quantile(0.9)).sort("YEAR")["age"].to_list())
    print("   age<=-2 examples:", k.filter(pl.col("age")<=-2).group_by("YEAR","MOD_YEAR").len().sort("YEAR").rows())
