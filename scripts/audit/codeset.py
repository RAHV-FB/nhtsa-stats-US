"""Codes not present in all years of a source: show years present + max share; flags first/last year."""
import polars as pl, sys
d = pl.read_csv("outputs/cache/audit/out/veh_dist.csv", infer_schema_length=0).with_columns(pl.col("n").cast(pl.Int64), pl.col("N").cast(pl.Int64), pl.col("year").cast(pl.Int64))
for v in sys.argv[1].split(","):
    print("###", v)
    for src in ["FARS","CRSS"]:
        x = d.filter((pl.col("var")==v)&(pl.col("source")==src))
        if x.height==0: continue
        yrs = sorted(x["year"].unique().to_list())
        g = x.group_by("code").agg(pl.col("year").sort().alias("yrs"), pl.col("n").sum().alias("ntot"), (pl.col("n")/pl.col("N")*100).max().round(3).alias("maxpct"), pl.col("label").drop_nulls().last().alias("lab"))
        g = g.filter(pl.col("yrs").list.len()<len(yrs)).sort(pl.col("code").cast(pl.Int64,strict=False))
        for r in g.iter_rows(named=True):
            ys = r["yrs"]
            # contiguous run?
            print(f"  {src} code {r['code']:>5}: years {ys[0]}-{ys[-1]} (n_years={len(ys)}/{len(yrs)}) total_n={r['ntot']} max%={r['maxpct']} | {(r['lab'] or '')[:80]}")
