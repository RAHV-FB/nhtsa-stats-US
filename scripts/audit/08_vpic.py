"""vpicdecode: join structure with vehicle, coverage, safety-tech field values."""
import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300); pl.Config.set_fmt_str_lengths(60)
OUT="/tmp/nhtsa-audit/out"
rows=[]
for src in ["FARS","CRSS"]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    for y in range(2016,2025):
        v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+["BODY_TYP","MOD_YEAR","HIT_RUN","VIN"]).collect()
        p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(key+["MODELYEAR","VINDECODEERROR","VEHICLETYPE"]).collect()
        assert p.select(key).is_duplicated().sum()==0
        j = v.join(p.with_columns(pl.lit(1).alias("inv")), on=key, how="full", coalesce=True)
        vin_ok = v.filter(~pl.col("VIN").str.contains(r"^[0-9]*$") & (pl.col("VIN").str.len_chars()>=17)).height if v["VIN"].dtype==pl.Utf8 else None
        light = v.filter(pl.col("BODY_TYP").is_between(1,49))
        lj = light.join(p.select(key).with_columns(pl.lit(1).alias("inv")), on=key, how="left")
        newer = v.filter(pl.col("MOD_YEAR").is_between(1981,2030)).join(p.select(key).with_columns(pl.lit(1).alias("inv")), on=key, how="left")
        old = v.filter(pl.col("MOD_YEAR")<1981).join(p.select(key).with_columns(pl.lit(1).alias("inv")), on=key, how="left")
        unk = v.filter(pl.col("MOD_YEAR")>=9998).join(p.select(key).with_columns(pl.lit(1).alias("inv")), on=key, how="left")
        hr = v.filter(pl.col("HIT_RUN")==1).join(p.select(key).with_columns(pl.lit(1).alias("inv")), on=key, how="left")
        mym = v.join(p.select(key+["MODELYEAR"]), on=key, how="inner")
        rows.append(dict(source=src, year=y, n_vehicle=v.height, n_vpic=p.height,
            matched=j.filter(pl.col("inv").is_not_null() & pl.col("BODY_TYP").is_not_null()).height,
            vpic_orphans=j.filter(pl.col("BODY_TYP").is_null()).height,
            pct_veh_with_vpic=round(100*p.height/v.height,2),
            pct_light_with_vpic=round(100*lj["inv"].is_not_null().mean(),2),
            pct_my1981plus_with_vpic=round(100*newer["inv"].is_not_null().mean(),2),
            pct_mypre1981_with_vpic=round(100*old["inv"].is_not_null().mean(),2) if old.height else None,
            pct_myunk_with_vpic=round(100*unk["inv"].is_not_null().mean(),2),
            pct_hitrun_with_vpic=round(100*hr["inv"].is_not_null().mean(),2),
            pct_modelyear_agree=round(100*(mym["MOD_YEAR"]==mym["MODELYEAR"]).mean(),2),
            vin_17char_alpha=vin_ok))
r = pl.DataFrame(rows); print(r); r.write_csv(f"{OUT}/vpic_join.csv")
