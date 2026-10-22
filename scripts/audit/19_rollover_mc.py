import polars as pl
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(250)
for src in ["FARS","CRSS"]:
    d = pl.concat([pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(pl.lit(y).alias("YEAR"),"BODY_TYP","ROLLOVER","TOWED","DEFORMED").collect() for y in range(2016,2025)])
    mc = d.filter(pl.col("BODY_TYP").is_between(80,89))
    print(src, "motorcycles ROLLOVER distribution by year (%):")
    print(mc.group_by("YEAR","ROLLOVER").len().with_columns((100*pl.col("len")/pl.col("len").sum().over("YEAR")).round(2).alias("p")).pivot(on="ROLLOVER", index="YEAR", values="p").sort("YEAR"))
    nm = d.filter(~pl.col("BODY_TYP").is_between(80,89))
    print(src, "non-MC rollover (codes 1,2,3,9) % by year:", nm.group_by("YEAR").agg(pl.col("ROLLOVER").is_in([1,2,3,9]).mean().mul(100).round(2)).sort("YEAR").rows())
    print(src, "towed (2,3,6,7) % / not towed (5) / missing (8,9) by year:", d.group_by("YEAR").agg(pl.col("TOWED").is_in([2,3,6,7]).mean().mul(100).round(2).alias("towed"), (pl.col("TOWED")==5).mean().mul(100).round(2).alias("not"), pl.col("TOWED").is_in([8,9]).mean().mul(100).round(2).alias("miss")).sort("YEAR").rows())
    print(src, "DEFORMED: disabling(6)% / extent-unknown-or-NR (7,8)% / unknown(9)%:", d.group_by("YEAR").agg((pl.col("DEFORMED")==6).mean().mul(100).round(2), pl.col("DEFORMED").is_in([7,8]).mean().mul(100).round(2).alias("x"), (pl.col("DEFORMED")==9).mean().mul(100).round(2).alias("u")).sort("YEAR").rows())
