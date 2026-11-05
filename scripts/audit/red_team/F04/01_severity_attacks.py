"""F04 attacks on the severity RRs (CRSS fatal, model A).
Tests: (0) reproduce motorcycle/50-55/70+/unlit/heavy; (1) 'as severe as': direct contrast 50-55 vs 70+ and
60-65 vs 50-55 (needs margins diff); (2) sensitivity of speed-limit RRs to adjustment set: drop interstate /
drop speeding+alcohol (mediators of road class) ; (3) rural-only restriction for the speed ladder.
Look at: RR values and CI of 70+ vs 50-55 ratio under each spec."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
df, design = severity.load("fatal")
SL = severity.observed_levels(df, "speed_limit", specs.CRASH_LEVELS["speed_limit"])
def ladder(d, des, covs, tag):
    m = severity.fit(d, des, "fatal", covs)
    sc = {str(l): (lambda x, l=l: x.assign(speed_limit=l)) for l in SL}
    ms = m.margins(d, sc)
    out = {}
    for l in ["50-55","60-65","70+","40-45"]:
        e = ms.log_ratio(l,"30-35"); lo,hi = e.ci(); out[l]=(np.exp(e.estimate),np.exp(lo),np.exp(hi))
    r = ms.log_ratio("70+","50-55"); lo,hi = r.ci()
    r2 = ms.log_ratio("60-65","50-55"); lo2,hi2 = r2.ci()
    print(f"[{tag}] n={len(d)}", {k:tuple(round(x,2) for x in v) for k,v in out.items()},
          "| 70+/50-55 RR %.2f (%.2f-%.2f)"%(np.exp(r.estimate),np.exp(lo),np.exp(hi)),
          "| 60-65/50-55 %.2f (%.2f-%.2f)"%(np.exp(r2.estimate),np.exp(lo2),np.exp(hi2)), flush=True)
    return m
m = ladder(df, design, specs.PRE_CRASH, "A published spec")
for f,lv in (("any_motorcycle",["no","yes"]),("any_heavy_truck",["no","yes"]),("light",["daylight","dark_not_lighted"])):
    t = severity.factor_contrasts(m, df, f, severity.observed_levels(df,f,specs.CRASH_LEVELS[f]))
    print(t[["factor","level","adj_rr","adj_rr_low","adj_rr_high"]].to_string(index=False))
ladder(df, design, [c for c in specs.PRE_CRASH if c!="interstate"], "A minus interstate")
ladder(df, design, [c for c in specs.PRE_CRASH if c not in("interstate","speeding","alcohol_im")], "A minus interstate,speeding,alcohol")
print(df["urbanicity"].value_counts().to_dict())
for u in ("rural","urban"):
    k = (df["urbanicity"]==u).to_numpy()
    d = df.loc[k].reset_index(drop=True)
    ladder(d, design.subset(k), [c for c in specs.PRE_CRASH if c!="urbanicity"], f"A, {u} only")
print(pd.crosstab(df["speed_limit"], df["interstate"], normalize="index").round(2).to_string())
