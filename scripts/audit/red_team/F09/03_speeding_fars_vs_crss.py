"""F09 attack 7: is 'CRSS records speeding in 20% of fatal crashes vs 27% in FARS for the same population'
a clean recording-completeness comparison? Pooled 2016-2024 with design-based CI; by speeding type;
among known; observed-K vs imputed-fatal CRSS definition; single-vehicle subset; ratio by year."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.survey import svy_mean
from nhtsa_stats.analysis.measurement import observed_severity
df, design = data.crss_crash(outcome=None)
sev = observed_severity(df.MAX_SEV)
fc = data.fars_crash()
print("FARS crash cols w/ speed:", [c for c in fc.columns if "speed" in c])
sp_f = (fc.speeding == 1)
print("FARS pooled speeding %.1f  unknown %.1f  among known %.1f" % (100*sp_f.mean(), 100*fc.speeding.isna().mean(), 100*sp_f.sum()/fc.speeding.notna().sum()))
x = df.speeding.to_numpy(float)
def rep(lab, dom):
    r = svy_mean(design, (x == 1).astype(float), dom); u = svy_mean(design, np.isnan(x).astype(float), dom)
    k = svy_mean(design, (x == 1).astype(float), dom & ~np.isnan(x))
    print(f"{lab:34s} n={int(dom.sum()):5d} speeding {100*r.estimate:5.1f} ({100*(r.estimate-1.96*r.se):4.1f}-{100*(r.estimate+1.96*r.se):4.1f}) unk {100*u.estimate:4.1f} known-only {100*k.estimate:5.1f}")
rep("CRSS observed K 2016-24", sev == 4)
for a, b in [(2016, 2018), (2019, 2024)]:
    rep(f"CRSS observed K {a}-{b}", (sev == 4) & (df.YEAR.between(a, b)).to_numpy())
    f = fc[fc.YEAR.between(a, b)]; print(f"   FARS {a}-{b}: %.1f" % (100*(f.speeding == 1).mean()))
# imputed fatal definition
d2, des2 = __import__("nhtsa_stats.analysis.severity", fromlist=["x"]).load("fatal")
print("severity.load('fatal') cols:", [c for c in d2.columns if c in ("fatal", "speeding", "n_killed")])
r = svy_mean(des2, (d2.speeding == 1).astype(float).to_numpy(), (d2.fatal == 1).to_numpy())
print("CRSS imputed-fatal speeding %.1f (SE %.1f)" % (100*r.estimate, 100*r.se))
print("\nspeeding_type distribution among fatal crashes (% of all)")
st_c = df.speeding_type.astype(str).to_numpy()
for t in sorted(set(st_c[sev == 4])):
    r = svy_mean(design, (st_c == t).astype(float), sev == 4)
    print(f"  CRSS {t:28s} {100*r.estimate:5.1f}   FARS {100*(fc.speeding_type.astype(str) == t).mean():5.1f}")
print("\nsingle-vehicle & multi-vehicle subset, by year ratio")
sv = [c for c in df.columns if "single" in c or c in ("n_vehicles", "veh_count")]; print(sv, [c for c in fc.columns if "single" in c or c=="n_vehicles"])
