import polars as pl
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300)
F = ["ELECTRONICSTABILITYCONTROL","CRASHIMMINENTBRAKING","FORWARDCOLLISIONWARNING","BACKUPCAMERA","LANEDEPARTUREWARNING"]
frames=[]
for src in ["FARS","CRSS"]:
    for y in range(2016,2025):
        p = pl.scan_parquet(f"data/interim/{src}/vpicdecode/{y}.parquet").select(["MODELYEAR","VEHICLETYPE","CURBWEIGHTLB"]+F).collect().with_columns(pl.lit(src).alias("source"), pl.lit(y).alias("year"))
        frames.append(p)
p = pl.concat(frames).filter(pl.col("VEHICLETYPE").is_in(["PASSENGER CAR","MULTIPURPOSE PASSENGER VEHICLE (MPV)","TRUCK"]))
def share(f,v): return (pl.col(f).fill_null("<null>")==v).mean().mul(100).round(1)
for myr in [(2016,2018),(2019,2021)]:
    x = p.filter(pl.col("MODELYEAR").is_between(*myr))
    print(f"== light vehicles MY{myr}: share of ALL rows (%) by data year")
    print(x.group_by("source","year").agg(pl.len().alias("n"), *[share(f,"Standard").alias(f[:10]+"_std") for f in F], *[share(f,"<null>").alias(f[:10]+"_null") for f in F[:2]]).sort("source","year"))
print("== whole-file light vehicles: % ESC Standard (of all) / % null by MY single year, FARS 2024 vs FARS 2020")
for src,y in [("FARS",2020),("FARS",2024),("CRSS",2024)]:
    x = p.filter((pl.col("source")==src)&(pl.col("year")==y)&pl.col("MODELYEAR").is_between(2010,2025))
    print(src,y, x.group_by("MODELYEAR").agg(pl.len().alias("n"), share("ELECTRONICSTABILITYCONTROL","Standard").alias("esc"), share("CRASHIMMINENTBRAKING","Standard").alias("aeb"), share("CRASHIMMINENTBRAKING","Optional").alias("aeb_opt"), share("CRASHIMMINENTBRAKING","<null>").alias("aeb_null")).sort("MODELYEAR").rows())
print("CURBWEIGHTLB non-null among light vehicles by source-year:", p.group_by("source","year").agg(pl.col("CURBWEIGHTLB").is_not_null().mean().mul(100).round(2)).sort("source","year").rows())
