"""per_aux cross-check: infer the (unlabelled) A_* codes by cross-tabulation with labelled person variables.
A_RESTUSE vs REST_USE/HELM_USE (+body class), A_HELMUSE vs REST_USE/HELM_USE, A_PTYPE vs PER_TYP,
A_PERINJ vs INJ_SEV, A_EJECT vs EJECTION, A_AGE1.. vs AGE (first two only), FARS A_HISP/A_HRACE/A_RCAT vs race.
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(80)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
src = sys.argv[1]
K = ["ST_CASE"] if src == "FARS" else ["CASENUM"]
p = load_table(src, "person", columns=K + ["VEH_NO", "PER_NO", "PER_TYP", "BODY_TYP", "INJ_SEV", "REST_USE", "HELM_USE", "EJECTION", "AGE"]
               + (["HISPANIC"] if src == "FARS" else []))
ax_cols = K + ["VEH_NO", "PER_NO", "A_RESTUSE", "A_HELMUSE", "A_PTYPE", "A_PERINJ", "A_EJECT", "A_AGE1", "A_AGE2"] + (
    ["A_HISP", "A_HRACE", "A_RCAT", "A_DOA"] if src == "FARS" else [])
a = load_table(src, "per_aux", columns=ax_cols)
j = p.join(a, on=["YEAR"] + K + ["VEH_NO", "PER_NO"], how="left")
print(f"### {src} per_aux match rate:", j.select(pl.col("A_PTYPE").is_not_null().mean()).item())
cls = (pl.when(pl.col("BODY_TYP").is_between(1, 49)).then(pl.lit("LPV")).when(pl.col("BODY_TYP").is_between(80, 89)).then(pl.lit("moto"))
       .when(pl.col("VEH_NO") == 0).then(pl.lit("nonocc")).otherwise(pl.lit("othveh")))
j = j.with_columns(cls.alias("cls"), pl.when(pl.col("YEAR") <= 2018).then(pl.lit("16-18")).otherwise(pl.lit("19+")).alias("era"))


def xt(a_, b_, by=None, flt=None):
    g = j if flt is None else j.filter(flt)
    keys = ([by] if by else []) + [b_, a_]
    t = g.group_by(keys).len().pivot(on=a_, index=([by] if by else []) + [b_], values="len", sort_columns=True).sort(([by] if by else []) + [b_])
    print(f"\n#### {src}: {b_} (rows) x {a_} (cols)" + (f" by {by}" if by else ""))
    print(t)


xt("A_RESTUSE", "REST_USE", by="era", flt=pl.col("cls") == "LPV")
xt("A_RESTUSE", "cls", by="era")
xt("A_HELMUSE", "REST_USE", by="era", flt=(pl.col("cls") == "moto") & (pl.col("YEAR") <= 2018))
xt("A_HELMUSE", "HELM_USE", flt=(pl.col("cls") == "moto") & (pl.col("YEAR") >= 2019))
xt("A_HELMUSE", "cls", by="era")
xt("A_PTYPE", "PER_TYP")
xt("A_PERINJ", "INJ_SEV")
xt("A_EJECT", "EJECTION")
# age groups: min/max AGE per A_AGE1 code
for c in ("A_AGE1", "A_AGE2"):
    print(f"\n#### {src}: AGE range per {c}")
    print(j.group_by(c).agg(pl.col("AGE").min().alias("min"), pl.col("AGE").filter(pl.col("AGE") < 990).max().alias("max_lt990"),
                            pl.col("AGE").is_in([998, 999]).sum().alias("n_unk"), pl.len()).sort(c))
if src == "FARS":
    xt("A_HISP", "HISPANIC")
    print(j.group_by(["A_HRACE"]).agg(pl.len(), (pl.col("INJ_SEV") == 4).mean().alias("p_fatal")).sort("A_HRACE"))
    print(j.group_by(["A_RCAT"]).agg(pl.len(), (pl.col("INJ_SEV") == 4).mean().alias("p_fatal")).sort("A_RCAT"))
