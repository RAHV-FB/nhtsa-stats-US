import sys; sys.path.insert(0, "scripts/audit")
from helpers import *
c = pl.col
def bclass(e):
    return (pl.when(e.is_between(1, 13) | (e == 17)).then(1).when(e.is_between(30, 39)).then(2).when(e.is_between(14, 19)).then(3)
            .when(e.is_between(20, 29)).then(4).when(e.is_between(40, 49)).then(5).when(e.is_between(60, 64) | e.is_between(66, 79)).then(6)
            .when(e.is_between(80, 89)).then(7).when(e.is_between(50, 59)).then(8).otherwise(9))
for src in ["FARS", "CRSS"]:
    mc = ["BODY_TYP", "VPICBODYCLASS"] + (["BDYTYP_IM"] if src == "CRSS" else [])
    df = aux_main(src, "veh", ["A_BODY"], mc)
    df = df.with_columns(bclass(c("BODY_TYP")).alias("BC"))
    print(src, "agreement of BODY_TYP-only class with A_BODY by year")
    print(df.group_by("YEAR").agg((c("BC") == c("A_BODY")).mean().mul(100).round(2).alias("pct_agree"), pl.len()).sort("YEAR").transpose(include_header=True))
    print(src, "A_BODY=9 share by BODY_TYP group and year")
    print(df.group_by("YEAR").agg((c("A_BODY") == 9).mean().mul(100).round(2).alias("pct_A9"), (c("BC") == 9).mean().mul(100).round(2).alias("pct_BT_other_unknown"),
                                  (c("BODY_TYP").is_in([98, 99])).mean().mul(100).round(2).alias("pct_BT_98_99"), (c("BODY_TYP") == 9).mean().mul(100).round(2).alias("pct_BT9"),
                                  (c("BODY_TYP").is_in([49, 79])).mean().mul(100).round(2).alias("pct_BT49_79")).sort("YEAR"))
    print(src, "disagreements (A_BODY vs BODY_TYP class) top, 2020+ with VPICBODYCLASS")
    print(df.filter((c("BC") != c("A_BODY")) & (c("YEAR") >= 2020)).group_by(["BODY_TYP", "BC", "A_BODY", "VPICBODYCLASS"]).agg(pl.len()).sort("len", descending=True).head(25))
    print(df.filter((c("BC") != c("A_BODY")) & (c("YEAR") < 2020)).group_by(["BODY_TYP", "BC", "A_BODY"]).agg(pl.len()).sort("len", descending=True).head(15))
    if src == "CRSS":
        df = df.with_columns(bclass(c("BDYTYP_IM")).alias("BCI"))
        print("CRSS BDYTYP_IM class agreement by year", df.group_by("YEAR").agg((c("BCI") == c("A_BODY")).mean().mul(100).round(2).alias("pct")).sort("YEAR").to_dicts())
