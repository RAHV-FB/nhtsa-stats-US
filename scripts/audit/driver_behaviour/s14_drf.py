"""Driver-related factors: DR_SF1-4 (2016-19) vs driverrf (2020+): slot saturation, code prevalence per driver, LBDNS mapping."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import lt, OUT
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_hide_dataframe_shape(True); pl.Config.set_tbl_hide_column_data_types(True)
CODES = [6, 8, 10, 26, 27, 28, 36, 37, 38, 39, 48, 51, 58, 60, 89, 91, 99, 999]
for src in ["FARS", "CRSS"]:
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    v = lt(src, "vehicle", k + ["VEH_NO", "DR_PRES", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"] + (["WEIGHT"] if src == "CRSS" else []))
    v = v.filter(pl.col("DR_PRES") == 1).with_columns(W=pl.col("WEIGHT") if src == "CRSS" else pl.lit(1.0))
    old = v.filter(pl.col("YEAR") <= 2019)
    print(f"#### {src} DR_SF slot fill 2016-19 (% of drivers): n non-zero slots")
    old = old.with_columns(nz=sum([(pl.col(c).fill_null(0) != 0).cast(pl.Int32) for c in ["DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"]]))
    print(old.group_by("YEAR").agg([((pl.col("nz") == i).cast(pl.Float64) * pl.col("W")).sum().truediv(pl.col("W").sum()).mul(100).round(3).alias(f"nz{i}") for i in range(5)]).sort("YEAR"))
    # are slots filled in order? any DR_SF2 nonzero while DR_SF1 zero?
    print("out-of-order slots (SF1==0 & SF2!=0):", old.filter((pl.col("DR_SF1") == 0) & (pl.col("DR_SF2") != 0)).height)
    lng = old.unpivot(index=k + ["VEH_NO", "W"], on=["DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"], value_name="code").select(k + ["VEH_NO", "W", pl.col("code").cast(pl.Int64)])
    d = lt(src, "driverrf", k + ["VEH_NO", "DRIVERRF"], years=list(range(2020, 2025))).rename({"DRIVERRF": "code"})
    dv = v.filter(pl.col("YEAR") >= 2020).select(k + ["VEH_NO", "W"])
    d = d.join(dv, on=k + ["VEH_NO"], how="inner").select(k + ["VEH_NO", "W", pl.col("code").cast(pl.Int64)])
    print(f"{src} driverrf rows per driver 2020+: max", d.group_by(k + ["VEH_NO"]).len()["len"].max(), "; drivers with >=5 non-zero codes:", d.filter(pl.col("code") != 0).group_by(k + ["VEH_NO"]).len().filter(pl.col("len") >= 5).height)
    lng = pl.concat([lng, d])
    per = lng.group_by(k + ["VEH_NO"]).agg(pl.col("W").first(), *[(pl.col("code") == c).any().alias(f"c{c}") for c in CODES],
                                         (pl.col("code").is_in([0])).all().alias("none_only"),
                                         ((pl.col("code") != 0) & ~pl.col("code").is_in([99, 999])).any().alias("any_subst"))
    print(f"#### {src} % drivers with code (driver-present)")
    print(per.group_by("YEAR").agg([((pl.col(c).cast(pl.Float64) * pl.col("W")).sum() / pl.col("W").sum() * 100).round(2).alias(c) for c in ["none_only", "any_subst"] + [f"c{c}" for c in CODES]]).sort("YEAR"))
# LBDNS mapping: 2018-19 FARS/CRSS drivers with DR_SF=10: distract code distribution
for src in ["FARS", "CRSS"]:
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    v = lt(src, "vehicle", k + ["VEH_NO", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"], years=[2018, 2019])
    v = v.filter(pl.any_horizontal([pl.col(c) == 10 for c in ["DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"]]))
    dis = lt(src, "distract", k + ["VEH_NO", "MDRDSTRD"], years=[2018, 2019]).unique()
    x = v.join(dis, on=k + ["VEH_NO"])
    print(f"#### {src} 2018-19 drivers with DR_SF=10 (looked but did not see): MDRDSTRD codes")
    print(x.group_by("MDRDSTRD").len().sort("len", descending=True).head(8))
