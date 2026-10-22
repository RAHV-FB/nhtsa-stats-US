"""Consistency of design fields for the same CASENUM across CRSS tables (incl. aux)."""
import polars as pl, pandas as pd, os, glob
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",400)
DES = ["PSU","PSU_VAR","PSUSTRAT","STRATUM","PJ","REGION","URBANICITY","WEIGHT"]
acc = load_table("CRSS","accident",years=None,columns=["CASENUM"]+DES)
print("CASENUM prefix != YEAR:", acc.filter((pl.col("CASENUM")//10**8)!=pl.col("YEAR")).height, "; CASENUM unique overall:", acc["CASENUM"].n_unique()==acc.height)
ref = acc.rename({c: c+"_acc" for c in DES})
tables = sorted(os.path.basename(p) for p in glob.glob("/home/user/nhtsa-stats-US/data/interim/CRSS/*"))
inv = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/variable_availability.csv", infer_schema_length=0).filter(pl.col("source")=="CRSS")
rows=[]
for t in tables:
    if t=="accident": continue
    have = inv.filter(pl.col("table")==t)["column"].to_list()
    if "CASENUM" not in have: continue
    cols = ["CASENUM"]+[c for c in DES if c in have]
    df = load_table("CRSS",t,years=None,columns=cols)
    j = df.join(ref, on=["YEAR","CASENUM"], how="left")
    for y,g in j.group_by("YEAR"):
        r = dict(table=t, YEAR=y[0], rows=g.height, cases=g["CASENUM"].n_unique(), orphan_rows=int(g["WEIGHT_acc"].is_null().sum()))
        for c in DES:
            if c in cols:
                if c=="WEIGHT":
                    r["WEIGHT_mismatch"]=int(((g["WEIGHT"]-g["WEIGHT_acc"]).abs()>1e-6).sum()); r["WEIGHT_null"]=int(g["WEIGHT"].is_null().sum())
                else:
                    r[c+"_mm"]=int((g[c]!=g[c+"_acc"]).sum())
        rows.append(r)
    del df, j
res = pl.DataFrame(rows, infer_schema_length=None).sort(["table","YEAR"])
# summarise across years
agg = res.group_by("table").agg([pl.col(c).sum() for c in res.columns if c not in ("table","YEAR")]).sort("table")
print(agg.to_pandas().to_string(index=False))
print(res.filter(pl.col("orphan_rows")>0).to_pandas().to_string(index=False))
# coverage: accident cases with no vehicle / person rows
v = load_table("CRSS","vehicle",years=None,columns=["CASENUM"]).unique()
p = load_table("CRSS","person",years=None,columns=["CASENUM"]).unique()
for nm, s in [("vehicle",v),("person",p)]:
    miss = acc.join(s, on=["YEAR","CASENUM"], how="anti").group_by("YEAR").len().sort("YEAR")
    print(f"accident cases without any {nm} row:", miss.to_dicts())
# person WEIGHT vs accident WEIGHT exact float equality check
pp = load_table("CRSS","person",years=None,columns=["CASENUM","WEIGHT"]).join(acc.select(["YEAR","CASENUM","WEIGHT"]).rename({"WEIGHT":"WA"}), on=["YEAR","CASENUM"])
print("person rows with WEIGHT exactly != accident WEIGHT:", (pp["WEIGHT"]!=pp["WA"]).sum(), "max abs diff:", (pp["WEIGHT"]-pp["WA"]).abs().max())
