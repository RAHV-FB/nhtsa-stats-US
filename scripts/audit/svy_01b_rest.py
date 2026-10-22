import polars as pl, pandas as pd
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",300)
def P(d): print(d.to_pandas().to_string(index=False))
a = load_table("CRSS","accident",years=None,columns=["CASENUM","PSU","PSU_VAR","PSUSTRAT","PJ","REGION","URBANICITY"])
m2 = a.group_by(["PSU"]).agg(pl.col("PSU_VAR").unique().sort().alias("pv"), pl.col("PSUSTRAT").unique().sort().alias("str"))
m2 = m2.filter(pl.col("pv").list.len()>1).with_columns(pl.col("pv").cast(pl.List(pl.String)).list.join("/"), pl.col("str").cast(pl.List(pl.String)).list.join("/"))
print("PSU in >1 PSU_VAR"); P(m2)
print("rows with PSU != PSU_VAR by year:"); P(a.filter(pl.col("PSU")!=pl.col("PSU_VAR")).group_by(["YEAR","PSU"]).agg(pl.len().alias("n"), pl.col("PSU_VAR").n_unique().alias("npv")).sort("YEAR"))
s = a.group_by(["PSUSTRAT"]).agg(pl.col("REGION").unique().sort().alias("reg"), pl.col("URBANICITY").unique().sort().alias("urb"), pl.col("PSU_VAR").unique().sort().alias("psuvars"), pl.col("PSU").unique().sort().alias("psus")).sort("PSUSTRAT")
s = s.with_columns([pl.col(c).cast(pl.List(pl.String)).list.join("/") for c in ["reg","urb","psuvars","psus"]])
print("PSUSTRAT composition (all years)"); P(s)
pj = a.group_by("PJ").agg(pl.col("PSU").n_unique().alias("k"), pl.col("PSU_VAR").n_unique().alias("kv"))
print("PJ in >1 PSU over all years:", (pj["k"]>1).sum(), "of", pj.height, "; PJ in >1 PSU_VAR:", (pj["kv"]>1).sum())
pjy = a.group_by(["YEAR","PJ"]).agg(pl.col("PSU").n_unique().alias("k"), pl.col("PSU_VAR").n_unique().alias("kv"))
print("PJ in >1 PSU within year:", (pjy["k"]>1).sum(), " PJ in >1 PSU_VAR within year:", (pjy["kv"]>1).sum())
# PJ <-> PSU_VAR within stratum 20
s20 = a.filter(pl.col("PSUSTRAT")==20).group_by(["PSU_VAR"]).agg(pl.col("PJ").unique().sort().alias("pjs"), pl.col("YEAR").n_unique().alias("nyrs"), pl.len().alias("n")).sort("PSU_VAR")
print("Stratum 20 PSU_VAR -> PJs"); P(s20.with_columns(pl.col("pjs").cast(pl.List(pl.String)).list.join("/")))
# PJs per PSU per year summary
pp = a.group_by(["YEAR","PSU_VAR"]).agg(pl.col("PJ").n_unique().alias("npj")).group_by("YEAR").agg(pl.col("npj").min().alias("min"), pl.col("npj").median().alias("med"), pl.col("npj").max().alias("max"), pl.col("npj").sum().alias("tot")).sort("YEAR")
print("PJs per PSU_VAR per year"); P(pp)
# PJ code ranges vs PSU: is PJ = PSU*?
x = a.select(["PSU","PJ"]).unique().with_columns((pl.col("PJ")//100).alias("pj_div100"), (pl.col("PJ")//10).alias("pj_div10"))
print("PJ//100==PSU share:", (x["pj_div100"]==x["PSU"]).mean(), " PJ//10==PSU share:", (x["pj_div10"]==x["PSU"]).mean())
print(x.sort(["PSU","PJ"]).head(30).to_pandas().to_string(index=False))
