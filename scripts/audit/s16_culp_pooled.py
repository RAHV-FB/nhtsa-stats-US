"""Pooled C1 culpability pair shares, CRSS weighted, by period and severity; FARS by killed-driver count."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from s11_culpability import build, wp
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True)
for src in ["FARS", "CRSS"]:
    f, k = build(src)
    c = f.group_by(k).agg(pl.len().alias("nv"), (pl.col("DR_PRES") == 1).all().alias("bd"), (pl.col("HIT_RUN") == 1).any().alias("hr"))
    t = f.join(c.filter((pl.col("nv") == 2) & pl.col("bd")), on=k).filter(pl.col("PEDS") == 0)
    cr = t.group_by(k).agg(nC=(pl.col("c1") == "C").sum(), nN=(pl.col("c1") == "N").sum(), W=pl.col("W").first(), hr=pl.col("hr").first(),
                           sev=(pl.col("MAX_SEV").first() if src == "CRSS" else (pl.col("DRV_INJ_SEV") == 4).sum()))
    cr = cr.with_columns(pat=pl.when((pl.col("nC") == 1) & (pl.col("nN") == 1)).then(pl.lit("1C+1N")).when(pl.col("nC") == 2).then(pl.lit("2C")).when(pl.col("nN") == 2).then(pl.lit("2N")).otherwise(pl.lit("U")),
                         per=pl.when(pl.col("YEAR") <= 2019).then(pl.lit("2016-19")).otherwise(pl.lit("2020-24")))
    agg = [pl.len().alias("n")] + [wp(pl.col("pat") == p).alias(p) for p in ["1C+1N", "2C", "2N", "U"]]
    print(f"### {src} pooled"); print(cr.select(agg))
    print(f"### {src} by period"); print(cr.group_by("per").agg(agg).sort("per"))
    print(f"### {src} by hit-and-run"); print(cr.group_by("hr").agg(agg).sort("hr"))
    print(f"### {src} by severity ({'MAX_SEV' if src=='CRSS' else 'number of killed drivers'}) x period"); print(cr.group_by("sev", "per").agg(agg).sort("sev", "per"))
