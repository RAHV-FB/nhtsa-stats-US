"""Distraction / impairment / other multi-row tables: per-vehicle category shares, by year, by severity, by state."""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT

pl.Config.set_tbl_rows(300)
pl.Config.set_tbl_cols(40)
pl.Config.set_tbl_width_chars(300)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_tbl_hide_column_data_types(True)
SEV = {0: "O", 1: "C", 2: "B", 3: "A", 4: "K"}


def w(expr):
    return ((expr.cast(pl.Float64) * pl.col("W")).sum() / pl.col("W").sum() * 100).round(2)


def cat(p):
    return (pl.when(pl.col(f"{p}_has_nodrv")).then(pl.lit("nodrv"))
            .when(pl.col(f"{p}_has_S")).then(pl.lit("S"))
            .when(pl.col(f"{p}_has_unk")).then(pl.lit("unk"))
            .when(pl.col(f"{p}_has_nr")).then(pl.lit("nr"))
            .when(pl.col(f"{p}_has_none")).then(pl.lit("none")).otherwise(pl.lit("?")))


which = sys.argv[1:] or ["FARS", "CRSS"]
for src in which:
    f = pl.read_parquet(f"{OUT}/frame_{src}.parquet")
    f = f.with_columns(W=pl.col("WEIGHT") if src == "CRSS" else pl.lit(1.0))
    if src == "CRSS":
        f = f.with_columns(sev=pl.col("MAX_SEV").replace_strict(SEV, default="unk", return_dtype=pl.Utf8))
    else:
        f = f.with_columns(sev=pl.when(pl.col("DRV_INJ_SEV") == 4).then(pl.lit("killed"))
                           .when(pl.col("DRV_INJ_SEV").is_in([0, 1, 2, 3, 5])).then(pl.lit("survived"))
                           .otherwise(pl.lit("unk")))
    d = f.filter(pl.col("DR_PRES") == 1)
    for p in ["dis", "imp", "vio", "vis", "man", "fac", "drt"]:
        dd = d.filter(pl.col(f"{p}_nrows").is_not_null()).with_columns(c=cat(p))
        print(f"\n######## {src} {p}: category shares among driver-present vehicles ({'wtd' if src=='CRSS' else 'unwtd'} %)")
        print(dd.group_by("YEAR").agg([w(pl.col("c") == c).alias(c) for c in ["S", "none", "unk", "nr", "nodrv"]]
                                      + [(w(pl.col("c") == "S") / (w(pl.col("c") == "S") + w(pl.col("c") == "none")) * 100)
                                         .round(2).alias("S/(S+none)")]).sort("YEAR"))
        print(f"--- by severity, 2016-19 vs 2020-24")
        for per, cond in [("2016-19", pl.col("YEAR") <= 2019), ("2020-24", pl.col("YEAR") >= 2020)]:
            x = dd.filter(cond)
            if x.height == 0:
                continue
            print(per)
            print(x.group_by("sev").agg([pl.len().alias("n")] + [w(pl.col("c") == c).alias(c) for c in ["S", "none", "unk", "nr"]]
                                        + [(w(pl.col("c") == "S") / (w(pl.col("c") == "S") + w(pl.col("c") == "none")) * 100)
                                           .round(2).alias("S/(S+none)")]).sort("sev"))
    # specific flags by year
    flags = ["dis_any_subst_excl1", "dis_lookedbutdidnotsee", "dis_phone", "imp_asleep", "imp_ill", "imp_emotional",
             "imp_influence", "imp_physical", "vio_speed", "vio_dwi", "vio_license", "vio_hitrun", "vio_homicide",
             "vio_reckless_careless", "vio_moving_rules", "vis_obscured", "man_avoid", "fac_any"]
    print(f"\n######## {src} specific flags (% of driver-present vehicles)")
    print(d.group_by("YEAR").agg([w(pl.col(c)).alias(c.replace("dis_", "d_").replace("imp_", "i_").replace("vio_", "v_"))
                                  for c in flags]).sort("YEAR"))
    print(f"--- {src} specific flags by severity (pooled 2016-24)")
    print(d.group_by("sev").agg([w(pl.col(c)).alias(c.replace("dis_", "d_").replace("imp_", "i_").replace("vio_", "v_"))
                                 for c in flags]).sort("sev"))
    if src == "FARS":
        # state x year Not Reported shares for distract and drimpair
        for p in ["dis", "imp", "man"]:
            s = d.with_columns(c=cat(p)).group_by("STATE", "YEAR").agg(w(pl.col("c") == "nr").alias("nr")).pivot(
                on="YEAR", index="STATE", values="nr", sort_columns=True).sort("STATE")
            print(f"\n--- FARS {p} %NotReported by state x year")
            print(s)
            yrs = [c for c in s.columns if c != "STATE"]
            # count states with NR<5% and >50%
            print("states with NR<5%:", {y: int((s[y] < 5).sum()) for y in yrs})
            print("states with NR>50%:", {y: int((s[y] > 50).sum()) for y in yrs})
            print("states with NR>90%:", {y: int((s[y] > 90).sum()) for y in yrs})
    else:
        for p in ["dis", "imp"]:
            s = d.with_columns(c=cat(p)).group_by("PSU", "YEAR").agg(pl.len().alias("n"), w(pl.col("c") == "nr").alias("nr"))
            s = s.filter(pl.col("n") >= 200)
            print(f"\n--- CRSS {p}: distribution of PSU-level %NR by year (PSUs with >=200 vehicles)")
            print(s.group_by("YEAR").agg(pl.len().alias("nPSU"), pl.col("nr").quantile(0.1).alias("p10"),
                                         pl.col("nr").median().alias("p50"), pl.col("nr").quantile(0.9).alias("p90"),
                                         (pl.col("nr") < 5).sum().alias("lt5"), (pl.col("nr") > 90).sum().alias("gt90")).sort("YEAR"))
