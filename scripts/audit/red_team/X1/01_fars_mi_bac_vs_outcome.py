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
# counterfactual (rows with a defined survivor-model prediction only): untested killed drivers get the
# survivors' covariate-conditional imputed rate
ms=smf.glm("drv_p_p08"+f.replace("drv_killed +",""),data=un[un.drv_killed==0],family=sm.families.Binomial()).fit()
uk=un[un.drv_killed==1].copy(); uk["cf"]=np.asarray(ms.predict(uk)); ok=uk.cf.notna()
print("untested killed with defined prediction: %d of %d; actual mean p08 %.4f vs survivor-model counterfactual %.4f"%(ok.sum(),len(uk),uk.loc[ok,"drv_p_p08"].mean(),uk.loc[ok,"cf"].mean()))
# bound on W01-style statistic: share of killed drivers at BAC>=.08 (tested measured, untested imputed)
kt=d[d.drv_killed==1]; n=len(kt); meas=kt.drv_bac08_measured.sum(); imp=kt.loc[kt.drv_bac08_measured.isna(),"drv_p_p08"].sum()
shift=(uk.loc[ok,"drv_p_p08"]-uk.loc[ok,"cf"]).sum()
print("killed drivers: share BAC>=.08 = %.4f; if imputed rate had followed survivors' model (defined rows) = %.4f; untested share %.3f"%((meas+imp)/n,(meas+imp-shift)/n,kt.drv_bac08_measured.isna().mean()))
