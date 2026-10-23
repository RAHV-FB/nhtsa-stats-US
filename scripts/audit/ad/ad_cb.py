"""Codebook pivot for alcohol/drug audit: code x source-year counts with label variants."""
import polars as pl, sys, re
cb = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/codebook.csv", infer_schema_length=0)
def norm(s): return re.sub(r"[^a-z0-9]","",s.lower()) if s else None
src, table, var = sys.argv[1], sys.argv[2], sys.argv[3]
maxcodes = int(sys.argv[4]) if len(sys.argv)>4 else 200
x = cb.filter((pl.col("source")==src)&(pl.col("table")==table)&(pl.col("variable")==var)).with_columns(pl.col("n").cast(pl.Int64), pl.col("year").cast(pl.Int64))
x = x.with_columns(pl.col("code").cast(pl.Float64, strict=False).alias("ci"))
codes = x.select("ci","code").unique().sort("ci")
yrs = sorted(x["year"].unique().to_list())
print(f"## {src} {table}.{var} years={yrs}")
tot = x.group_by("year").agg(pl.col("n").sum().alias("N"))
print("N per year:", dict(zip(tot.sort("year")["year"], tot.sort("year")["N"])))
for i,(ci,code) in enumerate(codes.iter_rows()):
    if i>=maxcodes: print("...", codes.height, "codes total"); break
    g = x.filter(pl.col("code")==code).sort("year")
    cnt = " ".join(f"{str(y)[2:]}:{n}" for y,n in zip(g["year"],g["n"]))
    labs = {}
    for y,l in zip(g["year"], g["label"]):
        labs.setdefault(norm(l),[]).append((y,l))
    ls = " || ".join(f"[{v[0][0]}-{v[-1][0]}] {v[0][1]}" for v in labs.values())
    print(f"{code:>6} | {cnt} | {ls}")
