"""F04 pedestrian attacks (CRSS, killed | struck).
(0) reproduce striking-vehicle and speed-limit RRs.
(1) drop str_speeding + alcohol_im (possible mediators of vehicle type / speed) -> do vehicle RRs change?
(2) restrict to known striking vehicle + known speed limit (complete case).
(3) CC outcome (INJ_SEV not imputed): killed_cc.
(4) add urbanicity-free alternative: drop 'location' and 'light' (mediators?) to see total-association sensitivity.
Look at: SUV / pickup / large / 50-55 RRs under each spec."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity
from nhtsa_stats.analysis import vulnerable as V
def run(df, design, covs, outcome, tag):
    from nhtsa_stats.analysis.survey import SurveyLogit
    m = SurveyLogit(V._spec(df, covs), ridge=severity.RIDGE).fit(df, df[outcome].to_numpy(), design)
    res=[]
    if "striking" in covs:
        t = severity.factor_contrasts(m, df, "striking", severity.observed_levels(df,"striking",V.LEVELS["striking"])).set_index("level")
        for l in ("suv","pickup","large"): res.append("%s %.2f (%.2f-%.2f)"%(l,t.loc[l,"adj_rr"],t.loc[l,"adj_rr_low"],t.loc[l,"adj_rr_high"]))
    if "str_speed_limit" in covs:
        t = severity.factor_contrasts(m, df, "str_speed_limit", severity.observed_levels(df,"str_speed_limit",V.LEVELS["str_speed_limit"])).set_index("level")
        for l in ("30-35","50-55"): res.append("%s %.2f (%.2f-%.2f)"%(l,t.loc[l,"adj_rr"],t.loc[l,"adj_rr_low"],t.loc[l,"adj_rr_high"]))
    print(f"[{tag}] n={len(df)} ev={int(df[outcome].sum())} |", " | ".join(res), flush=True)
df, design = V.load("pedestrian","killed")
print(df.striking.value_counts().to_dict())
run(df,design,V.COVARIATES,"killed","(0) published")
run(df,design,[c for c in V.COVARIATES if c not in("str_speeding","alcohol_im")],"killed","(1) no speeding/alcohol")
run(df,design,[c for c in V.COVARIATES if c not in("location","light","tod")],"killed","(4) no location/light/tod")
k=((df.striking!="other_unknown")&(df.str_speed_limit!="unknown")).to_numpy()
run(df.loc[k].reset_index(drop=True),design.subset(k),V.COVARIATES,"killed","(2) known vehicle+limit")
k=(df.striking.isin(["car","suv","pickup"])).to_numpy()
run(df.loc[k].reset_index(drop=True),design.subset(k),V.COVARIATES,"killed","(2b) car/suv/pickup only")
d2,des2 = V.load("pedestrian","killed_cc")
run(d2,des2,V.COVARIATES,"killed_cc","(3) killed_cc (observed INJ_SEV)")
# 2016-19 vs 2020-24 vehicle effect
for nm,ys in (("2016-19",[2016,2017,2018,2019]),("2020-24",[2020,2021,2022,2023,2024])):
    k=df.YEAR.isin(ys).to_numpy()
    run(df.loc[k].reset_index(drop=True),design.subset(k),[c for c in V.COVARIATES if c!="YEAR"],"killed","(5) "+nm)
print(V.fars_striking_mix().to_string() if False else "")
