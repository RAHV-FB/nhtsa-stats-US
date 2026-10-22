import polars as pl
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300)
rows=[]
for src in ["FARS","CRSS"]:
    key = ["ST_CASE","VEH_NO"] if src=="FARS" else ["CASENUM","VEH_NO"]
    for y in range(2016,2025):
        cols = ["BODY_TYP"] + (["VPICBODYCLASS"] if y>=2020 else [])
        v = pl.scan_parquet(f"data/interim/{src}/vehicle/{y}.parquet").select(key+cols).collect()
        p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(key+["BODYCLASS","BODYCLASSID"]).collect()
        j = v.join(p, on=key, how="left")
        r = dict(source=src, year=y,
            st_wagon_n=j.filter(pl.col("BODY_TYP")==6).height,
            st_wagon_vpic_suv_pct=round(100*j.filter(pl.col("BODY_TYP")==6)["BODYCLASSID"].is_in([7,8]).mean(),1),
            hatch5_vpic_suv_pct=round(100*j.filter(pl.col("BODY_TYP")==5)["BODYCLASSID"].is_in([7,8]).mean(),1),
            sedan4_vpic_suv_pct=round(100*j.filter(pl.col("BODY_TYP")==4)["BODYCLASSID"].is_in([7,8]).mean(),2),
            util14_vpic_suv_pct=round(100*j.filter(pl.col("BODY_TYP")==14)["BODYCLASSID"].is_in([7,8]).mean(),1),
            bodyclassid_null_pct=round(100*j["BODYCLASSID"].is_null().mean(),2))
        if y>=2020:
            jj = j.filter(pl.col("BODYCLASSID").is_not_null())
            r["vpicbodyclass_eq_bodyclassid_pct"] = round(100*(jj["VPICBODYCLASS"]==jj["BODYCLASSID"]).mean(),2)
            r["vpicbody_when_no_vpicrow"] = str(j.filter(pl.col("BODYCLASSID").is_null()).group_by("VPICBODYCLASS").len().sort("len",descending=True).head(3).rows())
        rows.append(r)
print(pl.DataFrame(rows))
