"""X1-02  Is CRSS ALCHL_IM (alcohol_im, the adjustment variable in model A/B) severity-dependent?

Claims at risk: F02 (night 3.97 -> 1.62; Shapley alcohol 20%), F03/F04 (exceedance 5.22, alcohol 4.2),
F05, P02, P03 (all adjust for alcohol_im).
Tests: (1) among crashes whose POLICE alcohol is unknown, weighted logit of alcohol_im=yes on
all model-A covariates (excluding alcohol) WITH vs WITHOUT the outcome 'fatal' -> adjusted OR
of fatal. Same among police-known crashes (the genuine ascertainment gradient).
(2) Model A refit with (a) alcohol_im, (b) police alcohol (3 level), (c) no alcohol term:
adjusted fatal RRs for night, exceedance-type speeding, unlit dark, motorcycle, alcohol.
"""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
import statsmodels.api as sm
df, design = severity.load("fatal")
print("n",len(df),"fatal",int(df.fatal.sum()))
# (1) severity-dependence of the imputation
base=[c for c in specs.PRE_CRASH if c not in ("alcohol_im","YEAR")]+["crash_type","n_vehicles"]
def logit_or(sub, with_out):
    X=pd.get_dummies(sub[base+["YEAR"]].astype(str),drop_first=True).astype(float)
    if with_out: X["fatal"]=sub["fatal"].to_numpy()
    X=sm.add_constant(X); y=(sub["alcohol_im"]=="yes").astype(float)
    m=sm.GLM(y,X,family=sm.families.Binomial(),freq_weights=sub["WEIGHT"]/sub["WEIGHT"].mean()).fit(cov_type="HC1")
    return m
for name,sub in [("police-UNKNOWN (imputed)",df[df.alcohol=="unknown"]),("police-KNOWN",df[df.alcohol!="unknown"])]:
    sub=sub[sub.alcohol_im.isin(["yes","no"])]
    m=logit_or(sub,True)
    b=m.params["fatal"]; ci=m.conf_int().loc["fatal"]
    # compare: pseudo-R2 gain from outcome
    print("%-26s n=%7d  imputed-yes share(w)=%.3f  adj OR(fatal)=%.2f (%.2f-%.2f)"%(name,len(sub),np.average(sub.alcohol_im=="yes",weights=sub.WEIGHT),np.exp(b),np.exp(ci[0]),np.exp(ci[1])))
# (2) refits
res={}
for label,alc in [("alcohol_im",["alcohol_im"]),("police alcohol",["alcohol"]),("no alcohol",[])]:
    cov=[c for c in specs.PRE_CRASH if c!="alcohol_im"]+alc
    m=severity.fit(df,design,"fatal",cov)
    out={}
    for f,lv in [("tod","00-05"),("speeding","yes"),("light","dark_not_lighted"),("any_motorcycle","yes"),("alcohol_im","yes"),("alcohol","yes"),("weather","rain")]:
        if f not in cov: continue
        levels=severity.observed_levels(df,f,specs.CRASH_LEVELS[f])
        t=severity.factor_contrasts(m,df,f,levels).set_index("level")
        out[f"{f}={lv}"]="%.2f (%.2f-%.2f)"%(t.loc[lv,"adj_rr"],t.loc[lv,"adj_rr_low"],t.loc[lv,"adj_rr_high"])
    res[label]=out
print(pd.DataFrame(res).to_string())
