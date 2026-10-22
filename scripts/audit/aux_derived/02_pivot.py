"""Pivot distribution: per source/table/var, codes x years (pct)."""
import polars as pl, sys
d = pl.read_csv("/tmp/nhtsa-audit/out_aux/aux_dist.csv", infer_schema_length=0)
d = d.with_columns(pl.col("n").cast(pl.Int64), pl.col("year").cast(pl.Int64)).sort("year")
tot = d.group_by(["source","table","year","var"]).agg(pl.col("n").sum().alias("tot"))
d = d.join(tot, on=["source","table","year","var"])
for (src, tab, var), g in d.sort(["source","table","var"]).group_by(["source","table","var"], maintain_order=True):
    if (g["code"] == "__MANY__").any():
        m = g.select("year","dtype","nd","mn","mx","nnull","tot").sort("year")
        print(f"\n### {src} {tab} {var} MANY"); print(m.to_pandas().to_string(index=False)); continue
    p = g.with_columns((100*pl.col("n")/pl.col("tot")).round(2).alias("pct")).pivot(on="year", index="code", values="pct", sort_columns=True).with_columns(pl.col("code").cast(pl.Int64, strict=False)).sort("code")
    print(f"\n### {src} {tab} {var} dtype={g['dtype'][0]} nulls={g.group_by('year').agg(pl.col('nnull').first()).sort('year')['nnull'].to_list()}")
    print(p.to_pandas().to_string(index=False))
