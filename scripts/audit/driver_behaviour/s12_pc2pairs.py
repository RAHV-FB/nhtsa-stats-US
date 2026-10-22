"""P_CRASH2 code pairs in two-vehicle crashes (both drivers present, no non-motorists)."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import lt
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True)
for src in ["FARS", "CRSS"]:
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    v = lt(src, "vehicle", k + ["VEH_NO", "P_CRASH2", "DR_PRES", "ACC_TYPE"] + (["WEIGHT"] if src == "CRSS" else []))
    a = lt(src, "accident", k + ["PEDS"])
    v = v.join(a, on=k)
    c = v.group_by(k).agg(pl.len().alias("n"), (pl.col("DR_PRES") == 1).all().alias("bd"), pl.col("PEDS").first())
    v = v.join(c.filter((pl.col("n") == 2) & pl.col("bd") & (pl.col("PEDS") == 0)), on=k)
    v = v.with_columns(W=pl.col("WEIGHT") if src == "CRSS" else pl.lit(1.0))
    p = v.sort("P_CRASH2").group_by(k).agg(pl.col("P_CRASH2").cast(pl.Utf8).str.join("+").alias("pair"), pl.col("W").first())
    t = p.group_by("pair").agg(pl.len().alias("n"), pl.col("W").sum().alias("w")).with_columns((pl.col("w")/pl.col("w").sum()*100).round(2).alias("wpct")).sort("w", descending=True)
    print(src); print(t.head(40))
