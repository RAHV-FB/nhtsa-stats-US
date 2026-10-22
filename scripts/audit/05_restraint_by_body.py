"""Cross-tab REST_USE / HELM_USE / AIR_BAG / EJECTION by vehicle class (person.BODY_TYP) and year.

Vehicle class from BODY_TYP: 1-49 light passenger vehicle (LPV), 50-59 bus, 60-79 medium/heavy truck,
80-89 motorcycle/moped, 90-97 other (ATV, snowmobile, farm, LSV, golf cart, ROV...), 98/99 unknown.
Only occupants (VEH_NO > 0).
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

src = sys.argv[1]
w = ["WEIGHT"] if src == "CRSS" else []
p = load_table(src, "person", columns=["VEH_NO", "PER_TYP", "BODY_TYP", "REST_USE", "HELM_USE", "AIR_BAG", "EJECTION", "SEAT_POS"] + w)
p = p.filter(pl.col("VEH_NO") > 0)
if src == "FARS":
    p = p.with_columns(pl.lit(1.0).alias("WEIGHT"))
cls = (pl.when(pl.col("BODY_TYP").is_between(1, 49)).then(pl.lit("LPV"))
       .when(pl.col("BODY_TYP").is_between(50, 59)).then(pl.lit("bus"))
       .when(pl.col("BODY_TYP").is_between(60, 79)).then(pl.lit("MHtruck"))
       .when(pl.col("BODY_TYP").is_between(80, 89)).then(pl.lit("moto"))
       .when(pl.col("BODY_TYP").is_between(90, 97)).then(pl.lit("other"))
       .otherwise(pl.lit("unk")))
p = p.with_columns(cls.alias("cls"))


def tab(var, years, cond=None, top=None):
    g = p.filter(pl.col("YEAR").is_in(years))
    if cond is not None:
        g = g.filter(cond)
    t = g.group_by(["YEAR", "cls", var]).agg(pl.col("WEIGHT").sum().alias("w"))
    t = t.with_columns((100 * pl.col("w") / pl.col("w").sum().over(["YEAR", "cls"])).round(2).alias("pct"))
    wide = t.pivot(on=["YEAR", "cls"], index=var, values="pct", sort_columns=True).sort(var).fill_null(0)
    with pl.Config(tbl_rows=100, tbl_cols=40, tbl_width_chars=300):
        print(f"\n#### {src} {var} % within (year, class); years={years}")
        print(wide)


tab("REST_USE", [2016, 2017, 2018, 2019, 2024])
tab("HELM_USE", [2019, 2024])
tab("AIR_BAG", [2016, 2017, 2024])
tab("EJECTION", [2016, 2024])
# class distribution
print(p.group_by(["YEAR", "cls"]).len().pivot(on="cls", index="YEAR", values="len").sort("YEAR"))
