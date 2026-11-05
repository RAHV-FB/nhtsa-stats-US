"""P07 attack: is the 'unsupported' verdict an artefact of the n>=30 & deaths>=10 rule?
For every one of the 96 grid cells compute CRSS n, deaths, model risk SE (log scale) and
design effect proxies. Compare the precision of published-'supported' vs 'unsupported' cells,
and show what the worked case's single-vehicle contrast would be (RR, CI) and how many cells/
contrasts flip under looser thresholds. Look at: se_logRR by deaths; flips table."""
import sys; sys.path.insert(0, "scripts/audit/red_team/P07")
from common import *
df, design = cases.case_frame()
m, cells, cd, _ = fit_alt(df, design, cases.GRID, "all")
sc = cases.grid(cases.GRID)
ms = m.margins(cells, scen_funcs(cases.GRID, sc))
sup = cases.support(df, design, cases.GRID, sc, m.predict(df))
t = cd.tcrit(); kr = cases.scenario_key(REF)
rows = []
for s in sc:
    k = cases.scenario_key(s); e = ms.estimate(k); r = ms.log_ratio(k, kr)
    rows.append(dict(key=k, n=sup[k]["crss_n"], d=sup[k]["crss_deaths"], supported=sup[k]["supported"],
                     risk=e.estimate, se_logit=e.se/(e.estimate*(1-e.estimate)), se_logrr=r.se,
                     rr=np.exp(r.estimate)))
R = pd.DataFrame(rows); R.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/P07/grid.csv", index=False)
R["dbin"] = pd.cut(R.d, [-1, 0, 4, 9, 14, 29, 59, 1e9])
print(R.groupby("dbin", observed=True).agg(cells=("key", "size"), sup=("supported", "sum"),
      med_se_logrr=("se_logrr", "median"), max_se=("se_logrr", "max")).to_string())
print("\ncells with 5<=deaths<=9 or n<30 but deaths>=5:")
print(R[(~R.supported) & (R.d >= 5)].sort_values("d")[["key","n","d","risk","se_logrr","rr"]].to_string())
print("\nsupported cells with 10-14 deaths (precision comparison):")
print(R[R.supported & (R.d < 15)][["key","n","d","risk","se_logrr","rr"]].to_string())
for ne, nn in [(10,30),(8,30),(5,30),(5,20)]:
    ok = (R.n >= nn) & (R.d >= ne)
    print(f"threshold deaths>={ne}, n>={nn}: supported cells {int(ok.sum())} / {len(R)}")
# worked case contrasts under looser rule
k = cases.scenario_key(CASE)
for n in CASE:
    kw = cases.scenario_key(dict(CASE, **{n: REF[n]}))
    r = ms.log_ratio(k, kw)
    w = R[R.key == kw].iloc[0]
    print(n, f"RR {np.exp(r.estimate):.2f} ({np.exp(r.estimate-t*r.se):.2f}-{np.exp(r.estimate+t*r.se):.2f}) comparator cell n={w.n} deaths={w.d} published_supported={w.supported}")
