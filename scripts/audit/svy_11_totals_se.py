"""Estimated national crash totals (sum of WEIGHT) by year and by MAXSEV_IM / MAX_SEV class, with design SE (PSUSTRAT/PSU_VAR)."""
import polars as pl, pandas as pd
from nhtsa_stats.ingestion.cache import load_table
from svy_lib import svy_total
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
a = load_table("CRSS","accident",years=None,columns=["CASENUM","PSUSTRAT","PSU_VAR","WEIGHT","MAX_SEV","MAXSEV_IM"])
cats = {"all": pl.lit(1.0), "O (IM=0)": (pl.col("MAXSEV_IM")==0).cast(pl.Float64), "C (IM=1)": (pl.col("MAXSEV_IM")==1).cast(pl.Float64),
        "B (IM=2)": (pl.col("MAXSEV_IM")==2).cast(pl.Float64), "A (IM=3)": (pl.col("MAXSEV_IM")==3).cast(pl.Float64), "K (IM=4)": (pl.col("MAXSEV_IM")==4).cast(pl.Float64),
        "inj-unk (IM=5)": (pl.col("MAXSEV_IM")==5).cast(pl.Float64), "unknown (MAX_SEV=9)": (pl.col("MAX_SEV")==9).cast(pl.Float64)}
rows=[]
for y in range(2016,2025):
    d = a.filter(pl.col("YEAR")==y)
    for k,e in cats.items():
        est,se,_ = svy_total(d,e)
        rows.append(dict(YEAR=y, cat=k, est_k=round(est/1000,1), se_k=round(se/1000,1), rse_pct=round(100*se/est,1)))
r = pl.DataFrame(rows)
for col in ["est_k","se_k","rse_pct"]:
    t = r.pivot(on="YEAR", index="cat", values=col)
    print(col); print(t.to_pandas().to_string(index=False))
