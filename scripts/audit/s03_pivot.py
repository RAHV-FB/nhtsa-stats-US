"""Pivotability of multi-row tables: rows per vehicle and coexistence of none/unknown/NR with substantive codes."""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT

pl.Config.set_tbl_rows(200)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
for src in ["FARS", "CRSS"]:
    f = pl.read_parquet(f"{OUT}/frame_{src}.parquet")
    for p in ["dis", "imp", "fac", "man", "vio", "vis", "drt"]:
        g = f.filter(pl.col(f"{p}_nrows").is_not_null())
        r = g.group_by("YEAR").agg(
            pl.len().alias("veh"),
            (pl.col(f"{p}_nrows") > 1).mean().mul(100).round(2).alias("pct_multi"),
            pl.col(f"{p}_nrows").max().alias("max_rows"),
            (pl.col(f"{p}_has_none") & pl.col(f"{p}_has_S")).sum().alias("none&S"),
            (pl.col(f"{p}_has_unk") & pl.col(f"{p}_has_S")).sum().alias("unk&S"),
            (pl.col(f"{p}_has_nr") & (pl.col(f"{p}_has_S") | pl.col(f"{p}_has_none") | pl.col(f"{p}_has_unk"))).sum()
            .alias("nr&other"),
            (pl.col(f"{p}_has_none") & pl.col(f"{p}_has_unk")).sum().alias("none&unk"),
            (pl.col(f"{p}_has_nodrv") & (pl.col(f"{p}_nrows") > 1)).sum().alias("nodrv&multi"),
            # among multi-row vehicles: share all-substantive
            ((pl.col(f"{p}_nrows") > 1) & pl.col(f"{p}_has_S") & ~pl.col(f"{p}_has_none") & ~pl.col(f"{p}_has_unk")
             & ~pl.col(f"{p}_has_nr")).sum().alias("multi_allS"),
        ).sort("YEAR")
        print(f"\n== {src} {p}")
        print(r)
    # DR_SF wide 2016-19: n nonzero slots
    g = f.filter(pl.col("YEAR") <= 2019)
    print(f"\n== {src} DR_SF1-4 (2016-19) / driverrf (2020+) non-zero codes per vehicle")
    print(f.group_by("YEAR").agg(
        (pl.col("drf_n_nonzero") > 1).mean().mul(100).round(2).alias("pct_ge2_nonzero"),
        pl.col("drf_n_nonzero").max().alias("max_nonzero"),
        (pl.col("drf_has_S") & pl.col("drf_has_unk")).sum().alias("S&unk"),
    ).sort("YEAR"))
