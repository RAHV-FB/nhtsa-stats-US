"""F02: effect heterogeneity / positivity. Refit model A within subsets and report the target contrast.
 rain vs clear on wet surface only (rain on dry is ~empty); interstate within speed-limit bands;
 older-driver within low (<=45) vs high (>=50 mph) speed limits; night 00-05 within urban/rural.
Look at: does the pooled standardised RR (0.70 interstate, 1.66 older) describe every stratum?"""
import sys, pandas as pd
from nhtsa_stats.analysis import severity, specs
outcome = sys.argv[1] if len(sys.argv) > 1 else "fatal"
df, design = severity.load(outcome)
def sub(mask, drop, factor, lv, label):
    keep = mask.to_numpy()
    d = df.loc[keep].reset_index(drop=True); dsg = design.subset(keep)
    cov = [c for c in specs.PRE_CRASH if c not in drop]
    try:
        m = severity.fit(d, dsg, outcome, cov)
        levels = severity.observed_levels(d, factor, specs.CRASH_LEVELS[factor])
        t = severity.factor_contrasts(m, d, factor, levels)
        r = t[t.level == lv].iloc[0]
        print(f"{outcome} | {label:42s} | n={len(d):6d} ev={int(d[outcome].sum()):5d} | {factor}:{lv} RR={r.adj_rr:.2f} ({r.adj_rr_low:.2f}-{r.adj_rr_high:.2f})", flush=True)
    except Exception as e:
        print(label, "FAILED", repr(e)[:200])
w = df.weather.isin(["clear","rain"])
sub(df.surface=="wet", ["surface"], "weather", "rain", "rain vs clear, wet surface only")
sub(df.surface=="dry", ["surface"], "weather", "rain", "rain vs clear, dry surface only")
sub(w, ["surface"], "weather", "rain", "rain vs clear, all surfaces, no surface adj")
for lab, mask in [("speed 30-45", df.speed_limit.isin(["30-35","40-45","<=25"])), ("speed 50-65", df.speed_limit.isin(["50-55","60-65"])), ("speed 70+", df.speed_limit=="70+")]:
    sub(mask, [], "interstate", "yes", "interstate, "+lab)
for lab, mask in [("speed <=45", df.speed_limit.isin(["30-35","40-45","<=25"])), ("speed >=50", df.speed_limit.isin(["50-55","60-65","70+"]))]:
    sub(mask, [], "older_driver", "yes", "older driver, "+lab)
for lab, mask in [("urban", df.urbanicity=="urban"), ("rural", df.urbanicity=="rural")]:
    sub(mask, ["urbanicity"], "tod", "00-05", "night 00-05, "+lab)
