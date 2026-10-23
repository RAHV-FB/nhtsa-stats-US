import polars as pl
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(250)
for src,y in [("CRSS",2021),("CRSS",2022),("CRSS",2023),("FARS",2022)]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+["VPICBODYCLASS","BODY_TYP"]).collect()
    p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(key+["BODYCLASSID","VINDECODEERROR"]).collect()
    j = v.join(p, on=key, how="left")
    mm = j.filter(pl.col("BODYCLASSID").is_not_null() & (pl.col("VPICBODYCLASS")!=pl.col("BODYCLASSID")))
    print(src, y, "mismatch n", mm.height, "top pairs (VPICBODYCLASS, BODYCLASSID, VINDECODEERROR):", mm.group_by("VPICBODYCLASS","BODYCLASSID","VINDECODEERROR").len().sort("len",descending=True).head(5).rows())
    print("   VINDECODEERROR among VPICBODYCLASS==999 with vpic row:", j.filter((pl.col("VPICBODYCLASS")==999)&pl.col("BODYCLASSID").is_not_null()).group_by("VINDECODEERROR").len().sort("len",descending=True).head(4).rows(),
          " | VPIC 999 & no vpic row:", j.filter((pl.col("VPICBODYCLASS")==999)&pl.col("BODYCLASSID").is_null()).height)
    print("   VINDECODEERROR dist:", p.group_by("VINDECODEERROR").len().sort("len",descending=True).head(4).rows())
