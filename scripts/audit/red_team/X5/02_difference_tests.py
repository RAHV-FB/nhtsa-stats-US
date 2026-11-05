"""X5-02: The difference tests the reports imply but never run.
(a) Alcohol RR 2016-18 vs 2019-24 (published 5.4 vs 3.8, "intervals overlap" style): joint survey logit
    (model A covariates, YEAR kept) + alcohol_im 'yes' x late(2019+) product; Wald F on the product and
    design-based test of log RR(early) - log RR(late) from standardised margins in each period domain.
(b) Within-circumstance rise (published speeding 1.38 vs alcohol 1.01 vs all 1.11): joint model B
    covariates (no YEAR) + late + late x {speeding, alcohol_im, motorcycle, pedestrian-config via crash_type
    not used}; Wald F for heterogeneity and test log WR(speeding) - log WR(alcohol), log WR(speeding) -
    log WR(neither).  Pooled-slope model => numbers differ from the published separate-period fits.
Look at p-values and the CI of the difference.
"""
import numpy as np, pandas as pd
from scipy import stats
from nhtsa_stats.analysis import severity, specs, trends
from nhtsa_stats.analysis.survey import SurveyLogit, ModelSpec

def tst(est):
    z = est.estimate / est.se
    return est.estimate, est.se, 2 * stats.t.sf(abs(z), est.df)

df, design = severity.load("fatal")
y = df["fatal"].to_numpy()
late = (df.YEAR >= 2019).to_numpy().astype(float)
cov = [c for c in specs.PRE_CRASH]
levels = {c: severity.observed_levels(df, c, specs.CRASH_LEVELS[c]) for c in cov}
df = df.copy(); df["x_late_alc"] = late * (df.alcohol_im == "yes").to_numpy()
spec = ModelSpec(categorical=levels, numeric=["x_late_alc"])
m = SurveyLogit(spec, ridge=severity.RIDGE).fit(df, y, design)
print("converged", m.converged_)
w = m.wald_test(["x_late_alc"]); print("(a) alcohol x late product: F=%.2f p=%.4f" % (w["F"], w["p"]))
def setter(v):
    def f(d):
        d = d.copy(); d["alcohol_im"] = v; d["x_late_alc"] = late * (v == "yes"); return d
    return f
sc = {"y_e": setter("yes"), "n_e": setter("no"), "y_l": setter("yes"), "n_l": setter("no")}
# separate domains -> run margins twice
ms_e = m.margins(df, {"y": setter("yes"), "n": setter("no")}, domain=(late == 0))
ms_l = m.margins(df, {"y": setter("yes"), "n": setter("no")}, domain=(late == 1))
# combine margin sets
from nhtsa_stats.analysis.survey import MarginSet
vals = {**{k + "_e": v for k, v in ms_e.values.items()}, **{k + "_l": v for k, v in ms_l.values.items()}}
infl = {**{k + "_e": v for k, v in ms_e.influence.items()}, **{k + "_l": v for k, v in ms_l.influence.items()}}
ms = MarginSet(vals, infl, ms_e.design)
for nm, a, b in [("RR early", "y_e", "n_e"), ("RR late", "y_l", "n_l")]:
    e = ms.log_ratio(a, b); print(f"   {nm}: {np.exp(e.estimate):.2f} ({np.exp(e.estimate-2.018*e.se):.2f}-{np.exp(e.estimate+2.018*e.se):.2f})")
e = ms.contrast(lambda m_: float(np.log(m_["y_e"] / m_["n_e"]) - np.log(m_["y_l"] / m_["n_l"])))
est, se, p = tst(e); print("   log RR(early)-log RR(late) = %.3f (SE %.3f), ratio of RRs %.2f (%.2f-%.2f), p=%.4f" % (est, se, np.exp(est), np.exp(est-2.018*se), np.exp(est+2.018*se), p))

print("\n(b) within-circumstance heterogeneity, model B covariates, no YEAR")
cov2 = [c for c in specs.PRE_CRASH if c != "YEAR"] + specs.CIRCUMSTANCE
df2, design2 = severity.load("fatal")
lv2 = {c: severity.observed_levels(df2, c, specs.CRASH_LEVELS[c]) for c in cov2}
late = (df2.YEAR >= 2020).to_numpy().astype(float)   # project's P1 = 2020-24
flags = {"spd": (df2.speeding == "yes").to_numpy(), "alc": (df2.alcohol_im == "yes").to_numpy(), "moto": (df2.any_motorcycle == "yes").to_numpy()}
def build(d, l, fl):
    d = d.copy(); d["late"] = l
    for k, f in fl.items(): d["late_" + k] = l * f
    return d
df2 = build(df2, late, flags)
spec2 = ModelSpec(categorical=lv2, numeric=["late", "late_spd", "late_alc", "late_moto"])
m2 = SurveyLogit(spec2, ridge=severity.RIDGE).fit(df2, df2["fatal"].to_numpy(), design2)
print("converged", m2.converged_)
for t in ["late_spd", "late_alc", "late_moto"]:
    w = m2.wald_test([t]); print("   %s: F=%.2f p=%.4f" % (t, w["F"], w["p"]))
w = m2.wald_test(["late_spd", "late_alc", "late_moto"]); print("   joint 3 terms: F=%.2f p=%.4f" % (w["F"], w["p"]))
def setl(v):
    def f(d):
        # setter re-derives interaction columns from the flags of the (unchanged) rows
        d = d.copy(); d["late"] = v
        for k, fl in flags.items(): d["late_" + k] = v * fl
        return d
    return f
res = {}
doms = {"all": np.ones(len(df2), bool), "spd": flags["spd"], "alc": flags["alc"], "moto": flags["moto"], "neither": ~(flags["spd"] | flags["alc"])}
vals, infl = {}, {}
for dn, dm in doms.items():
    mm = m2.margins(df2, {"1": setl(1.0), "0": setl(0.0)}, domain=dm)
    for k in ("1", "0"): vals[dn + k] = mm.values[k]; infl[dn + k] = mm.influence[k]
ms2 = MarginSet(vals, infl, design2)
for dn in doms:
    e = ms2.log_ratio(dn + "1", dn + "0"); print(f"   within RR {dn:8s}: {np.exp(e.estimate):.3f} ({np.exp(e.estimate-2.018*e.se):.3f}-{np.exp(e.estimate+2.018*e.se):.3f})")
for a, b in [("spd", "alc"), ("spd", "neither"), ("spd", "moto"), ("alc", "neither")]:
    e = ms2.contrast(lambda m_: float(np.log(m_[a+"1"]/m_[a+"0"]) - np.log(m_[b+"1"]/m_[b+"0"])))
    est, se, p = tst(e); print(f"   diff of log within-RR {a} - {b}: ratio {np.exp(est):.2f} ({np.exp(est-2.018*se):.2f}-{np.exp(est+2.018*se):.2f}) p={p:.4f}")
