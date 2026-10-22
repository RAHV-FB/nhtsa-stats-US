"""DRUGRES 4-digit scheme (2022+) band summary and 3-digit (2016-2021) band summary with 'type unknown' anchor labels."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_rows(400); pl.Config.set_fmt_str_lengths(70); pl.Config.set_tbl_width_chars(250)
d = load_table("FARS","drugs",years=None,columns=["DRUGRES","DRUGRESNAME"]).unique()  # dedupe irrelevant for labels
g = d.group_by(["YEAR","DRUGRES","DRUGRESNAME"]).len()
new = g.filter((pl.col("YEAR")>=2022)&(pl.col("DRUGRES")>=1000)&(pl.col("DRUGRES")<9995)).with_columns((pl.col("DRUGRES")//1000).alias("band"))
for b in sorted(new["band"].unique().to_list()):
    x = new.filter(pl.col("band")==b).group_by(["DRUGRES"]).agg(pl.col("DRUGRESNAME").unique().alias("lab"), pl.col("len").sum()).sort("len", descending=True)
    anchor = x.filter(pl.col("DRUGRES")%1000>=990)
    print(f"band {b}xxx: {x.height} codes, n={x['len'].sum()}; anchors: {[(r[0], r[1]) for r in anchor.select('DRUGRES','lab').iter_rows()]}")
    print("   top:", [(r[0], r[1][0][:35], r[2]) for r in x.head(6).iter_rows()])
old = g.filter((pl.col("YEAR")<=2021)&(pl.col("DRUGRES")>=100)&(pl.col("DRUGRES")<=995)).with_columns((pl.col("DRUGRES")//100).alias("band"))
for b in sorted(old["band"].unique().to_list()):
    x = old.filter(pl.col("band")==b).group_by(["DRUGRES"]).agg(pl.col("DRUGRESNAME").unique().alias("lab"), pl.col("len").sum()).sort("len", descending=True)
    anchor = x.filter(pl.col("DRUGRES")%100>=95)
    print(f"band {b}xx: {x.height} codes, n={x['len'].sum()}; anchors: {[(r[0], r[1]) for r in anchor.select('DRUGRES','lab').iter_rows()]}")
    print("   top:", [(r[0], r[1][0][:35], r[2]) for r in x.head(6).iter_rows()])
# anything in 2022+ between 2 and 999 ?
print(g.filter((pl.col("YEAR")>=2022)&(pl.col("DRUGRES")>1)&(pl.col("DRUGRES")<1000)))
print(g.filter((pl.col("YEAR")<=2021)&(pl.col("DRUGRES")>999)))
