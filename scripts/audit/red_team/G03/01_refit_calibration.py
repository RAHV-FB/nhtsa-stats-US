"""G03 attack 1-3: refit fatal/circumstance-stage logit_main, logit_interact, hgb(31,100) and a
'logit_xtype' (main effects + crash_type x {junction, speeding, speed band, motorcycle, light}
products, C=10) on 2016-21 with the project's own code; score on 2023-24.
Reproduces calibration slope / O/E overall and by hit-and-run, then asks
 (a) is the hit-and-run O/E 0.6 structural (present in 2022 and in-sample training years too)?
 (b) is it driven by 'unknown' proxy levels?
 (c) does a crash-type-interaction logistic close the hgb gap (AUROC, Brier skill, log loss),
     with paired Rao-Wu cluster bootstrap (100 reps)?
Saves test predictions to work/G03/preds.npz."""
import os, sys, time
import numpy as np, pandas as pd
from nhtsa_stats.models import severity_ml as m
from nhtsa_stats import config
RT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/G03/"
t0 = time.time()
df = m.load_crashes(); df = df[df["fatal"].notna()].reset_index(drop=True)
tr = df[df.YEAR.isin(config.TRAIN_YEARS)].reset_index(drop=True)
va = df[df.YEAR.isin(config.VALID_YEARS)].reset_index(drop=True)
te = df[df.YEAR.isin(config.TEST_YEARS)].reset_index(drop=True)
print("rows", len(tr), len(va), len(te), "fatal test", int(te.fatal.sum()))
stage = "pre_crash+circumstance"; out = "fatal"
pre = m.Preprocessor(list(m.STAGES[stage])).fit(tr)
xtr = pre.onehot(tr)
fm = m.fit_logistic(pre, tr, out, m.RIDGE_C, "logit_main", stage, x=xtr)
pre_i = m.Preprocessor(list(m.STAGES[stage]), products=m.stage_products(stage)).fit(tr)
fi = m.fit_logistic(pre_i, tr, out, m.RIDGE_C, "logit_interact", stage)
hg = m.fit_hgb(pre, tr, out, dict(learning_rate=0.1, max_leaf_nodes=31, min_samples_leaf=100), stage)
print("hgb iters", hg.params, f"{time.time()-t0:.0f}s")
# crash_type x other dummies
names = pre.onehot_names_
ct = [i for i, n in enumerate(names) if n.startswith("crash_type[")]
oth = [i for i, n in enumerate(names) if n.split("[")[0] in ("junction", "speeding", "speed_limit", "any_motorcycle", "light")]
print("xtype products:", len(ct) * len(oth))
def xt(x):
    P = np.hstack([x[:, [a]] * x[:, oth] for a in ct]); keep = np.asarray(xt.keep) if hasattr(xt, "keep") else None
    return P
Ptr = xt(xtr); keep = Ptr.sum(0) >= 1  # at least one crash; ridge handles sparsity
xt.keep = np.flatnonzero((Ptr[tr.fatal.values == 1] != 0).sum(0) >= 5)  # >=5 fatal crashes in cell
print("kept products", len(xt.keep))
def X2(df_, x): return np.hstack([x, xt(x)[:, xt.keep]])
from sklearn.linear_model import LogisticRegression
est = LogisticRegression(C=10.0, **m.LOGIT_SOLVER).fit(X2(tr, xtr), tr.fatal.values, sample_weight=m._weights(tr))
print("xtype fit", f"{time.time()-t0:.0f}s")
P = {}
for nm, d in (("va", va), ("te", te)):
    P[nm + "_main"] = fm.predict(d); P[nm + "_int"] = fi.predict(d); P[nm + "_hgb"] = hg.predict(d)
    P[nm + "_xt"] = est.predict_proba(X2(d, pre.onehot(d)))[:, 1]
P["tr_main"] = fm.predict(tr); P["tr_hgb"] = hg.predict(tr)
np.savez(RT + "preds.npz", **P)
# overall metrics
def met(p, d, mask=None):
    mk = np.ones(len(d), bool) if mask is None else mask
    return m._point_metrics(p[mk], d.fatal.values[mk], d.WEIGHT.values[mk])
rows = []
for k in ("main", "int", "xt", "hgb"):
    r = met(P["te_" + k], te); rows.append({"model": k, **{x: r[x] for x in ("auroc", "brier_skill", "log_loss", "oe_ratio", "calibration_slope")}})
print(pd.DataFrame(rows).round(5).to_string())
# O/E by hit-and-run, sample and period
for nm, d in (("train", tr), ("valid2022", va), ("test", te)):
    for k in ("main", "hgb"):
        p = P[("tr" if nm == "train" else "va" if nm.startswith("valid") else "te") + "_" + k]
        for hr in ("yes", "no"):
            mk = (d.hit_and_run == hr).values
            r = met(p, d, mk)
            print(f"{nm:10s} {k:5s} hit_and_run={hr:3s} n={mk.sum():6d} fatal={int(d.fatal.values[mk].sum()):5d} O/E={r['oe_ratio']:.3f} slope={r['calibration_slope']:.2f} prevalence={r['prevalence']:.4f}")
# proxy unknown within hit-and-run (test)
proxy = ["tod", "any_motorcycle", "any_heavy_truck", "speeding", "oldest_vehicle_age"]
unk = np.zeros(len(te), bool)
for c in proxy:
    v = te[c]; unk |= (v.astype(str).isin(["unknown"]) | v.isna()).values
for hr in ("yes", "no"):
    for u in (True, False):
        mk = ((te.hit_and_run == hr).values) & (unk == u)
        if mk.sum() > 50:
            r = met(P["te_hgb"], te, mk); print(f"test hgb hit_and_run={hr} proxy_unknown={u} n={mk.sum()} fatal={int(te.fatal.values[mk].sum())} O/E={r['oe_ratio']:.3f} meanpred={r['mean_predicted']:.4f}")
# crash type among hit-and-run vs not (test, weighted share)
w = te.WEIGHT
print(te.groupby("hit_and_run").apply(lambda g: pd.Series({"W_share_ped": (g.WEIGHT*(g.crash_family=="pedestrian_cyclist")).sum()/g.WEIGHT.sum(), "wfatal": (g.WEIGHT*g.fatal).sum()/g.WEIGHT.sum()})).round(4))
# paired bootstrap hgb vs xtype vs int, test
cidx, cs = m.cluster_index(te.PSUSTRAT.values, te.PSU_VAR.values)
mult = m.rao_wu_multipliers(cs, 100, np.random.default_rng(1))
G = {k: m.GroupedScores(P["te_" + k], te.fatal.values, te.WEIGHT.values, cidx, len(cs), resolution=m.BOOT_RESOLUTION) for k in ("main", "int", "xt", "hgb")}
B = {k: g.metrics(mult, calibration=False) for k, g in G.items()}
for a, b in (("hgb", "main"), ("hgb", "int"), ("hgb", "xt"), ("xt", "main"), ("int", "main")):
    for mt in ("auroc", "brier_skill", "log_loss"):
        d = B[a][mt] - B[b][mt]; lo, hi = np.percentile(d, [2.5, 97.5])
        print(f"paired {a}-{b} {mt}: {np.mean(d):+.5f} ({lo:+.5f},{hi:+.5f})")
print("done", f"{time.time()-t0:.0f}s")
