"""What makes WEIGHT vary within PJ x STRATUM? Test candidate adjustment-cell definitions."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
a = load_table("CRSS","accident",years=None,columns=["CASENUM","PJ","STRATUM","MONTH","MAXSEV_IM","MAX_SEV","WEIGHT","REGION","PSU_VAR"])
a = a.with_columns((pl.col("MAXSEV_IM")==4).alias("fatIM"), ((pl.col("MONTH")-1)//3).alias("Q"), pl.col("WEIGHT").round(6).alias("W6"))
for cell in [["PJ","STRATUM"],["PJ","STRATUM","fatIM"],["PJ","STRATUM","MONTH"],["PJ","STRATUM","Q"],["PJ","STRATUM","MONTH","fatIM"],["PSU_VAR","STRATUM","MONTH","fatIM"]]:
    g = a.group_by(["YEAR"]+cell).agg(pl.col("W6").n_unique().alias("k"), pl.len().alias("n"))
    s = g.group_by("YEAR").agg((pl.col("k")>1).sum().alias("cells_multi"), pl.len().alias("cells"), (pl.col("n")*(pl.col("k")>1)).sum().alias("rows_in_multi")).sort("YEAR")
    print(cell); print(s.to_pandas().to_string(index=False))
# ratio of fatal-crash weight to non-fatal weight in same PJ x STRATUM x MONTH
f = a.group_by(["YEAR","PJ","STRATUM","MONTH","fatIM"]).agg(pl.col("WEIGHT").mean().alias("w"))
r = f.filter(pl.col("fatIM")).join(f.filter(~pl.col("fatIM")), on=["YEAR","PJ","STRATUM","MONTH"], suffix="_nf").with_columns((pl.col("w")/pl.col("w_nf")).alias("ratio"))
print("fatal/nonfatal weight ratio within PJ x STRATUM x MONTH, by year x region:")
r = r.join(a.select(["YEAR","PJ","REGION"]).unique(), on=["YEAR","PJ"])
print(r.group_by(["YEAR","REGION"]).agg(pl.col("ratio").median().round(4).alias("med"), pl.col("ratio").min().round(4).alias("min"), pl.col("ratio").max().round(4).alias("max"), pl.len().alias("cells")).sort(["YEAR","REGION"]).to_pandas().to_string(index=False))
