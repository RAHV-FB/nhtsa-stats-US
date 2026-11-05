"""F11 attacks 1-4 (logit_main, pre_crash+circumstance, fatal): reproduce published logistic
weighted AUROC 0.903 on 2023-24; then ablate inputs that are recorded after the crash or are
unknown-code proxies (speeding, alcohol_im, unknown indicators), compare weighted/unweighted,
by test year, and recompute lowest-half O/P. Look at AUROC deltas vs the 0.9029 baseline."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from nhtsa_stats.models import severity_ml as m

def wauc(p, y, w):
    o = np.argsort(p, kind="mergesort"); p, y, w = p[o], y[o], w[o]
    # tie-aware via groups
    _, idx = np.unique(p, return_index=True)
    wy = np.add.reduceat(w*y, idx); wn = np.add.reduceat(w*(1-y), idx)
    cn = np.cumsum(wn) - wn
    return (np.sum(wy*(cn + 0.5*wn))) / (wy.sum()*wn.sum())

df = m.load_crashes()
df = df[df["fatal"].notna()]
tr = df[df.YEAR.isin(range(2016,2022))]; te = df[df.YEAR.isin([2023,2024])]
print("n train/test", len(tr), len(te), "events", int(tr.fatal.sum()), int(te.fatal.sum()))
stage = "pre_crash+circumstance"
cats_full = list(m.STAGES[stage])
def run(cats, label, numeric=None, extra=None):
    pre = m.Preprocessor(cats, numeric=m.NUMERIC if numeric is None else numeric).fit(tr)
    est = LogisticRegression(C=m.RIDGE_C, **m.LOGIT_SOLVER)
    est.fit(pre.onehot(tr), tr.fatal.values, sample_weight=m._weights(tr))
    p = est.predict_proba(pre.onehot(te))[:,1]
    y = te.fatal.values; w = te.WEIGHT.values
    r = dict(variant=label, auc_w=wauc(p,y,w), auc_unw=wauc(p,y,np.ones_like(w)),
             auc_2023=wauc(p[te.YEAR.values==2023],y[te.YEAR.values==2023],w[te.YEAR.values==2023]),
             auc_2024=wauc(p[te.YEAR.values==2024],y[te.YEAR.values==2024],w[te.YEAR.values==2024]),
             oe=(w*y).sum()/(w*p).sum())
    cut = m.weighted_quantile(p, w, 0.5); lo = p <= cut
    r["oe_lowest_half"] = (w*y)[lo].sum()/(w*p)[lo].sum()
    return r, p
rows=[]
r,p0 = run(cats_full,"full (published logit_main)"); rows.append(r)
for drop,label in [(["speeding","alcohol_im"],"drop speeding+alcohol_im"),
                   (["speeding","alcohol_im","n_vehicles"],"drop speeding+alcohol_im+n_vehicles"),
                   (["crash_type","n_vehicles"],"pre-crash only (no configuration)")]:
    rows.append(run([c for c in cats_full if c not in drop],label)[0])
rows.append(run([c for c in cats_full if c not in ["speeding","alcohol_im","any_motorcycle","any_heavy_truck","tod"]],
                "drop speeding,alcohol_im,motorcycle,heavy_truck,tod (hit-and-run-unknown carriers)", numeric=["speed_limit_mph"])[0])
# unknown-only model: indicators of 'unknown' levels / missing numerics
def unk(d):
    X = pd.DataFrame(index=d.index)
    for c in cats_full: X["u_"+c] = (d[c].astype(object)=="unknown").astype(float)
    X["u_age"] = d.oldest_vehicle_age.isna().astype(float); X["u_lim"]=d.speed_limit_mph.isna().astype(float)
    return X.loc[:, X.std()>0] if False else X
Xt, Xe = unk(tr), unk(te)
keep = [c for c in Xt if Xt[c].std()>0]
est = LogisticRegression(C=100, max_iter=500); est.fit(Xt[keep], tr.fatal, sample_weight=m._weights(tr))
pu = est.predict_proba(Xe[keep])[:,1]
rows.append(dict(variant="UNKNOWN-INDICATORS ONLY (no substantive info)", auc_w=wauc(pu,te.fatal.values,te.WEIGHT.values),
                 auc_unw=wauc(pu,te.fatal.values,np.ones(len(te)))))
out = pd.DataFrame(rows); pd.set_option("display.width",220); print(out.round(4).to_string())
out.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F11/01.csv", index=False)
