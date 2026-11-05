"""F08 attacks 4-6.
(4) Model-free check of the composition share: DiNardo-Fortin-Lemieux reweighting (period
    propensity logit on the same model-B covariates) instead of the outcome-logit Oaxaca-Blinder.
(5) Differential ascertainment of police-recorded speeding: weighted speeding prevalence among
    fatal vs non-fatal crashes by period, and the ratio-of-ratios (CI via design linearisation).
(6) Formal period x subgroup interaction (pooled logit, covariates + period + subgroup x period,
    t with 42 df) for speeding, alcohol, motorcycle, interstate, and no-speeding-no-alcohol.
Look at: DFL composition share vs 49%/37%; speeding prevalence ratio in fatal vs non-fatal;
interaction p-values vs the published 'clearest in speeding' wording.
Run: $RT/bin/rt_py scripts/audit/red_team/F08/02_alt_estimators_and_subgroups.py
"""
import logging
import numpy as np, pandas as pd
from scipy import stats
from nhtsa_stats.analysis import trends as T
from nhtsa_stats.analysis.confounding import cluster_design
from nhtsa_stats.analysis.survey import MarginSet, ModelSpec, SurveyLogit

logging.disable(logging.WARNING)
df_all, design_all = T.load()
df, design = T.outcome_frame(df_all, design_all, "fatal")
covs = T.COVARIATE_SETS["B"]
w = design.weight
in0 = df.YEAR.isin(T.P0_YEARS).to_numpy(); in1 = ~in0
y = df.fatal.to_numpy(float)

# ---- (4) DFL reweighting
spec = ModelSpec(categorical={c: T.levels_of(df, c) for c in covs})
prop = SurveyLogit(spec, ridge=T.RIDGE).fit(df, in1.astype(float), design)
pi = prop.predict(df)                      # P(P1 | x), weighted-sample propensity
# odds adjusted for period weight totals so that reweighted P0 has the P1 covariate distribution
tilt = pi / (1 - pi) * (w[in0].sum() / w[in1].sum())
w0 = w * tilt
p0 = (w[in0] * y[in0]).sum() / w[in0].sum()
p1 = (w[in1] * y[in1]).sum() / w[in1].sum()
p0_at_P1mix = (w0[in0] * y[in0]).sum() / w0[in0].sum()      # P0 outcome structure, P1 mix
tilt1 = (1 - pi) / pi * (w[in1].sum() / w[in0].sum())
w1 = w * tilt1
p1_at_P0mix = (w1[in1] * y[in1]).sum() / w1[in1].sum()      # P1 outcome structure, P0 mix
tot = p1 - p0
print(f"DFL: p0={p0:.5f} p1={p1:.5f} RR={p1/p0:.3f}")
print(f"DFL composition share ref P0 (P0 outcomes, P1 mix): {(p0_at_P1mix-p0)/tot:.3f}  (ESS ratio {(w0[in0].sum()**2/(w0[in0]**2).sum())/in0.sum():.2f})")
print(f"DFL composition share ref P1 (P1 outcomes, P0 mix): {(p1-p1_at_P0mix)/tot:.3f}")
print(f"tilt max {tilt[in0].max():.1f}; p99 {np.percentile(tilt[in0],99):.2f}")

# ---- (5) speeding ascertainment by severity and period
sp = (df.speeding == "yes").to_numpy(float)
vals, tots = {}, {}
for per, m in (("P0", in0), ("P1", in1)):
    for k, mk in (("fatal", y == 1), ("nonfatal", y == 0)):
        d = m & mk
        vals[f"sp_{k}_{per}"], tots[f"sp_{k}_{per}"] = T.mean_lin(design, sp, d)
ms = MarginSet(vals, tots, cluster_design(design))
for k in vals: print(k, round(vals[k], 4))
for nm, f in {
    "speeding prevalence ratio P1/P0 among FATAL": lambda m: m["sp_fatal_P1"] / m["sp_fatal_P0"],
    "speeding prevalence ratio P1/P0 among NONFATAL": lambda m: m["sp_nonfatal_P1"] / m["sp_nonfatal_P0"],
    "ratio of ratios (fatal / nonfatal)": lambda m: (m["sp_fatal_P1"]/m["sp_fatal_P0"])/(m["sp_nonfatal_P1"]/m["sp_nonfatal_P0"]),
}.items():
    e = T.estimate(ms, f, "ratio"); print(nm, round(e["estimate"], 3), round(e["low"], 3), round(e["high"], 3))

# ---- (6) interaction tests
groups = {
    "speeding": (df.speeding == "yes"), "alcohol_im": (df.alcohol_im == "yes"),
    "motorcycle": (df.any_motorcycle == "yes"), "interstate": (df.interstate == "yes"),
}
df = df.copy()
for gname, g in groups.items():
    base = [c for c in covs if c not in {"speeding": ["speeding"], "alcohol_im": ["alcohol_im"],
            "motorcycle": ["any_motorcycle"], "interstate": ["interstate"]}[gname]]
    lev = ["g0_P0", "g0_P1", "g1_P0", "g1_P1"]
    df["gp"] = pd.Categorical(np.where(g, "g1", "g0") + np.where(in0, "_P0", "_P1"), categories=lev)
    sp2 = ModelSpec(categorical={**{c: T.levels_of(df, c) for c in base}, "gp": lev})
    mdl = SurveyLogit(sp2, ridge=T.RIDGE).fit(df, y, design)
    names = list(mdl.names_); b = mdl.coef_; V = mdl.vcov_
    ix = {n: i for i, n in enumerate(names)}
    k = {l: next(i for n, i in ix.items() if "gp" in n and l in n) for l in lev[1:]}
    c = np.zeros(len(b)); c[k["g1_P1"]] = 1; c[k["g1_P0"]] = -1; c[k["g0_P1"]] = -1
    est = c @ b; se = np.sqrt(c @ V @ c); t = est / se; p = 2 * stats.t.sf(abs(t), 42)
    print(f"interaction {gname}: log-OR diff {est:.3f} (se {se:.3f}) ratio-of-OR {np.exp(est):.2f} p={p:.3f}", flush=True)
