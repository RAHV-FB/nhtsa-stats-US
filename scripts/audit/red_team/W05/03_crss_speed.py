"""W05 CRSS attack on 'share of struck pedestrians who died 2.2% -> 33.1% (RR 6.6)'.
Refit the project's survey logit under alternative specifications and outcomes and print RR(50-55 vs <=25):
 baseline; complete-case outcome (INJ_SEV, no imputation); drop mediators (location, light, tod);
 add nothing but urbanicity; urban only; exclude unknown/none speed-limit; collapse 50-55+ etc.
Also unweighted cell counts behind the crude rates, and by-period stability (2016-19 vs 2020-24)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, vulnerable as V
from nhtsa_stats.analysis.survey import SurveyLogit, ModelSpec
def fit(df, design, outcome, covs, label, ref="<=25"):
    spec = V._spec(df, covs)
    m = SurveyLogit(spec, ridge=severity.RIDGE).fit(df, df[outcome].to_numpy(), design)
    lv = severity.observed_levels(df, "str_speed_limit", V.LEVELS["str_speed_limit"])
    t = severity.factor_contrasts(m, df, "str_speed_limit", lv)
    r = t[t.level.isin(["30-35","40-45","50-55","60-65","70+"])][["level","adj_rate","adj_rr","adj_rr_low","adj_rr_high"]]
    print(f"--- {label}"); print(r.round(3).to_string(index=False))
df, design = V.load("pedestrian","killed")
print("n",len(df),"events",int(df.killed.sum()))
print(df.groupby("str_speed_limit").agg(n=("killed","size"),ev=("killed","sum"),w=("WEIGHT","sum")).assign(wrate=lambda x:0))
g=df.assign(wk=df.WEIGHT*df.killed).groupby("str_speed_limit").agg(w=("WEIGHT","sum"),wk=("wk","sum"));g["rate"]=g.wk/g.w;print(g.round(4))
fit(df,design,"killed",V.COVARIATES,"baseline (published spec)")
fit(df,design,"killed",["str_speed_limit"],"crude")
fit(df,design,"killed",[c for c in V.COVARIATES if c not in("location","light","tod")],"drop location/light/tod")
fit(df,design,"killed",[c for c in V.COVARIATES if c not in("urbanicity","region")],"drop urbanicity/region")
fit(df,design,"killed",[c for c in V.COVARIATES if c not in("striking","str_speeding")],"drop striker/str_speeding")
fit(df,design,"killed",[c for c in V.COVARIATES if c not in("alcohol_im","age_band","sex")],"drop alcohol/age/sex")
# restrict
sub=df.urbanicity=="urban"
d2=df[sub].reset_index(drop=True); 
import numpy as np
# complete-case outcome
dcc,dsg=V.load("pedestrian","killed_cc")
print("cc n",len(dcc),"events",int(dcc.killed_cc.sum()))
fit(dcc,dsg,"killed_cc",V.COVARIATES,"complete-case outcome (INJ_SEV, drops unknown severity)")
# KA outcome
dka,dks=V.load("pedestrian","killed_or_serious")
fit(dka,dks,"killed_or_serious",V.COVARIATES,"KA outcome")
# period split via unweighted subset designs (design.subset)
for lab,mask in (("2016-2019",df.YEAR<=2019),("2020-2024",df.YEAR>=2020)):
    full=np.zeros(len(df),bool)
    try:
        ds=design.subset(mask.to_numpy())
        dd=df[mask].reset_index(drop=True)
        fit(dd,ds,"killed",[c for c in V.COVARIATES if c!="YEAR"],"period "+lab)
    except Exception as e: print(lab,"fail",e)
# without 'unknown/none' speed-limit rows
mask=~df.str_speed_limit.isin(["unknown","none_nontrafficway"])
ds=design.subset(mask.to_numpy()); dd=df[mask].reset_index(drop=True)
fit(dd,ds,"killed",V.COVARIATES,"excluding unknown/none speed-limit rows")
