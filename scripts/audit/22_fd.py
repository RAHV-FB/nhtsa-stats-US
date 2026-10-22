"""Functional-dependency test: share of rows whose aux code equals the modal aux code within cells of given source columns."""
import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
def fd(df, a, keys, by="YEAR"):
    t = df.group_by([by] + keys + [a]).agg(pl.len().alias("n"))
    m = t.group_by([by] + keys).agg(c("n").max().alias("mx"), c("n").sum().alias("tot"))
    r = m.group_by(by).agg((c("mx").sum() / c("tot").sum() * 100).round(3).alias("pct_fd")).sort(by)
    return r
for src in ["FARS", "CRSS"]:
    mc = ["BODY_TYP", "VPICBODYCLASS"] + (["BDYTYP_IM"] if src == "CRSS" else [])
    df = aux_main(src, "veh", ["A_BODY"], mc)
    print(src, "A_BODY | BODY_TYP", fd(df, "A_BODY", ["BODY_TYP"]).to_dicts())
    print(src, "A_BODY | BODY_TYP,VPICBODYCLASS", fd(df, "A_BODY", ["BODY_TYP", "VPICBODYCLASS"]).to_dicts())
    if src == "CRSS":
        print(src, "A_BODY | BDYTYP_IM", fd(df, "A_BODY", ["BDYTYP_IM"]).to_dicts())
    # vPIC-only for 2020+
    d = df.filter(c("YEAR") >= 2020)
    print(src, "A_BODY | VPICBODYCLASS", fd(d, "A_BODY", ["VPICBODYCLASS"]).to_dicts())
    # residuals within (BODY_TYP, VPIC) cells
    t = d.group_by(["BODY_TYP", "VPICBODYCLASS", "A_BODY"]).agg(pl.len().alias("n"))
    m = t.group_by(["BODY_TYP", "VPICBODYCLASS"]).agg(c("n").sum().alias("tot"), c("n").max().alias("mx"), pl.struct("A_BODY", "n").sort_by("n", descending=True).alias("dist"))
    print(m.with_columns((c("tot") - c("mx")).alias("resid")).sort("resid", descending=True).head(12))
