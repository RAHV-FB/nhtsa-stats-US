"""Verify STRATUM (crash-type sampling stratum) meanings by cross-tab with crash composition; 2016-18 vs 2019-24."""
import polars as pl, pandas as pd
from nhtsa_stats.ingestion.cache import load_table
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",400)
def P(d): print(d.to_pandas().to_string(index=False))
a = load_table("CRSS","accident",years=None,columns=["CASENUM","STRATUM","MAX_SEV","MAXSEV_IM"])
v = load_table("CRSS","vehicle",years=None,columns=["CASENUM","VEH_NO","BODY_TYP","MOD_YEAR","MAX_VSEV"])
p = load_table("CRSS","person",years=None,columns=["CASENUM","VEH_NO","PER_NO","PER_TYP","INJ_SEV","INJSEV_IM"])
v = v.with_columns(
    pl.col("BODY_TYP").is_between(80,89).alias("mc"),
    pl.col("BODY_TYP").is_between(50,78).alias("mh"),     # buses 50-59, medium/heavy trucks 60-78 (79 = unknown light/medium/heavy)
    pl.col("BODY_TYP").is_between(1,49).alias("pv"),
    pl.when(pl.col("MOD_YEAR")<9000).then(pl.col("YEAR")-pl.col("MOD_YEAR")).alias("age"))
vc = v.group_by(["YEAR","CASENUM"]).agg(pl.col("mc").any(), pl.col("mh").any(), pl.col("pv").any(),
      pl.col("age").filter(pl.col("pv")).min().alias("min_pv_age"),
      (pl.col("mc") & pl.col("MAX_VSEV").is_in([1,2,3,4,5])).any().alias("mc_veh_inj"))
pc = p.group_by(["YEAR","CASENUM"]).agg((pl.col("PER_TYP").is_in([4,5,6,7,8,10]) & pl.col("INJ_SEV").is_in([1,2,3,4,5])).any().alias("nonocc_inj"),
      pl.col("PER_TYP").is_in([3,4,5,6,7,8,10]).any().alias("any_nonocc"))
d = a.join(vc, on=["YEAR","CASENUM"], how="left").join(pc, on=["YEAR","CASENUM"], how="left").with_columns(
    pl.col("MAX_SEV").is_in([1,2,3,4,5]).alias("inj"), pl.col("MAX_SEV").is_in([3,4]).alias("KA"), pl.col("MAX_SEV").is_in([1,2]).alias("BC"),
    pl.col("YEAR").is_in([2016,2017,2018]).alias("early"))
for early in [True, False]:
    t = d.filter(pl.col("early")==early).group_by("STRATUM").agg(pl.len().alias("n"),
        *[(pl.col(c).cast(pl.Float64).mean()*100).round(1).alias(c) for c in ["nonocc_inj","any_nonocc","mc","mc_veh_inj","mh","pv","inj","KA","BC"]],
        (pl.col("min_pv_age")<=3).cast(pl.Float64).mean().mul(100).round(1).alias("pv_age<=3"),
        (pl.col("min_pv_age")<=4).cast(pl.Float64).mean().mul(100).round(1).alias("pv_age<=4"),
        (pl.col("min_pv_age")<=5).cast(pl.Float64).mean().mul(100).round(1).alias("pv_age<=5"),
        pl.col("min_pv_age").median().alias("med_min_pv_age")).sort("STRATUM")
    print("2016-18" if early else "2019-24"); P(t)
# LMY threshold: distribution of youngest PV age in strata 4 vs 5, 6 vs 8, 9 vs 10
for s in [4,5,6,8,9]:
    x = d.filter(pl.col("STRATUM")==s).group_by("min_pv_age").len().sort("min_pv_age").head(12)
    print("STRATUM",s,"youngest PV age distr:", dict(zip(x["min_pv_age"].to_list(), x["len"].to_list())))
# LMY by year: max youngest-PV age in stratum 4 per year (95th pct)
P(d.filter(pl.col("STRATUM").is_in([4,6,9])).group_by(["YEAR","STRATUM"]).agg(pl.col("min_pv_age").quantile(0.95).alias("p95_age"), (pl.col("min_pv_age")<=4).mean().round(3).alias("share_le4"), (pl.col("min_pv_age")<=5).mean().round(3).alias("share_le5")).sort(["STRATUM","YEAR"]))
P(d.filter(pl.col("STRATUM").is_in([5,8,10])).group_by(["YEAR","STRATUM"]).agg((pl.col("min_pv_age")<=4).mean().round(3).alias("share_le4"), (pl.col("min_pv_age")<=5).mean().round(3).alias("share_le5"), (pl.col("min_pv_age")<=3).mean().round(3).alias("share_le3")).sort(["STRATUM","YEAR"]))
# MAX_SEV=8 vs no person rows
nop = a.join(p.select(["YEAR","CASENUM"]).unique(), on=["YEAR","CASENUM"], how="anti")
print("cases with no person rows:", nop.height, " of which MAX_SEV=8:", (nop["MAX_SEV"]==8).sum(), "; MAX_SEV=8 total:", (a["MAX_SEV"]==8).sum())
# MAXSEV_IM vs max person INJSEV_IM; MAX_SEV vs max INJ_SEV (rank: 0<1<2<3<4, 5 injured-unk, 6 died prior, 9 unknown)
pm = p.group_by(["YEAR","CASENUM"]).agg(pl.col("INJSEV_IM").filter(pl.col("INJSEV_IM").is_in([0,1,2,3,4])).max().alias("mx_im"),
      pl.col("INJSEV_IM").is_in([5]).any().alias("any5_im"), pl.col("INJ_SEV").filter(pl.col("INJ_SEV").is_in([0,1,2,3,4])).max().alias("mx"),
      (pl.col("INJ_SEV")==9).any().alias("any9"), (pl.col("INJ_SEV")==5).any().alias("any5"))
j = a.join(pm, on=["YEAR","CASENUM"], how="inner")
x = j.group_by(["MAXSEV_IM","mx_im","any5_im"]).len().sort(["MAXSEV_IM","mx_im","any5_im"])
print("MAXSEV_IM vs max(INJSEV_IM in 0-4), any INJSEV_IM=5"); P(x)
x = j.group_by(["MAX_SEV","mx","any5","any9"]).len().sort(["MAX_SEV","mx","any5","any9"])
print("MAX_SEV vs max(INJ_SEV in 0-4), any 5, any 9"); P(x.filter(pl.col("len")>20))
