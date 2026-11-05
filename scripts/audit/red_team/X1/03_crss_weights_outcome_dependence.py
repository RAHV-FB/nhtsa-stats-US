"""X1-03  CRSS WEIGHT is benchmarked to FARS fatal counts (MAXSEV_IM=4) -> outcome-dependent weights.

Claims at risk: F01, F08 (fatal share, 0.51% -> 0.64%), F10, F11 (weighted prevalence/AP/calibration),
all weighted fatal rates. Tests: (1) mean weight of sampled fatal vs A-injury vs other crashes within
year x region; the fatal/KA-nonfatal ratio shows the size of the benchmark factor; (2) weighted fatal
count vs FARS fatal crashes per year (circularity of any CRSS-vs-FARS fatal-count comparison);
(3) fatal-share sensitivity: re-weight fatal crashes with the weight of non-fatal 'A' crashes
in the same year x region (a proxy for 'un-benchmarked' weights) and report resulting fatal share
by year and the 2019->2022 ratio; (4) fatal-vs-all weighted AUROC is unaffected? report unweighted vs weighted
prevalence only.
"""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data, severity
df, design = severity.load("fatal")
df["cls"]=np.where(df.fatal==1,"fatal",np.where(df.ka==1,"A_nonfatal","other"))
g=df.groupby(["YEAR","region","cls"]).WEIGHT.mean().unstack()
g["fatal/A"]=g["fatal"]/g["A_nonfatal"]; g["fatal/other"]=g["fatal"]/g["other"]
print("ratio of mean sampled weight, fatal vs non-fatal-A, by year x region (summary):")
print(g[["fatal/A","fatal/other"]].describe().round(2).to_string())
print(g.groupby("YEAR")[["fatal/A","fatal/other"]].median().round(2).to_string())
w=df.groupby("YEAR").apply(lambda s: pd.Series({"w_fatal":s.loc[s.fatal==1,"WEIGHT"].sum(),"n_fatal_sampled":int((s.fatal==1).sum()),"w_total":s.WEIGHT.sum()}))
fc=data.fars_crash().groupby("YEAR").size() if hasattr(data,"fars_crash") else None
fc=pd.Series(fc.to_numpy() if hasattr(fc,'to_numpy') else fc, index=w.index) if fc is not None else None
w["FARS_fatal_crashes"]=fc.values if fc is not None else np.nan
w["ratio"]=w.w_fatal/w.FARS_fatal_crashes
w["fatal_share_%"]=100*w.w_fatal/w.w_total
print(w.round(3).to_string())
# proxy of un-benchmarked weights: fatal crashes get the mean weight of non-fatal A crashes in same year x region
m=df.groupby(["YEAR","region"]).apply(lambda s: s.loc[s.cls=="A_nonfatal","WEIGHT"].mean()).rename("wA")
d2=df.join(m,on=["YEAR","region"])
d2["w2"]=np.where(d2.fatal==1,d2.wA,d2.WEIGHT)
alt=d2.groupby("YEAR").apply(lambda s: 100*s.loc[s.fatal==1,"w2"].sum()/s.w2.sum())
print("fatal share % : published-weights vs fatal-given-A-weight proxy")
print(pd.DataFrame({"published":w["fatal_share_%"],"proxy":alt}).round(3).to_string())
pre=w.loc[[2016,2017,2018,2019],"w_fatal"].sum()/w.loc[[2016,2017,2018,2019],"w_total"].sum(); post=w.loc[[2022,2023,2024],"w_fatal"].sum()/w.loc[[2022,2023,2024],"w_total"].sum()
print("published ratio post(2022-24)/pre(2016-19) fatal share: %.3f"%(post/pre))
sub=d2[d2.YEAR.isin([2016,2017,2018,2019])]; sub2=d2[d2.YEAR.isin([2022,2023,2024])]
pr=sub.loc[sub.fatal==1,"w2"].sum()/sub.w2.sum(); po=sub2.loc[sub2.fatal==1,"w2"].sum()/sub2.w2.sum()
print("proxy ratio post/pre: %.3f"%(po/pr))
