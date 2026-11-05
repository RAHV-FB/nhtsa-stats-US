"""F09 attacks 4-6. (4) Is recording 'more complete' in severe CRSS crashes? unknown share K vs non-K by
period, with design-based SE for the difference. (5) 'Cannot support severity/trend at all':
within the stable post-break window 2020-2024 compute drugs/distraction K vs non-K prevalence with
Manski worst-case bounds (unknown=no / unknown=yes) and among-known; also year-trend stability in window.
(6) FARS side: distracted & drug-test fields unknown share by year/status (FARS-only trends)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.survey import svy_mean
from nhtsa_stats.analysis.measurement import observed_severity
df, design = data.crss_crash(outcome=None)
sev = observed_severity(df.MAX_SEV); yr = df.YEAR.to_numpy()
def m(x, dom): r = svy_mean(design, x, dom); return 100*r.estimate, 100*r.se
for name, ys in [("2016-2018", (2016, 2018)), ("2020-2024", (2020, 2024))]:
    iny = (yr >= ys[0]) & (yr <= ys[1])
    print(f"\n== period {name}: unknown share, K vs 0-3 (diff K-nonK, pp)")
    for f in ["alcohol", "drugs", "distracted", "speeding"]:
        x = df[f].to_numpy(float); u = np.isnan(x).astype(float)
        k = m(u, iny & (sev == 4)); n = m(u, iny & np.isin(sev, [0, 1, 2, 3]))
        se = (k[1]**2 + n[1]**2)**.5
        print(f"{f:11s} K {k[0]:5.1f}  nonK {n[0]:5.1f}  diff {k[0]-n[0]:5.1f} (SE~{se:.1f}, indep approx)")
print("\n== (5) window 2020-2024: prevalence among known, and Manski bounds, K vs 0-3 and KA vs 0-2")
iny = (yr >= 2020) & (yr <= 2024)
for f in ["drugs", "distracted"]:
    x = df[f].to_numpy(float)
    for lab, a, b in [("K", sev == 4, np.isin(sev, [0, 1, 2, 3])), ("KA", np.isin(sev, [3, 4]), np.isin(sev, [0, 1, 2]))]:
        out = []
        for dom in (iny & a, iny & b):
            yk = m((x == 1).astype(float), dom & ~np.isnan(x))
            lo = m((x == 1).astype(float), dom); hi = m(((x == 1) | np.isnan(x)).astype(float), dom)
            out.append((yk, lo, hi))
        print(f"{f:10s} {lab:2s} known-yes {out[0][0][0]:5.2f} vs {out[1][0][0]:5.2f} | bounds sev [{out[0][1][0]:.2f},{out[0][2][0]:.2f}] vs non-sev [{out[1][1][0]:.2f},{out[1][2][0]:.2f}]")
print("\n== window trend: yes% among known by year, K vs 0-3 (2019-2024)")
for f in ["drugs", "distracted"]:
    x = df[f].to_numpy(float)
    for y in range(2018, 2025):
        d = yr == y
        r = [m((x == 1).astype(float), d & ~np.isnan(x) & s)[0] for s in (sev == 4, np.isin(sev, [0, 1, 2, 3]))]
        u = m(np.isnan(x).astype(float), d)[0]
        print(f, y, f"known-yes K {r[0]:5.2f} nonK {r[1]:5.2f} unknown(all) {u:5.1f}")
# FARS
per = data.fars_person(); dr = per[per.ptype == "driver"].copy()
dr["st"] = np.where(dr.killed == 1, "killed", np.where(dr.killed == 0, "survived", "unk"))
print("\n== (6) FARS drivers: distracted unknown%, pr_drugs unknown%, drug tested % (columns present?)")
print([c for c in dr.columns if "distr" in c or "drug" in c.lower()])
g = dr[dr.st.isin(["killed", "survived"])].groupby(["YEAR", "st"])
print(pd.DataFrame({"distr_unk": g.distracted.apply(lambda s: 100*s.isna().mean()),
                    "distr_yes": g.distracted.apply(lambda s: 100*(s == 1).mean()),
                    "prdrug_unk": g.pr_drugs.apply(lambda s: 100*s.isna().mean()),
                    "prdrug_yes": g.pr_drugs.apply(lambda s: 100*(s == 1).mean())}).round(1).unstack())
