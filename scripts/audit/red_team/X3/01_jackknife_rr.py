"""X3 test 1: stratified delete-one-PSU jackknife (JKn) for model-A adjusted fatal RRs.
Claim tested: published linearised (Taylor, t42) CIs for adjusted RRs in
outputs/tables/severity/fatal_crude_vs_adjusted.csv (A_adj_rr*). Method: refit the weighted logit
with each of the 67 PSUs deleted (other PSUs in its stratum scaled n_h/(n_h-1)), recompute the
standardised margin RRs, JKn variance of log RR around the full-sample estimate.
Usage: 01_jackknife_rr.py START END  (replicate index range, to fit within the 420 s limit).
Output: $RT/work/X3/jk_{START}_{END}.csv  (log margins per replicate).  Run 02 to combine."""
import sys, time, numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis.survey import SurveyDesign, _sigmoid
OUT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/X3"
TARGETS = {"light": ("daylight", "dark_not_lighted"), "any_motorcycle": ("no", "yes"),
           "speeding": ("no", "yes"), "alcohol_im": ("no", "yes"),
           "speed_limit": ("30-35", "50-55"), "interstate": ("no", "yes"),
           "older_driver": ("no", "yes"), "tod": ("10-15", "00-05")}

def margins(m, df):
    out = {}
    for f, (ref, lv) in TARGETS.items():
        for name, val in (("ref", ref), ("lv", lv)):
            cf = df.copy(deep=False); cf[f] = val
            xa = m.spec.update_matrix(m._x, df, cf)
            out[f"{f}|{name}"] = float((m._w * _sigmoid(xa @ m.coef_)).sum() / m._w.sum())
    return out

df, d0 = severity.load("fatal")
a, b = int(sys.argv[1]), int(sys.argv[2])
rows = []
t0 = time.time()
if a == 0:
    m = severity.fit(df, d0, "fatal", specs.PRE_CRASH)
    r = margins(m, df); r["rep"] = -1; rows.append(r)
    print("full fit", round(time.time() - t0, 1), "s")
for c in range(a, min(b, d0.n_clusters)):
    h = d0.cluster_stratum[c]
    nh = int((d0.cluster_stratum == h).sum())
    w = d0.weight.copy()
    inh = d0.stratum == h
    w = np.where(inh, w * nh / (nh - 1), w)
    w = np.where(d0.cluster == c, 0.0, w)
    d = SurveyDesign(w, d0.stratum, d0.cluster, d0.cluster_stratum)
    m = severity.fit(df, d, "fatal", specs.PRE_CRASH)
    r = margins(m, df); r["rep"] = c; r["stratum"] = h; r["nh"] = nh; rows.append(r)
    print(c, round(time.time() - t0, 1), flush=True)
pd.DataFrame(rows).to_csv(f"{OUT}/jk_{a}_{b}.csv", index=False)
