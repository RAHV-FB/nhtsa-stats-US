"""CRSS design structure per year: strata, PSUs, nesting, lonely PSUs."""
import polars as pl, pandas as pd
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",300)
def P(d): print(d.to_pandas().to_string(index=False))
def piv(df, idx, val):
    t = df.pivot(on="YEAR", index=idx, values=val).sort(idx)
    return t.select([idx]+sorted([c for c in t.columns if c!=idx]))

cols = ["CASENUM","PSU","PSU_VAR","PSUSTRAT","STRATUM","PJ","REGION","URBANICITY","WEIGHT","MAX_SEV"]
a = load_table("CRSS","accident",years=None,columns=cols)
if 0: print("PSU_VAR per PSUSTRAT"); P(piv(a.group_by(["YEAR","PSUSTRAT"]).agg(pl.col("PSU_VAR").n_unique().alias("v")),"PSUSTRAT","v"))
print("PSU per PSUSTRAT"); P(piv(a.group_by(["YEAR","PSUSTRAT"]).agg(pl.col("PSU").n_unique().alias("v")),"PSUSTRAT","v"))
print("cases per PSUSTRAT"); P(piv(a.group_by(["YEAR","PSUSTRAT"]).agg(pl.len().alias("v")),"PSUSTRAT","v"))
print("min cases per PSU_VAR within stratum"); P(piv(a.group_by(["YEAR","PSUSTRAT","PSU_VAR"]).agg(pl.len().alias("n")).group_by(["YEAR","PSUSTRAT"]).agg(pl.col("n").min().alias("v")),"PSUSTRAT","v"))
print("cases per PSU_VAR"); P(piv(a.group_by(["YEAR","PSU_VAR"]).agg(pl.len().alias("v")),"PSU_VAR","v"))
m = a.group_by(["PSU_VAR"]).agg(pl.col("PSUSTRAT").unique().sort().cast(pl.List(pl.String)).list.join("/").alias("strata"),
     pl.col("PSU").unique().sort().cast(pl.List(pl.String)).list.join("/").alias("psus"),
     pl.col("YEAR").unique().sort().cast(pl.List(pl.String)).list.join(",").alias("years"),
     pl.col("REGION").unique().sort().cast(pl.List(pl.String)).list.join("/").alias("reg"),
     pl.col("URBANICITY").unique().sort().cast(pl.List(pl.String)).list.join("/").alias("urb")).sort("PSU_VAR")
print("PSU_VAR mapping"); P(m)
m2 = a.group_by(["PSU"]).agg(pl.col("PSU_VAR").unique().sort().alias("pv"), pl.col("PSUSTRAT").unique().sort().alias("str"), pl.col("YEAR").n_unique().alias("nyrs"))
m2 = m2.filter(pl.col("pv").list.len()>1).sort("PSU").with_columns(pl.col("pv").cast(pl.List(pl.String)).list.join("/"), pl.col("str").cast(pl.List(pl.String)).list.join("/"))
print("PSU in >1 PSU_VAR"); P(m2)
# PSU_VAR -> PSU pairs that differ by year
pp = a.group_by(["YEAR","PSU","PSU_VAR"]).agg(pl.len().alias("n")).filter(pl.col("PSU")!=pl.col("PSU_VAR")).sort(["PSU","YEAR"])
print("PSU != PSU_VAR"); P(pp)
# strata: region/urbanicity composition
s = a.group_by(["PSUSTRAT"]).agg(pl.col("REGION").unique().sort().alias("reg"), pl.col("URBANICITY").unique().sort().alias("urb"), pl.col("PSU_VAR").unique().sort().alias("psuvars")).sort("PSUSTRAT")
s = s.with_columns([pl.col(c).cast(pl.List(pl.String)).list.join("/") for c in ["reg","urb","psuvars"]])
print("PSUSTRAT composition"); P(s)
# PJ nesting in PSU across years
pj = a.group_by("PJ").agg(pl.col("PSU").n_unique().alias("k"))
print("PJ in >1 PSU over all years:", (pj["k"]>1).sum(), "of", pj.height)
