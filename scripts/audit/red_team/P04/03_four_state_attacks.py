"""P04 claim: in the 4 high-testing states BAC>=.08 OR 2.17 (1.82-2.58) vs any drug 1.28
(1.13-1.44) for being the driver who died; 'alcohol is the stronger correlate'.
Attacks (own statsmodels logit, crash-clustered SE, project covariates):
 A reproduce; B per-state and leave-one-state-out; C formal test alcohol-vs-drug log-OR
 difference; D drug definition variants (excl. cannabinoid; excl. carboxy-THC-only/presumptive
 only); E state fixed effects; F states chosen by a looser rule (>=40% / >=30% tested both
 groups) to see stability; G alcohol x drug joint categories (the main-effects ranking hides
 the interaction).  Read the OR columns."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, statsmodels.api as sm
from nhtsa_stats.analysis import drugs as D
df=D.load_fars_drivers(); st=D.state_testing(df); d=D._driver_frame(df)
d=d[(d.survival!="unknown")&d.alcohol.notna()&d.drug.notna()].reset_index(drop=True)
d["y"]=(d.survival=="killed").astype(float); d["cl"]=d.YEAR*1_000_000+d.case_id.astype(int)
high=list(st.loc[st.high_testing,"STATE"]); print("high states",high)
covs=list(D.DRIVER_COVS)
def X(sub,extra=None,fe=False):
    cols=[(sub.alcohol=="yes").astype(float).rename("alc"),(sub.drug=="yes").astype(float).rename("drg")] if extra is None else extra
    Z=pd.concat(cols,axis=1)
    cc=pd.get_dummies(sub[covs],drop_first=True).astype(float)
    Z=pd.concat([Z,cc]+([pd.get_dummies(sub.STATE,prefix="st",drop_first=True).astype(float)] if fe else []),axis=1)
    Z=Z.loc[:,(Z.std()>0)&((Z.sum()>=10)|Z.columns.isin(["alc","drg"]))]
    return sm.add_constant(Z)
def fit(sub,**kw):
    Z=X(sub,**kw)
    try: return sm.Logit(sub.y,Z).fit(disp=0,maxiter=200,method="bfgs" if False else "newton",cov_type="cluster",cov_kwds={"groups":sub.cl})
    except Exception as e: print("fit fail",e); return None
def line(tag,r,a="alc",b="drg"):
    if r is None: print(tag,"FAILED"); return
    ci=np.exp(r.conf_int().loc[[a,b]].values)
    V=r.cov_params().loc[[a,b],[a,b]].values; dlt=r.params[a]-r.params[b]; se=np.sqrt(V[0,0]+V[1,1]-2*V[0,1])
    print(f"{tag:46s} n={int(r.nobs):6d} OR_alc {np.exp(r.params[a]):.2f} ({ci[0,0]:.2f}-{ci[0,1]:.2f})  OR_drg {np.exp(r.params[b]):.2f} ({ci[1,0]:.2f}-{ci[1,1]:.2f})  diff z={dlt/se:.2f} p={2*(1-__import__('scipy.stats').stats.norm.cdf(abs(dlt/se))):.4f}")
S=d[d.STATE.isin(high)].reset_index(drop=True)
line("A high-testing 4 states (reproduce)",fit(S))
line("A' all states",fit(d.reset_index(drop=True)))
for s in high:
    line(f"B only state {s} (n_killed {int(S[S.STATE==s].y.sum())})",fit(S[S.STATE==s].reset_index(drop=True)))
    line(f"B leave out state {s}",fit(S[S.STATE!=s].reset_index(drop=True)))
line("E state FE, 4 states",fit(S,fe=True))
line("E state FE, all states",fit(d.reset_index(drop=True),fe=True))
# D drug variants
dr=D.DRUG_CLASSES
raw=df[["YEAR","case_id","VEH_NO","drv_drug_cannabinoid","drv_drug_presumptive_only","drv_drug_carboxy_thc_only"]+[f"drv_drug_{c}" for c in dr]]
keys=["YEAR","case_id","VEH_NO"]
dd=D._driver_frame(df).merge(raw.drop_duplicates(keys),on=keys,how="left",suffixes=("","_r"))
dd=dd[(dd.survival!="unknown")&dd.alcohol.notna()&dd.drug.notna()].reset_index(drop=True); dd["y"]=(dd.survival=="killed").astype(float); dd["cl"]=dd.YEAR*1_000_000+dd.case_id.astype(int)
for name,sel in (("4 states",dd.STATE.isin(high)),("all states",dd.STATE>0)):
    sub=dd[sel].reset_index(drop=True)
    noncann=(sub[[f"drv_drug_{c}" for c in dr if c!="cannabinoid"]].fillna(0).max(axis=1)==1).astype(float)
    r=fit(sub,extra=[(sub.alcohol=="yes").astype(float).rename("alc"),noncann.rename("drg")]); line(f"D drug = non-cannabinoid, {name}",r)
    cann=(sub.drv_drug_cannabinoid.fillna(0)==1).astype(float)
    r=fit(sub,extra=[(sub.alcohol=="yes").astype(float).rename("alc"),noncann.rename("drg"),cann.rename("thc")]); 
    print("   separate: non-cann OR %.2f, cannabinoid OR %.2f"%(np.exp(r.params['drg']),np.exp(r.params['thc'])))
    strict=((sub.drug=="yes")&(sub.drv_drug_presumptive_only.fillna(0)!=1)&(sub.drv_drug_carboxy_thc_only.fillna(0)!=1)).astype(float)
    r=fit(sub,extra=[(sub.alcohol=="yes").astype(float).rename("alc"),strict.rename("drg")]); line(f"D drug excl presumptive/carboxy-only, {name}",r)
# F looser state rules
for thr in (0.4,0.3):
    hs=st[(st.drug_tested_killed>=thr)&(st.drug_tested_survived>=thr)&(st.bac_tested_killed>=thr)&(st.bac_tested_survived>=thr)].STATE.tolist()
    sub=d[d.STATE.isin(hs)].reset_index(drop=True); line(f"F states with all four rates >= {thr} ({len(hs)} states)",fit(sub))
# G joint categories
sub=S; a=(sub.alcohol=="yes");g=(sub.drug=="yes")
J=pd.concat([(a&~g).astype(float).rename("alc_only"),(~a&g).astype(float).rename("drug_only"),(a&g).astype(float).rename("both")],axis=1)
r=fit(sub,extra=[J[c] for c in J]); print("G 4 states joint (ref neither):",{k:round(float(np.exp(r.params[k])),2) for k in J})
sub=d.reset_index(drop=True); a=(sub.alcohol=="yes");g=(sub.drug=="yes")
J=pd.concat([(a&~g).astype(float).rename("alc_only"),(~a&g).astype(float).rename("drug_only"),(a&g).astype(float).rename("both")],axis=1)
r=fit(sub,extra=[J[c] for c in J]); print("G all states joint (ref neither):",{k:round(float(np.exp(r.params[k])),2) for k in J})
# prevalences by state
print(S.groupby("STATE").agg(n=("y","size"),killed=("y","sum"),alc=("alcohol",lambda s:(s=="yes").mean()),drug=("drug",lambda s:(s=="yes").mean())).round(3))
