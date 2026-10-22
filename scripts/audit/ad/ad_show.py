"""Pivot dist.csv: code x source-year percent (or n), with label variants. usage: ad_show.py VAR [SOURCES] [pct|n] [TABLE]"""
import polars as pl, sys, re
OUT = "/tmp/nhtsa-audit/out_ad"
d = pl.read_csv(f"{OUT}/dist.csv", infer_schema_length=0).with_columns(pl.col("n").cast(pl.Int64), pl.col("N").cast(pl.Int64), pl.col("year").cast(pl.Int64))
def norm(s): return re.sub(r"[^a-z0-9]","",s.lower()) if s else None
var = sys.argv[1]; srcs = sys.argv[2].split(",") if len(sys.argv)>2 else ["FARS","CRSS"]
mode = sys.argv[3] if len(sys.argv)>3 else "pct"
x = d.filter((pl.col("var")==var)&pl.col("source").is_in(srcs))
if len(sys.argv)>4: x = x.filter(pl.col("table")==sys.argv[4])
x = x.group_by(["source","year","code"]).agg(pl.col("n").sum(), pl.col("N").first(), pl.col("label").drop_nulls().first())
x = x.with_columns(pl.col("code").cast(pl.Float64, strict=False).alias("ci"))
pl.Config.set_tbl_rows(500); pl.Config.set_tbl_cols(40); pl.Config.set_fmt_str_lengths(70); pl.Config.set_tbl_width_chars(400)
lab = {}
for r in x.filter(pl.col("label").is_not_null()).sort(["source","year"]).iter_rows(named=True):
    lab.setdefault(r["code"],[]).append((r["source"][0]+str(r["year"])[2:], r["label"]))
x = x.with_columns((pl.col("source").str.slice(0,1)+pl.col("year").cast(pl.Utf8).str.slice(2,2)).alias("sy"),
                   (100*pl.col("n")/pl.col("N")).round(2).alias("pct"))
val = "pct" if mode=="pct" else "n"
p = x.pivot(on="sy", index=["ci","code"], values=val).sort("ci", nulls_last=True)
order = [c for s in srcs for c in [s[0]+str(y)[2:] for y in range(2016,2025)] if c in p.columns]
p = p.select(["code"]+order)
labs=[]
for c in p["code"]:
    L = lab.get(c,[])
    nl = {}
    for sy,l in L: nl.setdefault(norm(l),[]).append((sy,l))
    if not nl: labs.append("")
    elif len(nl)==1: labs.append(L[-1][1][:70])
    else: labs.append(" || ".join(f"{v[0][0]}-{v[-1][0]}:{v[0][1][:50]}" for v in nl.values()))
p = p.with_columns(pl.Series("label",labs))
print(f"### {var} {srcs} {mode}")
print(p)
