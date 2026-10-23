"""Code distributions per source-year (with embedded labels when present) for all alcohol/drug variables.
Output: out_ad/dist.csv (source,year,table,var,code,label,n,N)."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
OUT = "outputs/cache/audit/out_ad"
spec = {
 ("FARS","person"): ["DRINKING","ALC_STATUS","ATST_TYP","ALC_DET","DRUGS","DRUG_DET","DRUGTST1","DRUGTST2","DRUGTST3","DRUGRES1","DRUGRES2","DRUGRES3","INJ_SEV","PER_TYP"],
 ("CRSS","person"): ["DRINKING","ALC_STATUS","ATST_TYP","DRUGS","PERALCH_IM","DRUGTST1","DRUGTST2","DRUGTST3","DRUGRES1","DRUGRES2","DRUGRES3","INJ_SEV","PER_TYP"],
 ("FARS","vehicle"): ["DR_DRINK"],
 ("CRSS","vehicle"): ["VEH_ALCH","V_ALCH_IM"],
 ("FARS","accident"): ["DRUNK_DR"],
 ("CRSS","accident"): ["ALCOHOL","ALCHL_IM","MAX_SEV"],
 ("FARS","drimpair"): ["DRIMPAIR"], ("CRSS","drimpair"): ["DRIMPAIR"],
 ("FARS","nmimpair"): ["NMIMPAIR"], ("CRSS","nmimpair"): ["NMIMPAIR"],
 ("FARS","drugs"): ["DRUGSPEC","DRUGMETHOD","DRUGUOM"],
 ("FARS","acc_aux"): ["A_POSBAC"], ("FARS","per_aux"): ["A_ALCTES"],
}
rows=[]
for (src,tab),vars_ in spec.items():
    import nhtsa_stats.ingestion.cache as c
    cols=[]
    for v in vars_: cols += [v, v+"NAME"]
    try:
        df = load_table(src, tab, years=None, columns=cols)
    except Exception as e:
        # label columns may not exist at all -> retry without
        print("retry", src, tab, e)
        df = load_table(src, tab, years=None, columns=vars_)
    for v in vars_:
        if v not in df.columns: continue
        lab = v+"NAME" if v+"NAME" in df.columns else None
        sel = df.select(["YEAR", pl.col(v).cast(pl.Utf8).alias("code")] + ([pl.col(lab).alias("label")] if lab else [pl.lit(None, pl.Utf8).alias("label")]))
        g = sel.group_by(["YEAR","code","label"]).len().rename({"len":"n"})
        N = sel.group_by("YEAR").len().rename({"len":"N"})
        g = g.join(N, on="YEAR").with_columns(pl.lit(src).alias("source"), pl.lit(tab).alias("table"), pl.lit(v).alias("var"))
        g = g.filter(pl.col("code").is_not_null() | (pl.col("n")>0))
        rows.append(g.select("source",pl.col("YEAR").alias("year"),"table","var","code","label","n","N"))
    del df
out = pl.concat(rows)
out.write_csv(f"{OUT}/dist.csv")
print(out.height)
