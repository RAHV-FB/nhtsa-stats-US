"""Where do imputed fatal crashes come from; unknown severity by sampling STRATUM; 2020 monthly sample/weights."""
import polars as pl, pandas as pd
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",400)
def P(d): print(d.to_pandas().to_string(index=False))
def piv(df, idx, val):
    t = df.pivot(on="YEAR", index=idx, values=val).sort(idx)
    return t.select([idx]+sorted([c for c in t.columns if c!=idx]))
a = load_table("CRSS","accident",years=None,columns=["CASENUM","STRATUM","MAX_SEV","MAXSEV_IM","WEIGHT","MONTH","PSU_VAR"])
x = a.filter((pl.col("MAXSEV_IM")==4)&(pl.col("MAX_SEV")!=4))
print("crashes with MAXSEV_IM=4 but MAX_SEV!=4: by year n, weighted, mean weight")
P(x.group_by("YEAR").agg(pl.len().alias("n"), pl.col("WEIGHT").sum().round(0).alias("sumW"), pl.col("WEIGHT").mean().round(1).alias("meanW")).sort("YEAR"))
print("by MAX_SEV"); P(x.group_by("MAX_SEV").agg(pl.len().alias("n"), pl.col("WEIGHT").sum().round(0).alias("sumW")).sort("MAX_SEV"))
print("by STRATUM"); P(x.group_by("STRATUM").agg(pl.len().alias("n"), pl.col("WEIGHT").sum().round(0).alias("sumW")).sort("STRATUM"))
y = a.filter((pl.col("MAXSEV_IM")!=4)&(pl.col("MAX_SEV")==4)); print("MAX_SEV=4 but MAXSEV_IM!=4:", y.height)
# unknown MAX_SEV (9) rate by STRATUM (sampling stratum assigned from PAR) and weighted
print("MAX_SEV=9 (all persons unknown) % by STRATUM x year")
P(piv(a.group_by(["YEAR","STRATUM"]).agg(((pl.col("MAX_SEV")==9).mean()*100).round(2).alias("v")),"STRATUM","v"))
print("weighted MAX_SEV=9 % by year:"); P(a.group_by("YEAR").agg(((pl.col("WEIGHT")*(pl.col("MAX_SEV")==9)).sum()/pl.col("WEIGHT").sum()*100).round(2).alias("pct9w"), ((pl.col("MAX_SEV")==9).mean()*100).round(2).alias("pct9")).sort("YEAR"))
p = load_table("CRSS","person",years=None,columns=["CASENUM","INJ_SEV","INJSEV_IM","STRATUM","PER_TYP","WEIGHT"])
print("person INJ_SEV=9 % by STRATUM x year"); P(piv(p.group_by(["YEAR","STRATUM"]).agg(((pl.col("INJ_SEV")==9).mean()*100).round(2).alias("v")),"STRATUM","v"))
print("person INJ_SEV=9 -> INJSEV_IM distribution (row %), by STRATUM group, pooled years")
q = p.filter(pl.col("INJ_SEV")==9).with_columns(pl.when(pl.col("STRATUM").is_in([9,10,7])).then(pl.lit("no-inj strata 7,9,10")).when(pl.col("STRATUM").is_in([6,8])).then(pl.lit("BC strata 6,8")).when(pl.col("STRATUM").is_in([4,5])).then(pl.lit("KA strata 4,5")).otherwise(pl.lit("2,3 nonocc/MC")).alias("sg"))
t = q.group_by(["sg","INJSEV_IM"]).agg(pl.len().alias("n"), pl.col("WEIGHT").sum().alias("w")).with_columns((pl.col("n")/pl.col("n").sum().over("sg")*100).round(2).alias("pct"), (pl.col("w")/pl.col("w").sum().over("sg")*100).round(2).alias("wpct")).sort(["sg","INJSEV_IM"])
P(t)
print("persons imputed fatal (INJ_SEV=9 -> INJSEV_IM=4) by year: n and weighted"); P(p.filter((pl.col("INJ_SEV")==9)&(pl.col("INJSEV_IM")==4)).group_by("YEAR").agg(pl.len().alias("n"), pl.col("WEIGHT").sum().round(0).alias("sumW")).sort("YEAR"))
# 2020 monthly
print("monthly n and weighted crashes (thousands), 2019 vs 2020 vs 2021")
m = a.filter(pl.col("YEAR").is_in([2019,2020,2021])).group_by(["YEAR","MONTH"]).agg(pl.len().alias("n"), (pl.col("WEIGHT").sum()/1000).round(1).alias("W"), pl.col("WEIGHT").median().round(1).alias("medW"))
P(m.pivot(on="YEAR", index="MONTH", values=["n","W","medW"]).sort("MONTH"))
# PSU_VAR 61 and 206 by month in 2020-2022 (partial participation?)
print("PSU_VAR 61/206/214 cases by year-month (selected)")
P(a.filter(pl.col("PSU_VAR").is_in([61,206])&pl.col("YEAR").is_in([2019,2020,2021,2022])).group_by(["PSU_VAR","YEAR"]).agg(pl.col("MONTH").n_unique().alias("months"), pl.col("MONTH").min().alias("first"), pl.col("MONTH").max().alias("last"), pl.len().alias("n")).sort(["PSU_VAR","YEAR"]))
# months covered per PSU_VAR per year: any PSU with <12 months
cov = a.group_by(["YEAR","PSU_VAR"]).agg(pl.col("MONTH").n_unique().alias("months")).filter(pl.col("months")<12).sort(["YEAR","PSU_VAR"])
print("PSU_VAR-years with <12 months of sampled crashes"); P(cov)
