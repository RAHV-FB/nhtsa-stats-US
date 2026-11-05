"""G01 claim: 'Any projection of a camera programme should therefore target limit-exceeding crashes' (RR 5.2 vs 1.06).
Tests whether the exceeded-vs-too-fast contrast holds in the settings cameras operate (urban, low speed limit) using
weighted CRSS crude P(fatal | crash) by speeding_type x speed-limit band x urban. Also CRSS unknown/unspecified share by year."""
import polars as pl
c = pl.read_parquet("data/processed/crss_crash.parquet")
print([x for x in c.columns if x in ("WEIGHT","fatal","ka","speeding_type","speed_limit","rural","FATALS","MAX_SEV","max_sev","YEAR","severity")])
print(c.columns)
import pandas as pd
d = c.select(["WEIGHT","speeding_type","speed_limit","urbanicity","fatal","ka","YEAR"]).to_pandas()
print(d.speed_limit.value_counts(dropna=False).head(12)); print(d.urbanicity.value_counts(dropna=False))
d["fatal"]=d.fatal.astype(float); d["ka"]=d.ka.astype(float)
def tab(by):
    g=d.groupby(by,observed=True).apply(lambda x: pd.Series({"n":len(x),"wN":x.WEIGHT.sum(),
        "p_fatal_x1000":1000*(x.WEIGHT*x.fatal).sum()/x.WEIGHT.sum(),"p_ka_pct":100*(x.WEIGHT*x.ka).sum()/x.WEIGHT.sum(),"n_fatal":x.fatal.sum()}))
    return g
print(tab("speeding_type"))
print(tab(["urbanicity","speeding_type"]))
print(tab(["speed_limit","speeding_type"]))
# share of crashes by type per year (weighted)
t=d.groupby(["YEAR","speeding_type"]).WEIGHT.sum().unstack(); print((t.div(t.sum(1),axis=0)*100).round(1))
