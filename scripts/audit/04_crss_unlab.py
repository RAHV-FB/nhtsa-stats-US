"""CRSS 2016-2018 (unlabelled): code-set overlap with labelled CRSS 2019+ / same-year FARS; TVD of distributions."""
import polars as pl
OUT="/tmp/nhtsa-audit/out"
d = pl.read_csv(f"{OUT}/veh_dist.csv", infer_schema_length=0).with_columns(pl.col("n").cast(pl.Int64), pl.col("N").cast(pl.Int64), pl.col("year").cast(pl.Int64))
cb = pl.read_csv("outputs/audit/codebook.csv", infer_schema_length=0).filter(pl.col("table")=="vehicle")
NUMERIC_LIKE = {"MOD_YEAR","MDLYR_IM","NUMOCCS","TRAV_SP","DEATHS","NUM_INJV","NUMINJ_IM"}
def dist(src,y,v):
    x = d.filter((pl.col("source")==src)&(pl.col("year")==y)&(pl.col("var")==v))
    return {c:n/N for c,n,N in zip(x["code"],x["n"],x["N"])}
def tvd(a,b):
    ks=set(a)|set(b); return round(0.5*sum(abs(a.get(k,0)-b.get(k,0)) for k in ks),4)
rows=[]
vars_ = sorted(d.filter((pl.col("source")=="CRSS")&(pl.col("year")<=2018))["var"].unique().to_list())
for v in vars_:
    lab_c = set(cb.filter((pl.col("source")=="CRSS")&(pl.col("variable")==v))["code"].to_list())
    for y in (2016,2017,2018):
        lab_f = set(cb.filter((pl.col("source")=="FARS")&(pl.col("variable")==v)&(pl.col("year")==str(y)))["code"].to_list())
        a = dist("CRSS",y,v)
        if not a: continue
        unl = {c:p for c,p in a.items() if c not in lab_c and c not in lab_f}
        unl_c19 = {c:p for c,p in a.items() if c not in lab_c}
        rows.append(dict(var=v, year=y, n_codes=len(a), n_codes_not_in_any_label=len(unl), pct_rows_not_in_any_label=round(100*sum(unl.values()),3),
                         n_codes_not_in_CRSS19plus=len(unl_c19), pct_rows_not_in_CRSS19plus=round(100*sum(unl_c19.values()),3),
                         ex_unl=",".join(sorted(unl, key=lambda c:-unl[c])[:6]),
                         tvd_vs_next=tvd(a, dist("CRSS",y+1,v)), tvd_vs_FARS_same=tvd(a, dist("FARS",y,v)) if dist("FARS",y,v) else None))
    rows.append(dict(var=v, year=1920, n_codes=None, n_codes_not_in_any_label=None, pct_rows_not_in_any_label=None, n_codes_not_in_CRSS19plus=None, pct_rows_not_in_CRSS19plus=None, ex_unl="baseline C19->C20,C20->C21",
                     tvd_vs_next=tvd(dist("CRSS",2019,v),dist("CRSS",2020,v)) if dist("CRSS",2020,v) else None, tvd_vs_FARS_same=tvd(dist("CRSS",2020,v),dist("CRSS",2021,v)) if dist("CRSS",2021,v) else None))
r = pl.DataFrame(rows)
r.write_csv(f"{OUT}/crss_unlabelled_check.csv")
pl.Config.set_tbl_rows(400); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250); pl.Config.set_fmt_str_lengths(40)
print(r)
