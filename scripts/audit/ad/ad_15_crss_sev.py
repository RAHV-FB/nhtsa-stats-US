"""CRSS weighted alcohol involvement & missingness by severity (crash MAX_SEV; driver INJ_SEV), by year; simple ORs under 3 codings."""
import polars as pl, math
OUT = "outputs/cache/audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
a = pl.read_parquet(f"{OUT}/crss_crash.parquet")
SEV = {0:"O",1:"C",2:"B",3:"A",4:"K"}
a = a.filter(pl.col("MAX_SEV").is_in([0,1,2,3,4])).with_columns(pl.col("MAX_SEV").replace_strict(SEV).alias("sev"))
def wtab(df, by, expr, name):
    return df.group_by(by).agg(((expr).cast(pl.Float64)*pl.col("WEIGHT")).sum().truediv(pl.col("WEIGHT").sum()).mul(100).round(2).alias(name))
for name, expr in [("ALCOHOL=1", pl.col("ALCOHOL")==1), ("ALCOHOL=9 unknown", pl.col("ALCOHOL")==9), ("ALCHL_IM=1", pl.col("ALCHL_IM")==1)]:
    t = wtab(a, ["YEAR","sev"], expr, "p").pivot(on="sev", index="YEAR", values="p").sort("YEAR").select(["YEAR","O","C","B","A","K"])
    print(f"--- weighted % {name} by MAX_SEV"); print(t)
# complete-case % among known
t = a.filter(pl.col("ALCOHOL").is_in([1,2])).pipe(wtab, ["YEAR","sev"], pl.col("ALCOHOL")==1, "p").pivot(on="sev", index="YEAR", values="p").sort("YEAR").select(["YEAR","O","C","B","A","K"])
print("--- weighted % ALCOHOL=1 among known (1/2)"); print(t)
# pooled period ORs K vs O and A vs O, KA vs O
def orr(df, ycol_expr, grp_a, grp_b):
    x = df.with_columns(ycol_expr.alias("y"))
    def odds(g):
        s = x.filter(pl.col("sev").is_in(g))
        p = (s["y"].cast(pl.Float64)*s["WEIGHT"]).sum()/s["WEIGHT"].sum()
        return p/(1-p), p
    oa, pa = odds(grp_a); ob, pb = odds(grp_b)
    return round(oa/ob,2), round(100*pa,2), round(100*pb,2)
for per,(y0,y1) in {"2016-18":(2016,2018),"2020-24":(2020,2024)}.items():
    s = a.filter(pl.col("YEAR").is_between(y0,y1))
    for lab, e, sub in [("unknown-as-no ALCOHOL==1", pl.col("ALCOHOL")==1, s), ("complete-case", pl.col("ALCOHOL")==1, s.filter(pl.col("ALCOHOL").is_in([1,2]))), ("ALCHL_IM", pl.col("ALCHL_IM")==1, s)]:
        print(per, lab, "OR K vs O, pK, pO:", orr(sub, e, ["K"], ["O"]), " OR A vs O:", orr(sub, e, ["A"], ["O"]), " OR C vs O:", orr(sub, e, ["C"], ["O"]))
# driver-level
p = pl.read_parquet(f"{OUT}/crss_person.parquet").filter((pl.col("PER_TYP")==1)&pl.col("INJ_SEV").is_in([0,1,2,3,4]))
p = p.with_columns(pl.col("INJ_SEV").replace_strict(SEV).alias("sev"))
for name, expr in [("DRINKING=1", pl.col("DRINKING")==1), ("DRINKING=8 not reported", pl.col("DRINKING")==8), ("DRINKING=9 unknown", pl.col("DRINKING")==9),
                   ("ALC test given (ALC_STATUS=2)", pl.col("ALC_STATUS")==2), ("measured BAC (ALC_RES<=940)", pl.col("ALC_RES")<=940),
                   ("PERALCH_IM=1", pl.col("PERALCH_IM")==1), ("DRUGS=1", pl.col("DRUGS")==1), ("DRUGS=8/9", pl.col("DRUGS").is_in([8,9]))]:
    t = wtab(p, ["YEAR","sev"], expr, "p").pivot(on="sev", index="YEAR", values="p").sort("YEAR").select(["YEAR","O","C","B","A","K"])
    print(f"--- DRIVERS weighted % {name} by own INJ_SEV"); print(t)
# BAC>=.08 among measured, by sev (pooled, unweighted n and weighted %)
m = p.filter(pl.col("ALC_RES")<=940)
print("CRSS drivers with measured BAC: n by sev and weighted % >=.08 (pooled 2016-2024)")
print(m.group_by("sev").agg(pl.len(), ((pl.col("ALC_RES")>=80).cast(pl.Float64)*pl.col("WEIGHT")).sum().truediv(pl.col("WEIGHT").sum()).mul(100).round(1).alias("pct08"),
      ((pl.col("DRINKING")==1).cast(pl.Float64)*pl.col("WEIGHT")).sum().truediv(pl.col("WEIGHT").sum()).mul(100).round(1).alias("pct_drinking1")).sort("sev"))
# test given by DRINKING (selection) among CRSS drivers pooled
print("CRSS drivers: weighted % with ALC test given by DRINKING category and sev group")
p2 = p.with_columns(pl.when(pl.col("sev").is_in(["K","A"])).then(pl.lit("KA")).otherwise(pl.lit("BCO")).alias("sg"))
print(p2.group_by(["sg","DRINKING"]).agg(((pl.col("ALC_STATUS")==2).cast(pl.Float64)*pl.col("WEIGHT")).sum().truediv(pl.col("WEIGHT").sum()).mul(100).round(1).alias("pct_tested"), pl.len()).sort(["sg","DRINKING"]))
