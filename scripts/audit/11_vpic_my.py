import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300); pl.Config.set_fmt_str_lengths(40)
F = ["ELECTRONICSTABILITYCONTROL","ANTILOCKBRAKESYSTEM","CRASHIMMINENTBRAKING","FORWARDCOLLISIONWARNING","LANEDEPARTUREWARNING","BACKUPCAMERA","BLINDSPOTWARNING","AIRBAGLOCSIDE","CURBWEIGHTLB","GROSSVEHICLEWEIGHTRATINGFROM"]
frames=[]
for src in ["FARS","CRSS"]:
    for y in range(2016,2025):
        p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(["MODELYEAR","VEHICLETYPE","VINDECODEDON"]+F).collect()
        p = p.with_columns([pl.col(c).cast(pl.Utf8) for c in F+["VINDECODEDON"]]).with_columns(pl.lit(src).alias("source"), pl.lit(y).alias("year"))
        frames.append(p)
p = pl.concat(frames)
lv = p.filter(pl.col("VEHICLETYPE").is_in(["PASSENGER CAR","MULTIPURPOSE PASSENGER VEHICLE (MPV)","TRUCK"]))
lv = lv.with_columns(pl.when(pl.col("MODELYEAR")<2000).then(pl.lit("<2000")).when(pl.col("MODELYEAR")<2006).then(pl.lit("2000-05")).when(pl.col("MODELYEAR")<2010).then(pl.lit("2006-09"))
     .when(pl.col("MODELYEAR")<2013).then(pl.lit("2010-12")).when(pl.col("MODELYEAR")<2016).then(pl.lit("2013-15")).when(pl.col("MODELYEAR")<2019).then(pl.lit("2016-18"))
     .when(pl.col("MODELYEAR")<2022).then(pl.lit("2019-21")).otherwise(pl.lit("2022+")).alias("myb"))
print("== Light vehicles (VEHICLETYPE car/MPV/truck), pooled FARS+CRSS 2016-2024: % by value, by model-year band")
for f in F[:8]:
    t = lv.group_by("myb").agg(pl.len().alias("n"), (pl.col(f)=="Standard").mean().mul(100).round(1).alias("Std"), (pl.col(f)=="Optional").mean().mul(100).round(1).alias("Opt"),
        (pl.col(f)=="Not Available").mean().mul(100).round(2).alias("NotAvail"), pl.col(f).is_null().mean().mul(100).round(1).alias("null")).sort("myb")
    print("###", f); print(t)
print("### CURBWEIGHTLB non-null % / GVWR-from non-null %, by myb")
print(lv.group_by("myb").agg(pl.len(), pl.col("CURBWEIGHTLB").is_not_null().mean().mul(100).round(2).alias("curb_nonnull"), pl.col("GROSSVEHICLEWEIGHTRATINGFROM").is_not_null().mean().mul(100).round(2).alias("gvwr_nonnull")).sort("myb"))
print(lv.group_by("GROSSVEHICLEWEIGHTRATINGFROM").len().sort("len",descending=True).head(20))
# decode vintage: MY 2013-2015 light vehicles, ESC Standard % by data year and source
print("== MY2013-15 light vehicles: % ESC Standard and % BACKUPCAMERA Standard by data year (decode vintage effect)")
print(lv.filter(pl.col("myb")=="2013-15").group_by("source","year").agg(pl.len(), (pl.col("ELECTRONICSTABILITYCONTROL")=="Standard").mean().mul(100).round(1).alias("esc_std"),
      (pl.col("ANTILOCKBRAKESYSTEM")=="Standard").mean().mul(100).round(1).alias("abs_std"),(pl.col("BACKUPCAMERA")=="Standard").mean().mul(100).round(1).alias("cam_std"),
      (pl.col("CRASHIMMINENTBRAKING")=="Standard").mean().mul(100).round(1).alias("aeb_std")).sort("source","year"))
print("== VINDECODEDON sample values per source-year")
print(p.group_by("source","year").agg(pl.col("VINDECODEDON").n_unique().alias("n_distinct"), pl.col("VINDECODEDON").min().alias("min"), pl.col("VINDECODEDON").max().alias("max")).sort("source","year"))
