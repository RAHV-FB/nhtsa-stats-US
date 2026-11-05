"""X1-01  Does the FARS multiply-imputed BAC depend on the driver's own injury outcome?

Claim tested: FARS MI BAC (drv_p_p08 = share of 10 implicates with BAC>=.08) is a 'pre-crash'
exposure for W01-W03, P01, P03, P04. If NHTSA's imputation model conditions on driver injury
(killed vs survived), imputed BAC among UNTESTED drivers carries outcome information.
Method: (1) among untested drivers, mean p_p08 by drv_killed, crude and adjusted (fractional
logit on crash covariates); (2) same gradient among tested drivers (measured BAC>=.08);
(3) counterfactual: set untested killed drivers' p_p08 to the adjusted rate they would have if
imputed with the survivors' (covariate-conditional) model and recompute the share of drivers/deaths.
Look at: adj OR killed in untested vs tested; change in W01 29.9%-type statistic.
"""
import numpy as np, polars as pl, statsmodels.api as sm, statsmodels.formula.api as smf
d = pl.read_parquet("data/processed/fars_driver.parquet", columns=[
 "YEAR","drv_killed","drv_p_p08","drv_bac08_measured","drv_age_band","drv_sex","night","weekend",
 "crash_type","n_vehicles","speeding","rural","DEATHS","drv_pr_alcohol","drv_alc_test_status","light"]).to_pandas()
d=d[d.drv_killed.isin([0,1])]
for c in ["drv_age_band","drv_sex","crash_type","n_vehicles","speeding","rural","night","weekend","light","drv_pr_alcohol"]:
    d[c]=d[c].astype(str)
f="~ drv_killed + C(YEAR)+C(drv_age_band)+C(drv_sex)+C(night)+C(weekend)+C(crash_type)+C(n_vehicles)+C(speeding)+C(rural)+C(light)+C(drv_pr_alcohol)"
un=d[d.drv_bac08_measured.isna() & d.drv_p_p08.notna()].copy()
te=d[d.drv_bac08_measured.notna()].copy()
print("n untested",len(un),"tested",len(te))
print("untested mean p_p08 by killed:\n",un.groupby("drv_killed").drv_p_p08.agg(["mean","size"]))
print("tested measured>=.08 by killed:\n",te.groupby("drv_killed").drv_bac08_measured.agg(["mean","size"]))
def fit(df,y):
    m=smf.glm(y+f,data=df,family=sm.families.Binomial()).fit(cov_type="HC1")
    b=m.params["drv_killed"]; ci=m.conf_int().loc["drv_killed"]
    return m,np.exp(b),np.exp(ci[0]),np.exp(ci[1])
mu,o,l,h=fit(un,"drv_p_p08"); print("UNTESTED adj OR(killed) for imputed p_p08: %.2f (%.2f-%.2f)"%(o,l,h))
mt,o2,l2,h2=fit(te,"drv_bac08_measured"); print("TESTED adj OR(killed) for measured BAC>=.08: %.2f (%.2f-%.2f)"%(o2,l2,h2))
# restricted to police-alcohol-unknown ('nan' string) untested to remove police-report path
un2=un[un.drv_pr_alcohol.isin(["nan","None"])]
print("n untested & police alcohol missing",len(un2))
# counterfactual: untested killed drivers get survivors' conditional rate (model fitted on untested survivors)
ms=smf.glm("drv_p_p08"+f.replace("drv_killed +",""),data=un[un.drv_killed==0],family=sm.families.Binomial()).fit()
k=un.drv_killed==1
cf=un.copy(); cf.loc[k,"drv_p_p08"]=ms.predict(un[k])
print("untested killed: actual mean p08 %.4f vs survivor-model counterfactual %.4f"%(un.loc[k,"drv_p_p08"].mean(),cf.loc[k,"drv_p_p08"].mean()))
# effect on share of ALL drivers/ killed drivers at BAC>=.08 (measured where tested else p_p08)
d=d.copy(); d["p"]=np.where(d.drv_bac08_measured.notna(),d.drv_bac08_measured,d.drv_p_p08)
d["pcf"]=d["p"]; idx=un.index[k.values]; print("n replaced",len(idx)); d.loc[idx,"pcf"]=cf.loc[idx,"drv_p_p08"].to_numpy()
kk=d[d.drv_killed==1]
print("killed drivers: share BAC>=.08  published-style %.4f ; counterfactual %.4f ; n=%d ; untested share %.3f"%(kk.p.mean(),kk.pcf.mean(),len(kk),kk.drv_bac08_measured.isna().mean()))
print("all drivers: %.4f vs %.4f"%(d.p.mean(),d.pcf.mean()))
