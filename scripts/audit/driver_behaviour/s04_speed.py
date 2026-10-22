"""SPEEDREL: distributions, unknown rates by severity, TRAV_SP/VSPD_LIM availability and validation."""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT

pl.Config.set_tbl_rows(300)
pl.Config.set_tbl_cols(40)
pl.Config.set_tbl_width_chars(300)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_tbl_hide_column_data_types(True)


def wmean(expr, w="W"):
    return ((expr.cast(pl.Float64) * pl.col(w)).sum() / pl.col(w).sum() * 100).round(2)


SEV = {0: "O", 1: "C", 2: "B", 3: "A", 4: "K"}


def prep(src):
    f = pl.read_parquet(f"{OUT}/frame_{src}.parquet")
    f = f.with_columns(W=pl.col("WEIGHT") if src == "CRSS" else pl.lit(1.0))
    f = f.with_columns(
        sr_yes=pl.col("SPEEDREL").is_in([2, 3, 4, 5]),
        sr_unk=pl.col("SPEEDREL") == 9,
        sr_nodrv=pl.col("SPEEDREL") == 8,
        ts_known=pl.col("TRAV_SP").is_between(1, 151) | (pl.col("TRAV_SP") == 997),
        ts_stopped=pl.col("TRAV_SP") == 0,
        ts_nr=pl.col("TRAV_SP") == 998,
        ts_unk=pl.col("TRAV_SP") == 999,
        sl_known=pl.col("VSPD_LIM").is_between(5, 95),
        drv_sev=pl.col("DRV_INJ_SEV").replace_strict(SEV, default="unk/other", return_dtype=pl.Utf8),
        drv_present=pl.col("DR_PRES") == 1,
    )
    if src == "CRSS":
        f = f.with_columns(crash_sev=pl.col("MAX_SEV").replace_strict(SEV, default="unk/other", return_dtype=pl.Utf8))
    else:
        f = f.with_columns(
            crash_sev=pl.when(pl.col("DRV_INJ_SEV") == 4).then(pl.lit("drv_killed"))
            .when(pl.col("DRV_INJ_SEV").is_in([0, 1, 2, 3, 5])).then(pl.lit("drv_survived"))
            .otherwise(pl.lit("drv_inj_unk")))
    return f


for src in ["FARS", "CRSS"]:
    f = prep(src)
    d = f.filter(pl.col("drv_present"))
    print(f"\n######## {src}: SPEEDREL among driver-present vehicles (DR_PRES=1), {'weighted %' if src=='CRSS' else '%'}")
    print(d.group_by("YEAR").agg(pl.len().alias("n"), wmean(pl.col("sr_yes")).alias("yes"),
                                 wmean(pl.col("sr_unk")).alias("unk9"), wmean(pl.col("sr_nodrv")).alias("code8"),
                                 wmean(pl.col("SPEEDREL") == 3).alias("exceeded"),
                                 wmean(pl.col("SPEEDREL") == 4).alias("toofast"),
                                 wmean(pl.col("SPEEDREL") == 5).alias("spec_unk"),
                                 wmean(pl.col("SPEEDREL") == 2).alias("racing")).sort("YEAR"))
    print(f"--- {src}: DR_PRES x SPEEDREL=8 cross-tab (unweighted)")
    print(f.group_by("DR_PRES", "SPEEDREL").len().filter(pl.col("SPEEDREL") == 8 | pl.col("DR_PRES").ne(1)).sort("DR_PRES", "SPEEDREL"))
    print(f"--- {src}: SPEEDREL yes / unknown by severity, pooled years, by period")
    for per, cond in [("2016-19", pl.col("YEAR") <= 2019), ("2020-24", pl.col("YEAR") >= 2020)]:
        print(per)
        print(d.filter(cond).group_by("crash_sev").agg(pl.len().alias("n"), wmean(pl.col("sr_yes")).alias("yes"),
                                                       wmean(pl.col("sr_unk")).alias("unk9"),
                                                       wmean(pl.col("ts_known")).alias("TRAV_SP_known"),
                                                       wmean(pl.col("ts_stopped")).alias("TRAV_SP_0"),
                                                       wmean(pl.col("ts_nr")).alias("TRAV_SP_NR"),
                                                       wmean(pl.col("ts_unk")).alias("TRAV_SP_unk"),
                                                       wmean(pl.col("sl_known")).alias("VSPD_LIM_known"),
                                                       ).sort("crash_sev"))
    print(f"--- {src}: by driver injury severity (pooled 2016-24)")
    print(d.group_by("drv_sev").agg(pl.len().alias("n"), wmean(pl.col("sr_yes")).alias("yes"),
                                    wmean(pl.col("sr_unk")).alias("unk9"), wmean(pl.col("ts_known")).alias("TRAV_SP_known"),
                                    ).sort("drv_sev"))
    print(f"--- {src}: per-year unknown(9) by severity")
    print(d.group_by("YEAR", "crash_sev").agg(wmean(pl.col("sr_unk")).alias("unk9")).pivot(
        on="crash_sev", index="YEAR", values="unk9").sort("YEAR"))
    print(f"--- {src}: per-year yes by severity")
    print(d.group_by("YEAR", "crash_sev").agg(wmean(pl.col("sr_yes")).alias("yes")).pivot(
        on="crash_sev", index="YEAR", values="yes").sort("YEAR"))
    print(f"--- {src}: per-year TRAV_SP known (1-151/997) by severity")
    print(d.group_by("YEAR", "crash_sev").agg(wmean(pl.col("ts_known")).alias("k")).pivot(
        on="crash_sev", index="YEAR", values="k").sort("YEAR"))

    # validation: both known, moving
    v = d.filter(pl.col("ts_known") & pl.col("sl_known") & (pl.col("TRAV_SP") != 997))
    v = v.with_columns(over=pl.col("TRAV_SP") - pl.col("VSPD_LIM"))
    print(f"--- {src}: among TRAV_SP & VSPD_LIM known: share TRAV_SP > VSPD_LIM, >= +10, by SPEEDREL code (pooled)")
    print(v.group_by("SPEEDREL").agg(pl.len().alias("n"), wmean(pl.col("over") > 0).alias("over0"),
                                    wmean(pl.col("over") >= 10).alias("over10"),
                                    wmean(pl.col("over") >= 20).alias("over20"),
                                    pl.col("over").median().alias("med_over")).sort("SPEEDREL"))
    vb = v.with_columns(ob=pl.col("over").cut([-1, 0, 4, 9, 14, 19, 29], labels=["<=-1", "0", "1-4", "5-9", "10-14",
                                                                                   "15-19", "20-29", ">=30"]))
    print(f"--- {src}: SPEEDREL yes/unk by (TRAV_SP - VSPD_LIM) bin")
    print(vb.group_by("ob").agg(pl.len().alias("n"), wmean(pl.col("sr_yes")).alias("yes"),
                                wmean(pl.col("SPEEDREL") == 3).alias("exceeded"),
                                wmean(pl.col("sr_unk")).alias("unk9")).sort("ob"))
    # rounding / heaping
    print(f"--- {src}: TRAV_SP heaping: share of known speeds that are multiples of 5")
    print(d.filter(pl.col("ts_known") & (pl.col("TRAV_SP") != 997)).group_by("YEAR").agg(
        wmean(pl.col("TRAV_SP") % 5 == 0).alias("mult5"), wmean(pl.col("TRAV_SP") == pl.col("VSPD_LIM")).alias("eq_limit")
    ).sort("YEAR"))
    # speeding by known/unknown TRAV_SP
    print(f"--- {src}: SPEEDREL yes by TRAV_SP status (pooled)")
    print(d.with_columns(ts=pl.when(pl.col("ts_known")).then(pl.lit("known")).when(pl.col("ts_stopped")).then(
        pl.lit("stopped")).when(pl.col("ts_nr")).then(pl.lit("NR")).when(pl.col("ts_unk")).then(pl.lit("unk"))
                         .otherwise(pl.lit("other"))).group_by("ts").agg(
        pl.len().alias("n"), wmean(pl.col("sr_yes")).alias("yes"), wmean(pl.col("sr_unk")).alias("unk9")).sort("ts"))
    if src == "FARS":
        print("--- FARS: SPEEDREL yes/unk by state (pooled, top/bottom 8 by unk)")
        s = d.group_by("STATE").agg(pl.len().alias("n"), wmean(pl.col("sr_yes")).alias("yes"),
                                    wmean(pl.col("sr_unk")).alias("unk9"), wmean(pl.col("ts_known")).alias("ts_known")).sort("unk9")
        print(s.head(8))
        print(s.tail(8))
        print("quantiles of state yes%:", s["yes"].quantile(0.1), s["yes"].median(), s["yes"].quantile(0.9))
        print("quantiles of state TRAV_SP known%:", s["ts_known"].quantile(0.1), s["ts_known"].median(), s["ts_known"].quantile(0.9))
