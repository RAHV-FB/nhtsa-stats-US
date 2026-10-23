"""FARS drugs.DRUGRES and person DRUGRES1-3 (2016-17): code ranges with labels and counts per year."""
import polars as pl, re
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_rows(400); pl.Config.set_fmt_str_lengths(90); pl.Config.set_tbl_width_chars(250)
d = load_table("FARS","drugs",years=None,columns=["DRUGRES","DRUGRESNAME"])
g = d.group_by(["YEAR","DRUGRES","DRUGRESNAME"]).len()
# codes outside 100-995 band, show all
print("### special (not 100-995)")
sp = g.filter((pl.col("DRUGRES")<100)|(pl.col("DRUGRES")>995))
print(sp.pivot(on="YEAR", index=["DRUGRES","DRUGRESNAME"], values="len", sort_columns=True).sort("DRUGRES"))
# hundreds band: count codes and total and sample labels
g2 = g.filter((pl.col("DRUGRES")>=100)&(pl.col("DRUGRES")<=995)).with_columns((pl.col("DRUGRES")//100).alias("band"))
print(g2.group_by(["band","YEAR"]).agg(pl.col("len").sum()).pivot(on="YEAR", index="band", values="len", sort_columns=True).sort("band"))
# band "xx95/xx96" codes = other in class?
for b in range(1,10):
    x = g2.filter(pl.col("band")==b).group_by(["DRUGRES","DRUGRESNAME"]).agg(pl.col("len").sum(), pl.col("YEAR").min().alias("y0"), pl.col("YEAR").max().alias("y1")).sort("len", descending=True)
    print(f"--- band {b}: {x['DRUGRES'].n_unique()} codes; top 8 / and codes ending 95-99:")
    print(x.head(8))
    print(x.filter(pl.col("DRUGRES")%100>=95))
p = load_table("FARS","person",years=[2016,2017],columns=["DRUGRES1","DRUGRES1NAME"])
gp = p.group_by(["YEAR","DRUGRES1","DRUGRES1NAME"]).len()
print("### person DRUGRES1 special")
print(gp.filter((pl.col("DRUGRES1")<100)|(pl.col("DRUGRES1")>995)).sort(["DRUGRES1","YEAR"]))
gp2 = gp.filter((pl.col("DRUGRES1")>=100)&(pl.col("DRUGRES1")<=995)).with_columns((pl.col("DRUGRES1")//100).alias("band"))
print(gp2.group_by(["band","YEAR"]).agg(pl.col("len").sum(), pl.col("DRUGRES1NAME").first()).sort(["band","YEAR"]))
