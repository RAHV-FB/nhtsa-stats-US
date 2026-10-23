"""FARS crash-level: A_POSBAC and DRUNK_DR derivations; MIACC/MIDRVACC structure vs persons."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
OUT = "outputs/cache/audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_person.parquet")
print("A_ALCTES=1 with ALC_RES 1-79:", df.filter((pl.col("A_ALCTES")==1)&pl.col("ALC_RES").is_between(1,79))["ALC_RES"].value_counts().sort("ALC_RES"))
print("A_ALCTES=2 with ALC_RES 1-9:", df.filter((pl.col("A_ALCTES")==2)&pl.col("ALC_RES").is_between(1,9)).height)
d = df.filter(pl.col("PER_TYP")==1)
c = d.group_by(["YEAR","ST_CASE"]).agg(
    pl.col("ALC_RES").is_between(10,940).any().alias("any_pos01"),
    pl.col("ALC_RES").is_between(1,940).any().alias("any_pos001"),
    (pl.col("ALC_RES")==998).any().alias("any998"),
    (pl.col("ALC_RES").is_between(0,9)).all().alias("all_zero_meas"),
    pl.col("DR_DRINK").sum().alias("n_drdrink"),
    pl.col("A_POSBAC").first(), pl.col("DRUNK_DR").first(), pl.len().alias("n_drv"))
c = c.with_columns(pl.when(pl.col("any_pos01")|pl.col("any998")).then(1).when(pl.col("all_zero_meas")).then(2).otherwise(3).alias("hyp"))
print("A_POSBAC vs hypothesis (1=any driver BAC>=.01 or 998; 2=all drivers tested with BAC<.01; 3=else):")
print(c.group_by(["A_POSBAC","hyp"]).len().pivot(on="hyp", index="A_POSBAC", values="len", sort_columns=True).sort("A_POSBAC"))
print("DRUNK_DR vs sum(DR_DRINK) among drivers (2016-2020):")
cc = c.filter(pl.col("YEAR")<=2020)
print(cc.group_by(["DRUNK_DR","n_drdrink"]).len().pivot(on="n_drdrink", index="DRUNK_DR", values="len", sort_columns=True).sort("DRUNK_DR"))
# crashes with no driver records (all-nonmotorist? or crash with no driver person)
a = load_table("FARS","accident",years=None,columns=["ST_CASE"])
print("crashes total", a.height, "crashes with >=1 PER_TYP=1 person:", c.height)
# MIACC/MIDRVACC
ma = load_table("FARS","miacc",years=None,columns=["ST_CASE"]+[f"A{i}" for i in range(1,11)])
md = load_table("FARS","midrvacc",years=None,columns=["ST_CASE"]+[f"A{i}" for i in range(1,11)])
mp = df.filter(pl.col("in_miper")==1)
mx_all = mp.group_by(["YEAR","ST_CASE"]).agg([pl.col(f"P{i}").max().alias(f"M{i}") for i in range(1,11)])
mx_drv = mp.filter(pl.col("PER_TYP")==1).group_by(["YEAR","ST_CASE"]).agg([pl.col(f"P{i}").max().alias(f"D{i}") for i in range(1,11)])
j = ma.join(mx_all, on=["YEAR","ST_CASE"], how="left")
print("MIACC: rows", ma.height, "crashes with miper rows", mx_all.height)
print("MIACC A_i == max over miper persons P_i:", [round(j.select((pl.col(f"A{i}")==pl.col(f"M{i}")).mean()).item(),5) for i in range(1,11)])
print("MIACC rows w/o any miper person:", j.filter(pl.col("M1").is_null()).height, j.filter(pl.col("M1").is_null()).select([f"A{i}" for i in range(1,4)]).unique().head())
jd = md.join(mx_drv, on=["YEAR","ST_CASE"], how="left")
print("MIDRVACC: rows", md.height, "crashes with driver in miper", mx_drv.height, "unmatched", jd.filter(pl.col("D1").is_null()).height)
print("MIDRVACC A_i == max over drivers P_i:", [round(jd.select((pl.col(f"A{i}")==pl.col(f"D{i}")).mean()).item(),5) for i in range(1,11)])
print("crashes in miacc not in midrvacc:", ma.join(md, on=["YEAR","ST_CASE"], how="anti").height)
# mismatches detail
bad = jd.filter(pl.col("A1")!=pl.col("D1"))
print("MIDRVACC mismatches A1 vs D1:", bad.height); print(bad.head(5))
bad2 = j.filter(pl.col("A1")!=pl.col("M1"))
print("MIACC mismatches:", bad2.height); print(bad2.head(5))
