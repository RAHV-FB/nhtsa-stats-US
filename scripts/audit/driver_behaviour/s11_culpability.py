"""Culpability (at-fault) indicator for quasi-induced exposure in two-vehicle crashes, FARS & CRSS 2016-2024.

Definitions (driver = in-transport vehicle with DR_PRES=1):
  P_CRASH2 classes: 'own_error'  = {6,8,9,10..17,19,20,21,50,51,52} (this vehicle's control loss / travel / turning event,
                                   or this vehicle struck a stopped/slower/decelerating vehicle in its own lane)
                    'own_neutral'= {1,2,3,4,5,18} (vehicle failure, road condition, this vehicle decelerating)
                    'other'      = {53,55,56,60..78} (other MV struck from behind / encroached / backing)
                    'nonmv'      = {80..92} and ambiguous {54,59}; 'unk' = {98,99}
  Driver-related factor error codes common to FARS and CRSS all years:
      {6, 8, 102, 103, 36, 50, 51, 58} + looked-but-did-not-see (distract 1 in 2016-17; DR_SF/DRIVERRF 10 2018+)
  C1 (action-based) culpable = SPEEDREL in 2-5 OR P_CRASH2 own_error OR drf error
      non-culpable = not culpable AND SPEEDREL==0 AND P_CRASH2 in other/own_neutral AND drf not unknown
      undetermined = otherwise
  C2 = C1 + driver state: DRIMPAIR in {1,2,9} or distracted (A_DRDIS set) -> culpable; DRIMPAIR/distract
       unknown/NR do NOT block non-culpable (reported separately as C2strict where they do)
  C3 = C1 + moving/speed/DWI/reckless violation charged
"""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT, lt

pl.Config.set_tbl_rows(200)
pl.Config.set_tbl_cols(40)
pl.Config.set_tbl_width_chars(300)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_tbl_hide_column_data_types(True)
OWN_ERR = [6, 8, 9] + list(range(10, 18)) + [19, 20, 21] + [50, 51, 52]  # 50-52: struck vehicle ahead in own lane
OWN_NEU = [1, 2, 3, 4, 5, 18]
OTHER = [53, 55, 56] + list(range(60, 79))  # other vehicle struck this one from behind / encroached
NONMV = list(range(80, 93)) + [54, 59]  # treated as ambiguous (not usable as evidence either way)
DRF_ERR = [6, 8, 102, 103, 36, 50, 51, 58]


def build(src):
    k = ["YEAR", "ST_CASE"] if src == "FARS" else ["YEAR", "CASENUM"]
    f = pl.read_parquet(f"{OUT}/frame_{src}.parquet")
    pc = lt(src, "vehicle", k + ["VEH_NO", "P_CRASH2", "P_CRASH1", "ACC_TYPE"])
    f = f.join(pc, on=k + ["VEH_NO"], how="left")
    # driver-related factor error codes, long form
    v = lt(src, "vehicle", k + ["VEH_NO", "DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"], years=[2016, 2017, 2018, 2019])
    lng = v.unpivot(index=k + ["VEH_NO"], on=["DR_SF1", "DR_SF2", "DR_SF3", "DR_SF4"], value_name="code").drop("variable")
    d = lt(src, "driverrf", k + ["VEH_NO", "DRIVERRF"], years=list(range(2020, 2025))).rename({"DRIVERRF": "code"})
    lng = pl.concat([lng.select(k + ["VEH_NO", pl.col("code").cast(pl.Int64)]), d.select(k + ["VEH_NO", pl.col("code").cast(pl.Int64)])])
    drf = lng.group_by(k + ["VEH_NO"]).agg(drf_err=pl.col("code").is_in(DRF_ERR).any(),
                                          drf_lbdns=(pl.col("code") == 10).any(),
                                          drf_unk=pl.col("code").is_in([99, 999]).any())
    f = f.drop([c for c in f.columns if c.startswith("drf_")]).join(drf, on=k + ["VEH_NO"], how="left")
    w = pl.col("WEIGHT") if src == "CRSS" else pl.lit(1.0)
    f = f.with_columns(
        W=w,
        lbdns=pl.when(pl.col("YEAR") <= 2017).then(pl.col("dis_lookedbutdidnotsee")).otherwise(pl.col("drf_lbdns")),
        pc=pl.when(pl.col("P_CRASH2").is_in(OWN_ERR)).then(pl.lit("own_error"))
        .when(pl.col("P_CRASH2").is_in(OWN_NEU)).then(pl.lit("own_neutral"))
        .when(pl.col("P_CRASH2").is_in(OTHER)).then(pl.lit("other"))
        .when(pl.col("P_CRASH2").is_in(NONMV)).then(pl.lit("nonmv")).otherwise(pl.lit("unk")),
        sp_yes=pl.col("SPEEDREL").is_in([2, 3, 4, 5]), sp_no=pl.col("SPEEDREL") == 0,
        state=pl.col("imp_asleep") | pl.col("imp_ill") | pl.col("imp_influence") | pl.col("dis_any_subst_excl1"),
        state_unk=pl.col("dis_has_unk") | pl.col("dis_has_nr") | pl.col("imp_has_unk") | pl.col("imp_has_nr"),
        vio=pl.col("vio_moving_rules") | pl.col("vio_speed") | pl.col("vio_reckless_careless") | pl.col("vio_dwi"),
        vio_unk=pl.col("vio_has_unk") | pl.col("vio_has_nr"),
    )
    f = f.with_columns(
        c1_cul=pl.col("sp_yes") | (pl.col("pc") == "own_error") | pl.col("drf_err") | pl.col("lbdns").fill_null(False))
    f = f.with_columns(
        c1=pl.when(pl.col("c1_cul")).then(pl.lit("C"))
        .when(pl.col("sp_no") & pl.col("pc").is_in(["other", "own_neutral"]) & ~pl.col("drf_unk")).then(pl.lit("N"))
        .otherwise(pl.lit("U")))
    f = f.with_columns(
        c2=pl.when(pl.col("c1_cul") | pl.col("state")).then(pl.lit("C")).when(pl.col("c1") == "N").then(pl.lit("N"))
        .otherwise(pl.lit("U")),
        c2s=pl.when(pl.col("c1_cul") | pl.col("state")).then(pl.lit("C"))
        .when((pl.col("c1") == "N") & ~pl.col("state_unk")).then(pl.lit("N")).otherwise(pl.lit("U")),
        c3=pl.when(pl.col("c1_cul") | pl.col("vio")).then(pl.lit("C"))
        .when((pl.col("c1") == "N") & ~pl.col("vio_unk")).then(pl.lit("N")).otherwise(pl.lit("U")),
    )
    return f, k


def wp(e):
    return ((e.cast(pl.Float64) * pl.col("W")).sum() / pl.col("W").sum() * 100).round(2)


def main():
  for src in ["FARS", "CRSS"]:
      f, k = build(src)
      # two-vehicle crashes: exactly 2 in-transport vehicles, no non-motorist persons, both drivers present
      nveh = f.group_by(k).agg(pl.len().alias("nv"), (pl.col("DR_PRES") == 1).all().alias("both_drv"),
                               (pl.col("HIT_RUN") == 1).any().alias("any_hr"))
      two = nveh.filter((pl.col("nv") == 2))
      t = f.join(two, on=k, how="inner")
      print(f"\n######## {src}")
      print("crash-level ACC_VE_FORMS==2 vs vehicle-row count==2 agreement:",
            t.group_by(k).agg(pl.col("ACC_VE_FORMS").first()).select((pl.col("ACC_VE_FORMS") == 2).mean()).item())
      t0 = t
      t = t.filter(pl.col("both_drv") & (pl.col("PEDS") == 0))
      print("two-vehicle crashes:", t0.select(k).unique().height, "; with both drivers present & PEDS==0:",
            t.select(k).unique().height, "; of which with a hit-and-run vehicle:",
            t.filter(pl.col("any_hr")).select(k).unique().height)
      print("--- P_CRASH2 class among 2-veh drivers (weighted % for CRSS), by period")
      print(t.group_by(pl.col("YEAR") >= 2020).agg([wp(pl.col("pc") == c).alias(c) for c in
                                                    ["own_error", "own_neutral", "other", "nonmv", "unk"]]))
      # pair patterns of P_CRASH2 classes
      pp = t.group_by(k).agg(pl.col("pc").sort().str.join("+").alias("pair"), pl.col("W").first())
      print("--- P_CRASH2 pair patterns (top)")
      print(pp.group_by("pair").agg(pl.len().alias("n"), pl.col("W").sum().alias("w")).with_columns(
          (pl.col("w") / pl.col("w").sum() * 100).round(2).alias("wpct")).sort("w", descending=True).head(10))
      sev = "MAX_SEV" if src == "CRSS" else None
      for defn in ["c1", "c2", "c2s", "c3"]:
          cr = t.group_by(k).agg(
              nC=(pl.col(defn) == "C").sum(), nN=(pl.col(defn) == "N").sum(), nU=(pl.col(defn) == "U").sum(),
              W=pl.col("W").first(), sev=(pl.col("MAX_SEV").first() if src == "CRSS" else pl.lit(4)),
              nkill=(pl.col("DRV_INJ_SEV") == 4).sum())
          cr = cr.with_columns(pat=pl.when((pl.col("nC") == 1) & (pl.col("nN") == 1)).then(pl.lit("1C+1N"))
                               .when(pl.col("nC") == 2).then(pl.lit("2C"))
                               .when(pl.col("nN") == 2).then(pl.lit("2N"))
                               .when((pl.col("nC") == 1) & (pl.col("nU") == 1)).then(pl.lit("1C+1U"))
                               .otherwise(pl.lit("other_U")))
          print(f"--- {src} {defn}: crash pattern shares by year ({'weighted' if src=='CRSS' else 'unweighted'} %)")
          print(cr.group_by("YEAR").agg([pl.len().alias("n")] + [wp(pl.col("pat") == p).alias(p) for p in
                                                                 ["1C+1N", "2C", "2N", "1C+1U", "other_U"]]).sort("YEAR"))
          if src == "CRSS":
              print(f"--- {src} {defn}: by MAX_SEV (pooled)")
              print(cr.group_by("sev").agg([pl.len().alias("n")] + [wp(pl.col("pat") == p).alias(p) for p in
                                                                    ["1C+1N", "2C", "2N", "1C+1U", "other_U"]]).sort("sev"))
      # driver-level: culpable share by own outcome (outcome dependence)
      t = t.with_columns(dsev=pl.when(pl.col("DRV_INJ_SEV") == 4).then(pl.lit("K")).when(pl.col("DRV_INJ_SEV") == 3)
                         .then(pl.lit("A")).when(pl.col("DRV_INJ_SEV").is_in([1, 2])).then(pl.lit("B/C"))
                         .when(pl.col("DRV_INJ_SEV") == 0).then(pl.lit("O")).otherwise(pl.lit("unk")))
      print(f"--- {src}: driver-level components in 2-veh crashes by driver's own injury (pooled)")
      print(t.group_by("dsev").agg(pl.len().alias("n"), wp(pl.col("c1") == "C").alias("c1_C"), wp(pl.col("c1") == "U").alias("c1_U"),
                                   wp(pl.col("sp_yes")).alias("speed"), wp(pl.col("pc") == "own_error").alias("pc_own"),
                                   wp(pl.col("pc") == "unk").alias("pc_unk"), wp(pl.col("drf_err")).alias("drf_err"),
                                   wp(pl.col("vio")).alias("vio_charged"), wp(pl.col("state")).alias("state"),
                                   wp(pl.col("c3") == "C").alias("c3_C")).sort("dsev"))
      # agreement among components within clean crashes: P_CRASH2 vs violation charged
      print(f"--- {src}: component agreement (driver-level, 2-veh): P_CRASH2 own_error vs violation charged")
      print(t.group_by("pc", "vio").agg(pl.len().alias("n"), pl.col("W").sum().alias("w")).sort("pc", "vio"))
      if src == "FARS":
          # within 1 killed + 1 survived driver crashes: who is culpable under c1 vs c3
          cr = t.group_by(k).agg(nk=(pl.col("DRV_INJ_SEV") == 4).sum(), ns=(pl.col("DRV_INJ_SEV").is_in([0, 1, 2, 3])).sum())
          tt = t.join(cr.filter((pl.col("nk") == 1) & (pl.col("ns") == 1)), on=k)
          print("--- FARS 2-veh crashes with exactly 1 killed + 1 surviving driver: % culpable by role")
          print(tt.group_by("dsev").agg(pl.len().alias("n"), wp(pl.col("c1") == "C").alias("c1_C"),
                                        wp(pl.col("vio")).alias("vio_charged"), wp(pl.col("c3") == "C").alias("c3_C"),
                                        wp(pl.col("pc") == "own_error").alias("pc_own")).sort("dsev"))


if __name__ == "__main__":
    main()
