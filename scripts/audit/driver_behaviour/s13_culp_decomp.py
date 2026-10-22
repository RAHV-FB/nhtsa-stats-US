"""Decompose culpability components by year in two-vehicle crashes; alternative definitions."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from s11_culpability import build, wp
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True)
for src in ["FARS", "CRSS"]:
    f, k = build(src)
    c = f.group_by(k).agg(pl.len().alias("nv"), (pl.col("DR_PRES") == 1).all().alias("bd"))
    t = f.join(c.filter((pl.col("nv") == 2) & pl.col("bd")), on=k).filter(pl.col("PEDS") == 0)
    print(f"#### {src}: driver-level component prevalence in 2-veh crashes by year (%)")
    print(t.group_by("YEAR").agg(wp(pl.col("sp_yes")).alias("speed"), wp(pl.col("pc") == "own_error").alias("pc_culp"),
                                 wp(pl.col("drf_err")).alias("drf_err"), wp(pl.col("lbdns").fill_null(False)).alias("lbdns"),
                                 wp(pl.col("drf_unk")).alias("drf_unk"), wp(pl.col("SPEEDREL") == 9).alias("speed_unk"),
                                 wp(pl.col("pc") == "unk").alias("pc_unk"), wp(pl.col("pc") == "nonmv").alias("pc_ambig"),
                                 wp(pl.col("c1") == "C").alias("c1_C")).sort("YEAR"))
    # drf error codes individually by year
    print(f"#### {src}: 2-veh crash exactly-one-culpable under alternative definitions (%)")
    t = t.with_columns(
        a0=pl.when(pl.col("pc") == "own_error").then(pl.lit("C")).when(pl.col("pc").is_in(["other", "own_neutral"])).then(pl.lit("N")).otherwise(pl.lit("U")),
        a1=pl.when((pl.col("pc") == "own_error") | pl.col("sp_yes")).then(pl.lit("C")).when(pl.col("pc").is_in(["other", "own_neutral"]) & pl.col("sp_no")).then(pl.lit("N")).otherwise(pl.lit("U")))
    rows = []
    for d in ["a0", "a1", "c1"]:
        cr = t.group_by(k).agg(nC=(pl.col(d) == "C").sum(), nN=(pl.col(d) == "N").sum(), W=pl.col("W").first(),
                               sev=(pl.col("MAX_SEV").first() if src == "CRSS" else pl.lit(4)))
        r = cr.group_by("YEAR").agg(wp((pl.col("nC") == 1) & (pl.col("nN") == 1)).alias(d)).sort("YEAR")
        rows.append(r)
    out = rows[0].join(rows[1], on="YEAR").join(rows[2], on="YEAR")
    print(out)
