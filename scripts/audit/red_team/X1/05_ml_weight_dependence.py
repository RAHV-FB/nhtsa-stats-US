"""X1-05  Prediction headline (F11) under outcome-dependent (FARS-benchmarked) weights.

Headline AUROC 0.921 is design-weighted; weights of sampled fatal crashes embed the FARS benchmark
for the TEST years too. Test: fit logit (pre_crash+circumstance, train 2016-21, weighted as the project does,
sklearn L2 C=100 ~ project's tiny ridge); evaluate on 2023-24 (a) with published WEIGHT, (b) with
fatal weights replaced by the mean non-fatal-A weight of the same year x region (proxy for un-benchmarked),
(c) unweighted; and (d) without alcohol_im+speeding. Also (e) temporal-split sanity: train 2016-21 only.
"""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from nhtsa_stats.models import severity_ml as S
df = S.load_crashes()
df = df[df["fatal"].notna()].reset_index(drop=True)
tr = df[df.YEAR.isin([2016,2017,2018,2019,2020,2021])]; te = df[df.YEAR.isin([2023,2024])].copy()
def fitscore(cols, label):
    pre = S.Preprocessor(list(cols)).fit(tr)
    Xtr, Xte = pre.onehot(tr), pre.onehot(te)
    m = LogisticRegression(C=100, max_iter=500).fit(Xtr, tr.fatal, sample_weight=tr.WEIGHT/tr.WEIGHT.mean())
    p = m.predict_proba(Xte)[:,1]
    a_w = roc_auc_score(te.fatal, p, sample_weight=te.WEIGHT)
    wA = te[(te.ka==1)&(te.fatal==0)].groupby(["YEAR","region"]).WEIGHT.mean().rename("wA")
    t2 = te.join(wA, on=["YEAR","region"]); w2 = np.where(t2.fatal==1, t2.wA, t2.WEIGHT)
    a_p = roc_auc_score(te.fatal, p, sample_weight=w2); a_u = roc_auc_score(te.fatal, p)
    print("%-42s AUROC weighted %.3f | fatal-wt=A-wt proxy %.3f | unweighted %.3f"%(label,a_w,a_p,a_u))
full = S.STAGES["pre_crash+circumstance"]
fitscore(full, "full model B features")
fitscore([c for c in full if c not in ("alcohol_im","speeding")], "minus alcohol_im, speeding")
fitscore([c for c in full if c not in ("alcohol_im","speeding","tod","any_motorcycle","any_heavy_truck")], "minus alcohol_im, speeding + H&R-proxy flags")
