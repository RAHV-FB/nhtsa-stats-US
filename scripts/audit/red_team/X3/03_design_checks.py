"""X3 test 2: design checks. (a) PSUs/strata present per year, weights; (b) CRSS-design fatal crashes/yr
vs FARS census (is the CRSS fatal numerator uncertainty real, and does it matter for the 54% 'denominator share'?);
(c) design effect and effective df: PSUs with >=1 fatal crash; (d) delete-one-year sensitivity of post-2020 RR is in 04.
Look at: PSU counts per year; CRSS vs FARS ratio of fatal crashes (2020-24 vs 2016-19)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data, severity
from nhtsa_stats.analysis.survey import svy_total
df, d = severity.load("fatal")
print("rows", len(df), "clusters", d.n_clusters, "strata", d.n_strata, "df", d.df)
g = df.groupby("YEAR").agg(n=("WEIGHT","size"), psus=("PSU_VAR","nunique"), strata=("PSUSTRAT","nunique"), wsum=("WEIGHT","sum"), fat=("fatal","sum"))
print(g)
yrs = {}
for y in sorted(df.YEAR.unique()):
    e = svy_total(d, df.fatal.to_numpy()*1.0, (df.YEAR==y).to_numpy())
    yrs[y] = (e.estimate, e.se)
fars = data.fars_crash()
fy = fars.groupby("YEAR").size() if "YEAR" in fars else None
print("FARS fatal crashes by year:", fy.to_dict())
out = pd.DataFrame({"crss_fatal_w": {y: v[0] for y, v in yrs.items()}, "crss_se": {y: v[1] for y, v in yrs.items()}, "fars": fy})
out["ratio"] = out.crss_fatal_w/out.fars; out["rel_se_crss"] = out.crss_se/out.crss_fatal_w
print(out.round(3))
p0, p1 = [2016,2017,2018,2019],[2020,2021,2022,2023,2024]
print("FARS fatal/yr ratio 2020-24 vs 2016-19:", fy[p1].mean()/fy[p0].mean())
print("CRSS fatal/yr ratio:", out.crss_fatal_w[p1].mean()/out.crss_fatal_w[p0].mean())
# PSUs with fatal crashes per stratum
pf = df[df.fatal==1].groupby("PSUSTRAT").PSU_VAR.nunique(); pa = df.groupby("PSUSTRAT").PSU_VAR.nunique()
print("strata:", len(pa), "min PSUs per stratum", pa.min(), "n strata with 2 PSUs", int((pa==2).sum()), "PSUs with a fatal crash", int(df[df.fatal==1].PSU_VAR.nunique()))
fat_psu = df[df.fatal==1].groupby(["PSUSTRAT","PSU_VAR"]).WEIGHT.sum().groupby("PSUSTRAT").size()
print("strata with fatal crashes in only one PSU:", int((fat_psu<2).sum()))
# Max PSU share of weighted fatal total
w = df[df.fatal==1].groupby("PSU_VAR").WEIGHT.sum(); print("largest PSU share of weighted fatal total:", round(w.max()/w.sum(),3), "top5", round(w.sort_values().tail(5).sum()/w.sum(),3))
