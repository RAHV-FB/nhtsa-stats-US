"""G03 attack: (a) apply the pre-specified 2022 rule (log loss within 1%, AUROC within .005)
to the crash-type-interaction logistic 'xt' from 01 -> would the rule have selected it over hgb?
(b) bootstrap (100 Rao-Wu reps, 2022) the margin of hgb over logit_main on the rule metrics;
(c) test-year O/E by tier of predicted risk (hgb): what 'stratification' use sees."""
import numpy as np, pandas as pd
from nhtsa_stats.models import severity_ml as m
from nhtsa_stats import config
RT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/G03/"
P = dict(np.load(RT + "preds.npz"))
df = m.load_crashes(); df = df[df["fatal"].notna()]
va = df[df.YEAR.isin(config.VALID_YEARS)].reset_index(drop=True); te = df[df.YEAR.isin(config.TEST_YEARS)].reset_index(drop=True)
res = {k: m._point_metrics(P["va_" + k], va.fatal.values, va.WEIGHT.values) for k in ("main", "int", "xt", "hgb")}
best_ll = min(r["log_loss"] for r in res.values()); best_auc = max(r["auroc"] for r in res.values())
for k, r in res.items():
    print(f"2022 {k:5s} ll={r['log_loss']:.5f} ({r['log_loss']/best_ll-1:+.2%}) auc={r['auroc']:.4f} ({r['auroc']-best_auc:+.4f}) passes_rule={r['log_loss']<=best_ll*1.01 and r['auroc']>=best_auc-0.005}")
cidx, cs = m.cluster_index(va.PSUSTRAT.values, va.PSU_VAR.values)
mult = m.rao_wu_multipliers(cs, 100, np.random.default_rng(2))
B = {k: m.GroupedScores(P["va_" + k], va.fatal.values, va.WEIGHT.values, cidx, len(cs), resolution=m.BOOT_RESOLUTION).metrics(mult, calibration=False) for k in res}
for k in ("main", "int", "xt"):
    llr = B[k]["log_loss"] / B["hgb"]["log_loss"] - 1; da = B["hgb"]["auroc"] - B[k]["auroc"]
    print(f"2022 boot {k}: log-loss excess vs hgb mean {llr.mean():+.3%} (2.5-97.5%: {np.percentile(llr,2.5):+.3%},{np.percentile(llr,97.5):+.3%}); AUROC gap {da.mean():+.4f} ({np.percentile(da,2.5):+.4f},{np.percentile(da,97.5):+.4f}); share of reps where {k} passes rule vs hgb: {np.mean((llr<=0.01)&(da<=0.005)):.2f}")
# tiers on test
p = P["te_hgb"]; w = te.WEIGHT.values; y = te.fatal.values
q = m.weighted_quantile(p, w, np.array([.5, .8, .95, .99]))
tier = np.searchsorted(q, p, side="right")
lab = ["bottom 50%", "50-80%", "80-95%", "95-99%", "top 1%"]
for t in range(5):
    mk = tier == t; print(f"test hgb tier {lab[t]:11s} n={mk.sum():6d} fatal={int(y[mk].sum()):5d} O/E={ (w[mk]*y[mk]).sum()/(w[mk]*p[mk]).sum():.3f} meanpred={ (w[mk]*p[mk]).sum()/w[mk].sum():.4f}")
