"""F11 attacks 6-7: refit the selected HGB (lr .1, 31 leaves, min leaf 100) single-threaded,
(a) full circumstance set and (b) without speeding+alcohol_im; weighted/unweighted AUROC on 2023-24,
by-year AUROC, lowest-half O/P, and the HGB-minus-logit gap with a simple PSU-cluster bootstrap (100 reps)
of the AUROC difference vs the post-crash-judgement-free logit. Compare with published 0.9206 / 0.0176 gap."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from nhtsa_stats.models import severity_ml as m
exec(open("scripts/audit/red_team/F11/01_logit_ablations.py").read().split("df = m.load_crashes()")[0].split("from nhtsa_stats.models import severity_ml as m")[1])
df = m.load_crashes(); df = df[df.fatal.notna()]
tr = df[df.YEAR.isin(range(2016,2022))]; te = df[df.YEAR.isin([2023,2024])]
y=te.fatal.values; w=te.WEIGHT.values; yr=te.YEAR.values
cats_full=list(m.STAGES["pre_crash+circumstance"])
res={}
for label,drop in [("full",[]),("no speeding/alcohol_im",["speeding","alcohol_im"])]:
    cats=[c for c in cats_full if c not in drop]
    pre=m.Preprocessor(cats).fit(tr)
    h=m.fit_hgb(pre,tr,"fatal",{"learning_rate":0.1,"max_leaf_nodes":31,"min_samples_leaf":100},"pre_crash+circumstance")
    ph=h.predict(te)
    est=LogisticRegression(C=m.RIDGE_C,**m.LOGIT_SOLVER).fit(pre.onehot(tr),tr.fatal.values,sample_weight=m._weights(tr))
    pl=est.predict_proba(pre.onehot(te))[:,1]
    res[label]=(ph,pl)
    cut=m.weighted_quantile(ph,w,0.5); lo=ph<=cut
    print(label,"n_iter",h.params["n_iter"],"HGB auc_w",round(wauc(ph,y,w),4),"unw",round(wauc(ph,y,np.ones_like(w)),4),
          "2023",round(wauc(ph[yr==2023],y[yr==2023],w[yr==2023]),4),"2024",round(wauc(ph[yr==2024],y[yr==2024],w[yr==2024]),4),
          "| logit auc_w",round(wauc(pl,y,w),4),"| O/P all",round((w*y).sum()/(w*ph).sum(),3),"lowest half",round((w*y)[lo].sum()/(w*ph)[lo].sum(),3),
          "events in lowest half (unweighted n)",int(y[lo].sum()))
# cluster bootstrap of gap (full): resample PSU_VAR within PSUSTRAT with replacement
ph,pl=res["full"]
key=(te.PSUSTRAT.astype(str)+"_"+te.PSU_VAR.astype(str)).values
codes,uniq=pd.factorize(key); strat=pd.Series(te.PSUSTRAT.values).groupby(codes).first().values
rng=np.random.default_rng(1); gaps=[]; los=[]
ncl=len(uniq); order=[np.where(codes==k)[0] for k in range(ncl)]
byst={}
for k in range(ncl): byst.setdefault(strat[k],[]).append(k)
for b in range(100):
    mult=np.zeros(ncl)
    for s,ks in byst.items():
        pick=rng.choice(ks,size=len(ks),replace=True)
        for k in pick: mult[k]+=1
    ww=w*mult[codes]
    gaps.append(wauc(ph,y,ww)-wauc(pl,y,ww))
    cut=m.weighted_quantile(ph,ww,0.5); lo=ph<=cut
    los.append((ww*y)[lo].sum()/(ww*ph)[lo].sum())
print("gap HGB-logit point",round(wauc(ph,y,w)-wauc(pl,y,w),4),"boot 2.5/97.5",np.percentile(gaps,[2.5,97.5]).round(4))
print("lowest-half O/P boot 2.5/97.5",np.percentile(los,[2.5,97.5]).round(3))
