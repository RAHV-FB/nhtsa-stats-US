"""F02: reproduce model-A headline RRs (night 00-05, rain, interstate, older, young) and run
leave-one-covariate-out sensitivity: which adjuster drives each reversal/unmasking?
Look at: row 'full' = published; others = model A minus the named covariate(s)."""
import sys, pandas as pd
from nhtsa_stats.analysis import severity, specs
outcome = sys.argv[1] if len(sys.argv) > 1 else "fatal"
df, design = severity.load(outcome)
targets = {"tod": ("00-05", "10-15"), "weather": ("rain", "clear"), "interstate": ("yes", "no"),
           "older_driver": ("yes", "no"), "young_driver": ("yes", "no")}
def run(label, drop):
    cov = [c for c in specs.PRE_CRASH if c not in drop]
    m = severity.fit(df, design, outcome, cov)
    out = []
    for f, (lv, ref) in targets.items():
        if f in drop: continue
        levels = severity.observed_levels(df, f, specs.CRASH_LEVELS[f])
        t = severity.factor_contrasts(m, df, f, levels)
        r = t[t.level == lv].iloc[0]
        out.append(f"{f}={r.adj_rr:.2f}({r.adj_rr_low:.2f}-{r.adj_rr_high:.2f})")
    print(f"{outcome} | {label:28s} | " + "  ".join(out), flush=True)
run("full (model A)", [])
for d in [["speed_limit"], ["urbanicity"], ["speed_limit","urbanicity"], ["junction"], ["alcohol_im"], ["speeding"],
          ["alcohol_im","speeding"], ["any_motorcycle"], ["any_heavy_truck"], ["surface"], ["light"], ["weekend"]]:
    run("minus " + "+".join(d), d)
