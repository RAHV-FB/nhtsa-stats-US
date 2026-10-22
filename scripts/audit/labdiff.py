"""For each variable, list codes whose normalised label text differs across source-years (full text)."""
import polars as pl, sys, re
cb = pl.read_csv("outputs/audit/codebook.csv", infer_schema_length=0).filter(pl.col("table")==sys.argv[1])
vars_ = sys.argv[2].split(",")
def norm(s): return re.sub(r"[^a-z0-9]","",s.lower()) if s else None
for v in vars_:
    x = cb.filter(pl.col("variable")==v)
    if x.height==0: print(f"### {v}: no labels"); continue
    x = x.with_columns(pl.col("label").map_elements(norm, return_dtype=pl.Utf8).alias("nl"))
    print(f"### {v}")
    for code, g in x.group_by("code"):
        if g["nl"].n_unique()>1:
            print(f"  code {code[0]}:")
            for nl, gg in g.sort(["source","year"]).group_by("nl", maintain_order=True):
                sy = ",".join(f"{s[0]}{y[2:]}" for s,y in zip(gg["source"],gg["year"]))
                print(f"     [{sy}] {gg['label'][0]}")
