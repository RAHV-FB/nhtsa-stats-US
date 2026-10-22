"""Code sets and distribution similarity (TVD) by year for design/severity vars; label transfer to CRSS 2016-18."""
import polars as pl, pandas as pd
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250)
a = load_table("CRSS","accident",years=None,columns=["CASENUM","STRATUM","REGION","URBANICITY","MAX_SEV","MAXSEV_IM","PSUSTRAT","WEIGHT"])
for v in ["STRATUM","REGION","URBANICITY","MAX_SEV","MAXSEV_IM","PSUSTRAT"]:
    t = a.group_by(["YEAR",v]).agg(pl.len().alias("n"), pl.col("WEIGHT").sum().alias("w")).with_columns((pl.col("n")/pl.col("n").sum().over("YEAR")).alias("s"), (pl.col("w")/pl.col("w").sum().over("YEAR")).alias("sw"))
    codes = t.group_by("YEAR").agg(pl.col(v).sort().alias("c")).sort("YEAR")
    cs = {r["YEAR"]: tuple(r["c"]) for r in codes.iter_rows(named=True)}
    ref = cs[2019]
    piv = t.pivot(on="YEAR", index=v, values="s").fill_null(0); pivw = t.pivot(on="YEAR", index=v, values="sw").fill_null(0)
    tvd = {y: round(0.5*sum(abs(piv[str(y)][i]-piv["2019"][i]) for i in range(piv.height)),3) for y in range(2016,2025)}
    tvdw = {y: round(0.5*sum(abs(pivw[str(y)][i]-pivw["2019"][i]) for i in range(pivw.height)),3) for y in range(2016,2025)}
    print(v, "codes2019:", ref, "| years with different code set:", {y:c for y,c in cs.items() if c!=ref})
    print("   TVD vs 2019 (unweighted):", tvd); print("   TVD vs 2019 (weighted):  ", tvdw)
# MAXSEV_IM deterministic from persons in early vs late years
p = load_table("CRSS","person",years=None,columns=["CASENUM","INJSEV_IM","INJ_SEV"])
pm = p.group_by(["YEAR","CASENUM"]).agg(pl.col("INJSEV_IM").filter(pl.col("INJSEV_IM")<=4).max().alias("mx"), (pl.col("INJSEV_IM")==5).any().alias("a5"), (pl.col("INJSEV_IM")==6).any().alias("a6"),
     pl.col("INJ_SEV").filter(pl.col("INJ_SEV")<=4).max().alias("mxo"), (pl.col("INJ_SEV")==5).any().alias("o5"), (pl.col("INJ_SEV")==9).all().alias("all9"))
j = a.join(pm, on=["YEAR","CASENUM"], how="left").with_columns(
    pl.when(pl.col("mx").is_null() & pl.col("a5").is_null()).then(8).when(pl.col("mx").is_null() | ((pl.col("mx")==0) & pl.col("a5"))).then(pl.when(pl.col("a5")).then(5).otherwise(6)).otherwise(pl.col("mx")).alias("pred_im"),
    pl.when(pl.col("mxo").is_null() & pl.col("o5").is_null()).then(8).when(pl.col("all9")).then(9).when(pl.col("mxo").is_null() | ((pl.col("mxo")==0) & pl.col("o5"))).then(pl.when(pl.col("o5")).then(5).otherwise(6)).otherwise(pl.col("mxo")).alias("pred"))
print(j.group_by("YEAR").agg((pl.col("pred_im")!=pl.col("MAXSEV_IM")).sum().alias("MAXSEV_IM_mismatch"), (pl.col("pred")!=pl.col("MAX_SEV")).sum().alias("MAX_SEV_mismatch"), pl.len().alias("n")).sort("YEAR").to_pandas().to_string(index=False))
print(j.filter(pl.col("pred")!=pl.col("MAX_SEV")).group_by(["MAX_SEV","pred"]).len().to_pandas().to_string(index=False))
