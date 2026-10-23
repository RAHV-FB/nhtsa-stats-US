"""Unknown / not-reported rates of person variables by year and by person INJ_SEV (and CRSS crash MAX_SEV).

Populations:
  occ_lpv  : MV-in-transport occupants (PER_TYP 1,2,9) of light passenger vehicles (BODY_TYP 1-49)
  occ_all  : all MV-in-transport occupants (PER_TYP 1,2,9)
  moto     : occupants of BODY_TYP 80-89
  nonmot   : non-motorists (VEH_NO == 0)
  allp     : all persons
CRSS shares are WEIGHT-weighted; unweighted n is kept.
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

OUT = "outputs/cache/audit/out"
src = sys.argv[1]
K = ["ST_CASE"] if src == "FARS" else ["CASENUM"]
cols = K + ["VEH_NO", "PER_TYP", "BODY_TYP", "INJ_SEV", "AGE", "SEX", "SEAT_POS", "REST_USE", "REST_MIS",
            "HELM_USE", "AIR_BAG", "EJECTION", "HOSPITAL", "LOCATION"]
if src == "FARS":
    cols += ["EXTRICAT", "HISPANIC", "WORK_INJ", "DOA"]
else:
    cols += ["WEIGHT"]
p = load_table(src, "person", columns=cols)
if src == "FARS":
    p = p.with_columns(pl.lit(1.0).alias("WEIGHT"))
else:
    acc = load_table("CRSS", "accident", columns=["CASENUM", "MAX_SEV"])
    p = p.join(acc, on=["YEAR", "CASENUM"], how="left")

sevname = {0: "O", 1: "C", 2: "B", 3: "A", 4: "K", 5: "U5", 6: "D6", 9: "U9"}
p = p.with_columns(pl.col("INJ_SEV").replace_strict(sevname, default="?").alias("sev"))
if src == "CRSS":
    p = p.with_columns(pl.col("MAX_SEV").replace_strict({**sevname, 8: "N8"}, default="?").alias("crash_sev"))

occ = pl.col("PER_TYP").is_in([1, 2, 9])
lpv = pl.col("BODY_TYP").is_between(1, 49)
moto = pl.col("BODY_TYP").is_between(80, 89)
early = pl.col("YEAR") <= 2018
helm_src = pl.when(early).then(pl.col("REST_USE")).otherwise(pl.col("HELM_USE"))

# (name, population filter, "unknown" condition)
DEFS = [
    ("REST_USE unk(98,99)", occ & lpv, pl.col("REST_USE").is_in([98, 99])),
    ("REST_USE unk+other(97,98,99)", occ & lpv, pl.col("REST_USE").is_in([97, 98, 99])),
    ("REST_USE notrep(98)", occ & lpv, pl.col("REST_USE") == 98),
    ("REST_USE unk_all_occ(98,99)", occ & ~moto, pl.col("REST_USE").is_in([98, 99])),
    ("HELMET unk moto(29/98/99)", occ & moto, helm_src.is_in([29, 98, 99, 97])),
    ("AGE unk(998,999)", pl.lit(True), pl.col("AGE").is_in([998, 999])),
    ("SEX unk(8,9)", pl.lit(True), pl.col("SEX").is_in([8, 9])),
    ("SEAT_POS unk(98,99)", occ, pl.col("SEAT_POS").is_in([98, 99])),
    ("SEAT_POS unk incl row-unk(19,29,39,49,98,99)", occ, pl.col("SEAT_POS").is_in([19, 29, 39, 49, 98, 99])),
    ("AIR_BAG unk(98,99) lpv", occ & lpv, pl.col("AIR_BAG").is_in([98, 99])),
    ("EJECTION unk(7,9) occ", occ & ~moto, pl.col("EJECTION").is_in([7, 9])),
    ("HOSPITAL unk(8,9)", pl.lit(True), pl.col("HOSPITAL").is_in([8, 9])),
    ("LOCATION unk(98,99) nonmot", pl.col("VEH_NO") == 0, pl.col("LOCATION").is_in([98, 99])),
]
if src == "FARS":
    DEFS += [("EXTRICAT unk(9) occ", occ, pl.col("EXTRICAT") == 9),
             ("HISPANIC unk(99) fatal", pl.col("INJ_SEV") == 4, pl.col("HISPANIC") == 99),
             ("WORK_INJ unk(9) fatal", pl.col("INJ_SEV") == 4, pl.col("WORK_INJ") == 9)]

rows = []
for name, pop, unk in DEFS:
    g = p.filter(pop).with_columns(unk.fill_null(False).alias("u"))
    for by in (["YEAR", "sev"], ["sev"], ["YEAR"]) + ((["YEAR", "crash_sev"], ["crash_sev"]) if src == "CRSS" else ()):
        t = g.group_by(by).agg(pl.len().alias("n"), pl.col("u").sum().alias("n_unk"),
                               (pl.col("u") * pl.col("WEIGHT")).sum().alias("w_unk"), pl.col("WEIGHT").sum().alias("w"))
        t = t.with_columns((100 * pl.col("w_unk") / pl.col("w")).alias("pct"), pl.lit(name).alias("var"),
                           pl.lit("+".join(by)).alias("by"))
        for c in ("YEAR", "sev", "crash_sev"):
            if c not in t.columns:
                t = t.with_columns(pl.lit(None, dtype=pl.Utf8 if c != "YEAR" else pl.Int64).alias(c))
        rows.append(t.select(["var", "by", "YEAR", "sev", "crash_sev", "n", "n_unk", "pct"]))
res = pl.concat(rows)
res.write_csv(f"{OUT}/missing_by_sev_{src}.csv")

order = ["K", "A", "B", "C", "O", "U5", "U9", "D6"]
with pl.Config(tbl_rows=60, tbl_cols=20, tbl_width_chars=250):
    for name, _, _ in DEFS:
        t = res.filter((pl.col("var") == name) & (pl.col("by") == "YEAR+sev"))
        wide = t.pivot(on="sev", index="YEAR", values="pct").sort("YEAR")
        wide = wide.select(["YEAR"] + [c for c in order if c in wide.columns]).with_columns(pl.exclude("YEAR").round(2))
        pooled = res.filter((pl.col("var") == name) & (pl.col("by") == "sev"))
        print(f"\n### {src} {name}: % unknown by year x INJ_SEV")
        print(wide)
        print("  pooled:", {r["sev"]: (round(r["pct"], 2), r["n"]) for r in pooled.sort("sev").iter_rows(named=True)})
        if src == "CRSS":
            t2 = res.filter((pl.col("var") == name) & (pl.col("by") == "crash_sev"))
            print("  by crash MAX_SEV pooled:", {r["crash_sev"]: (round(r["pct"], 2), r["n"]) for r in t2.sort("crash_sev").iter_rows(named=True)})
