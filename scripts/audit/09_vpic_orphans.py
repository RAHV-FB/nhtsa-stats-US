import polars as pl
pl.Config.set_tbl_rows(50); pl.Config.set_tbl_width_chars(250)
for src in ["FARS","CRSS"]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    for y in (2016,2020,2024):
        v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+["VIN"]).collect()
        p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(key).collect()
        pw = pl.scan_parquet(f"data/interim/{src}/parkwork/{y}.parquet")
        pwk = pw.collect_schema().names()
        pkey = [c for c in key if c in pwk]
        vn = "VEH_NO" if "VEH_NO" in pwk else None
        pwd = pw.select([c for c in pwk if c in key or c in ("PVEH_NO",)]).collect()
        if "VEH_NO" not in pwd.columns and "PVEH_NO" in pwd.columns: pwd = pwd.rename({"PVEH_NO":"VEH_NO"})
        orph = p.join(v.select(key), on=key, how="anti")
        inpw = orph.join(pwd.select(key).unique(), on=key, how="semi").height
        print(src, y, "orphans", orph.height, "of which in parkwork", inpw, "parkwork rows", pwd.height, "parkwork cols with key:", [c for c in pwk if 'VEH' in c][:5])
        print("   VIN length distribution:", v.with_columns(pl.col("VIN").cast(pl.Utf8).str.len_chars().alias("L")).group_by("L").len().sort("len",descending=True).head(4).rows(), "sample", v["VIN"].head(3).to_list())
