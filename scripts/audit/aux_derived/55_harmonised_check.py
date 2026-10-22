"""Check that the recommended universe-restricted recodes of A_RESTUSE / A_HELMUSE are break-free."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import *
c = pl.col
for src in ["FARS", "CRSS"]:
    d = aux_main(src, "per", ["A_RESTUSE", "A_HELMUSE"] + (["WEIGHT"] if src == "CRSS" else []), ["PER_TYP", "BODY_TYP", "REST_USE", "HELM_USE", "HELM_MIS", "REST_MIS"])
    d = d.with_columns((c("WEIGHT") if src == "CRSS" else pl.lit(1.0)).alias("w"))
    OCC = c("PER_TYP").is_in([1, 2, 9]); MCR = c("BODY_TYP").is_between(80, 84) | c("BODY_TYP").is_between(87, 89); MC = c("BODY_TYP").is_between(80, 89)
    u = d.filter(OCC & ~MCR)
    t = u.group_by(["YEAR", "A_RESTUSE"]).agg(c("w").sum().alias("w")).join(u.group_by("YEAR").agg(c("w").sum().alias("tw")), on="YEAR").with_columns((100 * c("w") / c("tw")).round(2).alias("pct"))
    print(src, "A_RESTUSE among PER_TYP 1/2/9 & BODY_TYP not 80-84/87-89 (", "weighted" if src == "CRSS" else "unweighted", ")")
    print(t.pivot(on="YEAR", index="A_RESTUSE", values="pct", sort_columns=True).sort("A_RESTUSE"))
    # helmet harmonised from source: MC riders; 2016-18 REST_USE helmet codes; 2019+ HELM_USE
    m = d.filter(OCC & MC).with_columns(
        pl.when(c("YEAR") <= 2018).then(pl.when(c("REST_USE").is_in([5, 16, 19]) & (c("REST_MIS") != 1)).then(1).when(c("REST_USE").is_in([5, 16, 19])).then(2).when(c("REST_USE").is_in([29, 98, 99])).then(3).otherwise(2))
        .otherwise(pl.when(c("HELM_USE").is_in([5, 16, 19]) & (c("HELM_MIS") != 1)).then(1).when(c("HELM_USE").is_in([98, 99])).then(3).otherwise(2)).alias("H"))
    t = m.group_by(["YEAR", "H"]).agg(c("w").sum().alias("w")).join(m.group_by("YEAR").agg(c("w").sum().alias("tw")), on="YEAR").with_columns((100 * c("w") / c("tw")).round(2).alias("pct"))
    print(src, "harmonised helmet among MC riders (1 used, 2 not used, 3 unknown)")
    print(t.pivot(on="YEAR", index="H", values="pct", sort_columns=True).sort("H"))
    t = m.group_by(["YEAR", "A_HELMUSE"]).agg(c("w").sum().alias("w")).join(m.group_by("YEAR").agg(c("w").sum().alias("tw")), on="YEAR").with_columns((100 * c("w") / c("tw")).round(2).alias("pct"))
    print(src, "raw A_HELMUSE among MC riders")
    print(t.pivot(on="YEAR", index="A_HELMUSE", values="pct", sort_columns=True).sort("A_HELMUSE"))
    print(src, "MC riders REST_USE codes 2016-18:", m.filter(c("YEAR") <= 2018).group_by("REST_USE").agg(pl.len()).sort("len", descending=True).head(8).to_dicts())
