"""Where do the 2016-only 'Not Applicable' codes (REST_USE 0, AIR_BAG 0) sit, and what absorbs them in 2017?
LPV occupants, FARS and CRSS, by seat row and model year band."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_rows(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
for src in ("FARS", "CRSS"):
    p = load_table(src, "person", years=[2016, 2017], columns=["PER_TYP", "BODY_TYP", "SEAT_POS", "REST_USE", "AIR_BAG", "MOD_YEAR"])
    p = p.filter(pl.col("PER_TYP").is_in([1, 2, 9]) & pl.col("BODY_TYP").is_between(1, 49))
    row = (pl.when(pl.col("SEAT_POS").is_between(11, 19)).then(pl.lit("front")).when(pl.col("SEAT_POS").is_between(21, 49)).then(pl.lit("rear"))
           .when(pl.col("SEAT_POS").is_between(50, 56)).then(pl.lit("cargo/ext")).otherwise(pl.lit("unk")))
    p = p.with_columns(row.alias("row"), pl.when(pl.col("MOD_YEAR") < 1998).then(pl.lit("<1998")).when(pl.col("MOD_YEAR") <= 2030).then(pl.lit(">=1998")).otherwise(pl.lit("unk")).alias("my"))
    for var, codes in (("REST_USE", [0, 7, 20]), ("AIR_BAG", [0, 20])):
        t = p.group_by(["YEAR", "row", var]).len().with_columns((100 * pl.col("len") / pl.col("len").sum().over(["YEAR", "row"])).round(2).alias("pct"))
        print(f"### {src} {var} % within (year, seat row), codes {codes}")
        print(t.filter(pl.col(var).is_in(codes)).pivot(on=["YEAR", var], index="row", values="pct", sort_columns=True).sort("row"))
    t = p.group_by(["YEAR", "my", "AIR_BAG"]).len().with_columns((100 * pl.col("len") / pl.col("len").sum().over(["YEAR", "my"])).round(2).alias("pct"))
    print(f"### {src} AIR_BAG 0/20 % by model-year band")
    print(t.filter(pl.col("AIR_BAG").is_in([0, 20])).pivot(on=["YEAR", "AIR_BAG"], index="my", values="pct", sort_columns=True).sort("my"))
