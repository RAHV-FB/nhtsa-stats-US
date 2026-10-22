"""CRSS weight distribution, sums of weights by year/STRATUM/MAX_SEV, STRATUM meaning checks."""
import polars as pl, pandas as pd, numpy as np
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",400)
def P(d): print(d.to_pandas().to_string(index=False))
def piv(df, idx, val):
    t = df.pivot(on="YEAR", index=idx, values=val).sort(idx)
    return t.select([idx]+sorted([c for c in t.columns if c!=idx]))
a = load_table("CRSS","accident",years=None,columns=["CASENUM","PSU_VAR","PSUSTRAT","STRATUM","PJ","WEIGHT","MAX_SEV","MAXSEV_IM","URBANICITY","REGION"])
w = pl.col("WEIGHT")
s = a.group_by("YEAR").agg(pl.len().alias("n"), w.sum().round(0).alias("sumW"), w.min().round(2).alias("min"), w.quantile(0.01).round(2).alias("p01"),
    w.quantile(0.05).round(2).alias("p05"), w.median().round(2).alias("med"), w.mean().round(2).alias("mean"), w.quantile(0.95).round(2).alias("p95"),
    w.quantile(0.99).round(2).alias("p99"), w.max().round(2).alias("max"), (w.std()/w.mean()).round(3).alias("cv"),
    ((w.sum()**2)/(w**2).sum()).round(0).alias("kish_neff"), (w<=0).sum().alias("nonpos"), w.is_null().sum().alias("null"), w.n_unique().alias("ndistinct")).sort("YEAR")
s = s.with_columns((pl.col("n")/pl.col("kish_neff")).round(2).alias("deff_w"), (pl.col("max")/pl.col("min")).round(1).alias("max_min"))
print("Weights by year"); P(s)
print("STRATUM n by year"); P(piv(a.group_by(["YEAR","STRATUM"]).agg(pl.len().alias("v")),"STRATUM","v"))
print("STRATUM share of n (%)"); P(piv(a.group_by(["YEAR","STRATUM"]).agg(pl.len().alias("v")).with_columns((100*pl.col("v")/pl.col("v").sum().over("YEAR")).round(1).alias("v")),"STRATUM","v"))
print("STRATUM sum of weights (thousands)"); P(piv(a.group_by(["YEAR","STRATUM"]).agg((w.sum()/1000).round(1).alias("v")),"STRATUM","v"))
print("STRATUM weighted share (%)"); P(piv(a.group_by(["YEAR","STRATUM"]).agg(w.sum().alias("v")).with_columns((100*pl.col("v")/pl.col("v").sum().over("YEAR")).round(1).alias("v")),"STRATUM","v"))
print("STRATUM median weight"); P(piv(a.group_by(["YEAR","STRATUM"]).agg(w.median().round(1).alias("v")),"STRATUM","v"))
print("STRATUM min weight"); P(piv(a.group_by(["YEAR","STRATUM"]).agg(w.min().round(1).alias("v")),"STRATUM","v"))
print("STRATUM max weight"); P(piv(a.group_by(["YEAR","STRATUM"]).agg(w.max().round(1).alias("v")),"STRATUM","v"))
print("MAX_SEV n by year"); P(piv(a.group_by(["YEAR","MAX_SEV"]).agg(pl.len().alias("v")),"MAX_SEV","v"))
print("MAX_SEV sum weights (estimated crashes)"); P(piv(a.group_by(["YEAR","MAX_SEV"]).agg(w.sum().round(0).alias("v")),"MAX_SEV","v"))
print("MAX_SEV weighted share (%)"); P(piv(a.group_by(["YEAR","MAX_SEV"]).agg(w.sum().alias("v")).with_columns((100*pl.col("v")/pl.col("v").sum().over("YEAR")).round(2).alias("v")),"MAX_SEV","v"))
print("MAX_SEV median weight"); P(piv(a.group_by(["YEAR","MAX_SEV"]).agg(w.median().round(1).alias("v")),"MAX_SEV","v"))
print("MAX_SEV min/max weight"); P(piv(a.group_by(["YEAR","MAX_SEV"]).agg(pl.format("{}-{}", w.min().round(1), w.max().round(1)).alias("v")),"MAX_SEV","v"))
print("MAXSEV_IM sum weights"); P(piv(a.group_by(["YEAR","MAXSEV_IM"]).agg(w.sum().round(0).alias("v")),"MAXSEV_IM","v"))
# STRATUM x MAX_SEV (unweighted, all years pooled and per year group)
for yrs,lab in [([2016,2017,2018],"2016-18"),([2019,2020,2021,2022,2023,2024],"2019-24")]:
    x = a.filter(pl.col("YEAR").is_in(yrs)).group_by(["STRATUM","MAX_SEV"]).agg(pl.len().alias("n")).pivot(on="MAX_SEV",index="STRATUM",values="n").sort("STRATUM")
    x = x.select(["STRATUM"]+sorted([c for c in x.columns if c!="STRATUM"], key=int)).fill_null(0)
    print(f"STRATUM x MAX_SEV rows, {lab}"); P(x)
# distinct weights within (YEAR, PJ, STRATUM)
d = a.group_by(["YEAR","PJ","STRATUM"]).agg(w.n_unique().alias("k"), pl.len().alias("n"))
print("cells (YEAR,PJ,STRATUM):", d.height, " with >1 distinct weight:", (d["k"]>1).sum(), " share of rows in such cells:", round(d.filter(pl.col("k")>1)["n"].sum()/d["n"].sum(),3))
d = a.group_by(["YEAR","PSU_VAR","STRATUM"]).agg(w.n_unique().alias("k"), pl.len().alias("n"))
print("cells (YEAR,PSU_VAR,STRATUM):", d.height, " with >1 distinct weight:", (d["k"]>1).sum())
# weight by urbanicity/region
print("sum W by URBANICITY (thousands)"); P(piv(a.group_by(["YEAR","URBANICITY"]).agg((w.sum()/1000).round(0).alias("v")),"URBANICITY","v"))
print("sum W by REGION (thousands)"); P(piv(a.group_by(["YEAR","REGION"]).agg((w.sum()/1000).round(0).alias("v")),"REGION","v"))
print("n by URBANICITY"); P(piv(a.group_by(["YEAR","URBANICITY"]).agg(pl.len().alias("v")),"URBANICITY","v"))
print("sum W by PSUSTRAT (thousands)"); P(piv(a.group_by(["YEAR","PSUSTRAT"]).agg((w.sum()/1000).round(0).alias("v")),"PSUSTRAT","v"))
# extreme weights: top 10 overall
print("top weights"); P(a.sort("WEIGHT",descending=True).head(12).select(["YEAR","CASENUM","PSUSTRAT","PSU_VAR","PJ","STRATUM","MAX_SEV","WEIGHT"]))
