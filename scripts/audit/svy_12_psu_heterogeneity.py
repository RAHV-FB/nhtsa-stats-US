"""Between-PSU heterogeneity of weighted injury / fatal / alcohol shares (explains large design effects)."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
a = load_table("CRSS","accident",years=[2019,2024],columns=["CASENUM","PSU_VAR","WEIGHT","MAXSEV_IM","ALCHL_IM"])
for y in [2019,2024]:
    d = a.filter(pl.col("YEAR")==y).group_by("PSU_VAR").agg(
        ((pl.col("WEIGHT")*pl.col("MAXSEV_IM").is_in([1,2,3,4,5])).sum()/pl.col("WEIGHT").sum()*100).alias("inj"),
        ((pl.col("WEIGHT")*(pl.col("MAXSEV_IM")==4)).sum()/pl.col("WEIGHT").sum()*100).alias("fat"),
        ((pl.col("WEIGHT")*(pl.col("ALCHL_IM")==1)).sum()/pl.col("WEIGHT").sum()*100).alias("alc"), pl.len().alias("n"))
    for c in ["inj","fat","alc"]:
        s = d[c]
        print(y, c, "PSU_VAR-level weighted %: min", round(s.min(),1), "p25", round(s.quantile(0.25),1), "median", round(s.median(),1), "p75", round(s.quantile(0.75),1), "max", round(s.max(),1))
