"""W05: (1) why 29% of CRSS struck pedestrians have unknown striker speed limit (vs 5.5% in FARS deaths):
by VSPD_LIM raw value, STR_VEH linkage, year. (2) 'mostly in the dark': weighted CRSS share of struck
pedestrians in dark and fatality rate by light; dark share of struck vs killed pedestrians (the gap is
lethality, not just exposure to walking in the dark). (3) weighted FARS-vs-CRSS speed-limit mix of killed."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats.analysis import vulnerable as V
df, design = V.load("pedestrian","killed")
print(df.groupby("YEAR").apply(lambda x: pd.Series({"n":len(x),"unk":(x.str_speed_limit=="unknown").mean()})).round(3))
raw=pl.concat([pl.read_parquet(f"data/interim/CRSS/vehicle/{y}.parquet").select("CASENUM","VEH_NO","VSPD_LIM").with_columns(pl.lit(y).alias("YEAR")) for y in range(2016,2025)]).to_pandas()
print(raw.VSPD_LIM.value_counts().head(12))
print("STR_VEH null share?")
p=pl.concat([pl.read_parquet(f"data/interim/CRSS/person/{y}.parquet").select("CASENUM","PER_TYP","STR_VEH","LOCATION").with_columns(pl.lit(y).alias("YEAR")) for y in range(2016,2025)]).filter(pl.col("PER_TYP")==5).to_pandas()
print(p.STR_VEH.describe(), (p.STR_VEH.fillna(-1)<=0).mean())
u=df[df.str_speed_limit=="unknown"]
print("unknown group: weighted killed rate",np.average(u.killed,weights=u.WEIGHT),"light mix");
print(u.groupby("urbanicity").size()/len(u))
print(df.groupby("urbanicity").apply(lambda x: pd.Series({"unk_share":(x.str_speed_limit=="unknown").mean(),"w_rate":np.average(x.killed,weights=x.WEIGHT)})))
d=df.copy(); d["dark"]=d.light.astype(str).str.contains("dark",case=False)
print(d.light.value_counts())
w=d.groupby("light").apply(lambda x: pd.Series({"n":len(x),"w_share_struck":x.WEIGHT.sum(),"killed":x.killed.sum(),"w_rate":np.average(x.killed,weights=x.WEIGHT)}))
w["w_share_struck"]/=w.w_share_struck.sum(); print(w.round(4))
print("weighted dark share of ALL struck peds",np.average(d.dark,weights=d.WEIGHT),"; of killed (unweighted rows)",d[d.killed==1].dark.mean())
print("hour/tod: weighted share struck by tod");print(d.groupby("tod").apply(lambda x: pd.Series({"w_share":x.WEIGHT.sum(),"rate":np.average(x.killed,weights=x.WEIGHT)})).assign(w_share=lambda x:x.w_share/x.w_share.sum()).round(4))
# CRSS weighted killed vs FARS speed mix
k=d[d.killed==1]; print("CRSS killed speed mix (unweighted rows)");print(k.str_speed_limit.value_counts(normalize=True).round(3))
