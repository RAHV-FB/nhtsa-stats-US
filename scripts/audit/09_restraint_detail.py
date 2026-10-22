"""Restraint detail: REST_MIS x REST_USE, HELM_MIS x HELM_USE, harmonised restraint by INJ_SEV and year
(LPV occupants), driver vs passenger, belted share among known.
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(80)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
OUT = "/tmp/nhtsa-audit/out"
src = sys.argv[1]
w = ["WEIGHT"] if src == "CRSS" else []
p = load_table(src, "person", columns=["VEH_NO", "PER_TYP", "BODY_TYP", "INJ_SEV", "REST_USE", "REST_MIS", "HELM_USE", "HELM_MIS", "AGE"] + w)
if src == "FARS":
    p = p.with_columns(pl.lit(1.0).alias("WEIGHT"))

R = (pl.when(pl.col("REST_USE").is_in([1, 2, 3, 8, 6])).then(pl.lit("belted"))
     .when(pl.col("REST_USE").is_in([4, 10, 11, 12])).then(pl.lit("child"))
     .when(pl.col("REST_USE").is_in([7, 20])).then(pl.lit("none"))
     .when(pl.col("REST_USE") == 0).then(pl.lit("na0"))
     .when(pl.col("REST_USE").is_in([5, 16, 17, 19, 29])).then(pl.lit("helmetcode"))
     .when(pl.col("REST_USE") == 96).then(pl.lit("nonocc"))
     .when(pl.col("REST_USE") == 97).then(pl.lit("other97"))
     .when(pl.col("REST_USE").is_in([98, 99])).then(pl.lit("unknown"))
     .otherwise(pl.lit("??")))
p = p.with_columns(R.alias("r"), pl.when(pl.col("YEAR") == 2016).then(pl.lit("2016")).when(pl.col("YEAR") <= 2018).then(pl.lit("2017-18"))
                   .otherwise(pl.lit("2019+")).alias("era"))

print(f"### {src} REST_MIS x harmonised REST_USE by era (row counts)")
print(p.group_by(["era", "r", "REST_MIS"]).len().pivot(on="REST_MIS", index=["era", "r"], values="len", sort_columns=True).sort(["era", "r"]))
print(f"### {src} HELM_MIS x HELM_USE (2019+)")
print(p.filter(pl.col("YEAR") >= 2019).group_by(["HELM_USE", "HELM_MIS"]).len().pivot(on="HELM_MIS", index="HELM_USE", values="len", sort_columns=True).sort("HELM_USE"))

occ = p.filter(pl.col("PER_TYP").is_in([1, 2, 9]) & pl.col("BODY_TYP").is_between(1, 49))
sev = {0: "O", 1: "C", 2: "B", 3: "A", 4: "K", 5: "U5", 6: "D6", 9: "U9"}
occ = occ.with_columns(pl.col("INJ_SEV").replace_strict(sev, default="?").alias("sev"))
# harmonised restraint distribution (weighted %) by INJ_SEV pooled & by year
t = occ.group_by(["sev", "r"]).agg(pl.col("WEIGHT").sum().alias("w"), pl.len().alias("n"))
t = t.with_columns((100 * pl.col("w") / pl.col("w").sum().over("sev")).round(2).alias("pct"))
print(f"### {src} LPV occupants: harmonised restraint % by INJ_SEV (pooled 2016-2024)")
print(t.pivot(on="sev", index="r", values="pct").select(["r"] + [c for c in ["K", "A", "B", "C", "O", "U5", "U9"]]).sort("r"))
# belted share among known (belted + child + none) by year x sev  (adult >= 13 to avoid child seats)
k = occ.filter(pl.col("r").is_in(["belted", "child", "none"]))
b = k.group_by(["YEAR", "sev"]).agg(((pl.col("r") != "none") * pl.col("WEIGHT")).sum() / pl.col("WEIGHT").sum() * 100)
b = b.rename({b.columns[-1]: "pct_restrained"})
print(f"### {src} LPV occupants: % restrained (belt or child seat) among known restraint, by year x INJ_SEV")
print(b.with_columns(pl.col("pct_restrained").round(2)).pivot(on="sev", index="YEAR", values="pct_restrained").select(
    ["YEAR"] + [c for c in ["K", "A", "B", "C", "O", "U5", "U9"]]).sort("YEAR"))
# drivers vs passengers unknown by sev
d = occ.with_columns((pl.col("r") == "unknown").alias("u")).group_by(["PER_TYP", "sev"]).agg(
    ((pl.col("u") * pl.col("WEIGHT")).sum() / pl.col("WEIGHT").sum() * 100).round(2).alias("pct_unk"), pl.len().alias("n"))
print(f"### {src} LPV occupants: % restraint unknown by PER_TYP x INJ_SEV (pooled)")
print(d.pivot(on="sev", index="PER_TYP", values="pct_unk").select(["PER_TYP"] + ["K", "A", "B", "C", "O", "U5", "U9"]).sort("PER_TYP"))
occ.group_by(["YEAR", "sev", "r"]).agg(pl.col("WEIGHT").sum().alias("w"), pl.len().alias("n")).write_csv(f"{OUT}/restraint_by_sev_{src}.csv")
