"""F11 attack 5: are the two 'confirmed' interactions robust? Re-estimate the product-term log OR
(full main-effects adjustment, weighted pseudo-ML logit, point estimates only) for
speeding=yes x mv_angle and intersection x mv_head_on in (a) test 2023-24 (published: +0.744 / -1.761),
(b) training years 2016-21, (c) 2023 vs 2024 separately, (d) alternative reference crash types
(all non-angle / non-head-on), (e) speeding unknown dropped. Look at sign and size stability, and cell event counts."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from nhtsa_stats.models import severity_ml as m
df = m.load_crashes(); df = df[df.fatal.notna()]
stage="pre_crash+circumstance"; cats=list(m.STAGES[stage])
def coef(d, prod, label):
    pre = m.Preprocessor(cats).fit(d)
    X = pre.onehot(d); col = prod(d).astype(float)
    X = np.column_stack([X, col])
    est = LogisticRegression(C=m.RIDGE_C, **m.LOGIT_SOLVER).fit(X, d.fatal.values, sample_weight=m._weights(d))
    ev = int(((col==1)&(d.fatal==1)).sum())
    print(f"{label:70s} coef={est.coef_[0][-1]:+.3f}  ROR={np.exp(est.coef_[0][-1]):.2f}  n_cell={int((col==1).sum())} events_in_cell={ev}")
sp = lambda d: (d.speeding=="yes")&(d.crash_type=="mv_angle")
hd = lambda d: (d.junction=="intersection")&(d.crash_type=="mv_head_on")
te = df[df.YEAR.isin([2023,2024])]; tr = df[df.YEAR.isin(range(2016,2022))]
for nm,pr in [("speeding x angle",sp),("intersection x head-on",hd)]:
    # NB: product alone with the main-effect dummies already present = refs as in published
    coef(te,pr,nm+" | test 2023-24")
    coef(tr,pr,nm+" | TRAIN 2016-21")
    coef(df[df.YEAR==2023],pr,nm+" | 2023")
    coef(df[df.YEAR==2024],pr,nm+" | 2024")
    coef(df[df.YEAR==2022],pr,nm+" | 2022 (valid)")
coef(te[te.speeding!="unknown"],sp,"speeding x angle | test, speeding known only")
coef(te[te.crash_type.isin(["mv_angle","mv_rear_end"])],sp,"speeding x angle | test, angle & rear-end crashes only")
# unweighted
d=te.copy(); d["WEIGHT"]=1.0; coef(d,sp,"speeding x angle | test UNWEIGHTED")
d=te.copy(); d["WEIGHT"]=1.0; coef(d,hd,"intersection x head-on | test UNWEIGHTED")
