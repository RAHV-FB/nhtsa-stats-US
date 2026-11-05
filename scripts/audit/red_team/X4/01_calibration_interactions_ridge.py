"""X4-01  Model-A (fatal) specification diagnostics on CRSS.

Tests: (a) weighted calibration by predicted-risk decile (obs vs predicted, and within period
and within crash type); (b) omitted interactions: period x key exposures (Wald F) and
crash_type x key exposures in model B (Wald F); movement of standardised RRs; (c) ridge 0 vs
0.01 vs 1 on standardised RRs.  Look at: decile table, F/p, and the RR table (A vs extended).
"""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis.survey import SurveyLogit, ModelSpec

pd.set_option("display.width", 220, "display.max_columns", 30)
df, design = severity.load("fatal")
w = design.weight
y = df["fatal"].to_numpy()
print("n", len(df), "events", int(y.sum()))
mA = severity.fit(df, design, "fatal", specs.PRE_CRASH)
p = mA.predict(df)

def calib(mask, label, nb=10):
    pm, wm, ym = p[mask], w[mask], y[mask]
    # weighted deciles of predicted risk
    o = np.argsort(pm); cw = np.cumsum(wm[o]) / wm.sum()
    b = np.minimum((cw * nb).astype(int), nb - 1)
    rows = []
    for k in range(nb):
        i = o[b == k]
        rows.append((label, k + 1, wm[i].sum(), np.average(pm[i], weights=wm[i]) * 100,
                     np.average(ym[i], weights=wm[i]) * 100, int(ym[i].sum())))
    return pd.DataFrame(rows, columns=["grp", "decile", "wsum", "pred%", "obs%", "events"])
c = calib(np.ones(len(df), bool), "all"); c["O/P"] = c["obs%"] / c["pred%"]
print(c.to_string(index=False))
for lab, m in [("2016-19", df.YEAR.le(2019).to_numpy()), ("2020-24", df.YEAR.ge(2020).to_numpy())]:
    cc = calib(m, lab, 5); cc["O/P"] = cc["obs%"] / cc["pred%"]; print(cc.to_string(index=False))
# calibration by crash type (observed/predicted overall)
rows = []
for ct in specs.CRASH_LEVELS["crash_type"]:
    m = (df.crash_type == ct).to_numpy()
    rows.append((ct, int(m.sum()), int(y[m].sum()), np.average(y[m], weights=w[m]) * 100, np.average(p[m], weights=w[m]) * 100))
t = pd.DataFrame(rows, columns=["crash_type", "n", "events", "obs%", "pred%"]); t["O/P"] = t["obs%"] / t["pred%"]
print(t.to_string(index=False))

KEY = [("light", "dark_not_lighted"), ("speed_limit", "50-55"), ("speed_limit", "70+"),
       ("any_motorcycle", "yes"), ("any_heavy_truck", "yes"), ("alcohol_im", "yes"),
       ("speeding", "yes"), ("tod", "00-05"), ("older_driver", "yes"), ("interstate", "yes")]
def rr(model, d):
    out = {}
    for f, lv in KEY:
        lvls = severity.observed_levels(d, f)
        tab = severity.factor_contrasts(model, d, f, lvls).set_index("level")
        out[f"{f}={lv}"] = (tab.loc[lv, "adj_rr"], tab.loc[lv, "adj_rr_low"], tab.loc[lv, "adj_rr_high"])
    return out
base = rr(mA, df)

# (b1) period x exposure interactions
df["period"] = np.where(df.YEAR <= 2019, "p0", "p1")
spec = ModelSpec(categorical={**{c: severity.observed_levels(df, c) for c in specs.PRE_CRASH}, "period": ["p0", "p1"]},
                 interactions=[("period", c) for c in ["speeding", "alcohol_im", "light", "speed_limit", "any_motorcycle", "any_heavy_truck", "tod", "older_driver", "interstate", "surface", "urbanicity", "junction"]])
mP = SurveyLogit(spec, ridge=0.01).fit(df, y, design)
terms = [n for n in mP.names_ if n.startswith("period[p1]:")]
print("period x 12 factors:", len(terms), "terms; Wald:", {k: v for k, v in mP.wald_test(terms).items() if k != "terms"})
for f in ["speeding", "alcohol_im", "light", "speed_limit", "any_motorcycle", "any_heavy_truck", "tod", "older_driver", "interstate"]:
    tt = [n for n in terms if n.startswith(f"period[p1]:{f}[")]
    r = mP.wald_test(tt); print(f"  period x {f}: F={r['F']:.2f} p={r['p']:.4f}")
ext = rr(mP, df)
# (b2) crash_type x exposure in model B
covB = specs.PRE_CRASH + specs.CIRCUMSTANCE
mB = severity.fit(df, design, "fatal", covB)
inter = [("crash_type", c) for c in ["speeding", "alcohol_im", "light", "speed_limit", "any_motorcycle", "any_heavy_truck", "older_driver"]]
specB = ModelSpec(categorical={c: severity.observed_levels(df, c) for c in covB}, interactions=inter)
mBI = SurveyLogit(specB, ridge=0.01).fit(df, y, design)
tB = [n for n in mBI.names_ if n.startswith("crash_type[") and ":" in n]
print("crash_type x 7 factors:", len(tB), "terms; Wald:", {k: v for k, v in mBI.wald_test(tB).items() if k != "terms"})
for f in ["speeding", "alcohol_im", "light", "speed_limit", "any_motorcycle", "any_heavy_truck", "older_driver"]:
    tt = [n for n in tB if n.endswith(tuple(f"{f}[{l}]" for l in severity.observed_levels(df, f)))]
    r = mBI.wald_test(tt); print(f"  crash_type x {f}: q={r['q']} F={r['F']:.2f} p={r['p']:.4f}")
baseB, extB = rr(mB, df), rr(mBI, df)
# (c) ridge
rows = []
for rg in (0.0, 0.01, 1.0, 100.0):
    m = severity.fit(df, design, "fatal", specs.PRE_CRASH, ridge=rg)
    r_ = rr(m, df); rows.append({"ridge": rg, **{k: v[0] for k, v in r_.items()}})
print(pd.DataFrame(rows).round(3).to_string(index=False))
res = pd.DataFrame({"A": {k: v[0] for k, v in base.items()}, "A+period_ix": {k: v[0] for k, v in ext.items()},
                    "B": {k: v[0] for k, v in baseB.items()}, "B+type_ix": {k: v[0] for k, v in extB.items()}})
res["period_ratio"] = res["A+period_ix"] / res["A"]; res["type_ratio"] = res["B+type_ix"] / res["B"]
print(res.round(3).to_string())
