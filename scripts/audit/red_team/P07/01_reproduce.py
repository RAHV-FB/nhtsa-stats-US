"""P07 reproduction: worked case n/deaths, observed rate, mean prediction, standardised risk,
RR vs reference, one-factor-removed RRs. Compare with outputs/tables/cases/*. Also PSU counts."""
import sys; sys.path.insert(0, "scripts/audit/red_team/P07")
from common import *
df, design = cases.case_frame()
print("frame n", len(df), "deaths", int(df.drv_killed.sum()))
m, cells, cd, prods = fit_alt(df, design, cases.GRID, "all")
print("n product terms", len(prods))
sc = [CASE] + [dict(CASE, **{n: REF[n]}) for n in CASE] + [REF]
ms = m.margins(cells, scen_funcs(cases.GRID, sc))
t = cd.tcrit()
k = cases.scenario_key(CASE); kr = cases.scenario_key(REF)
e = ms.estimate(k); print("case std risk", e.estimate, logit_ci(e.estimate, e.se, e.df))
rr = ms.log_ratio(k, kr); print("RR vs ref", np.exp(rr.estimate), np.exp(rr.estimate - t*rr.se), np.exp(rr.estimate + t*rr.se))
for n in CASE:
    kw = cases.scenario_key(dict(CASE, **{n: REF[n]}))
    r = ms.log_ratio(k, kw)
    print(n, "risk without", ms.estimate(kw).estimate, "RR", np.exp(r.estimate), np.exp(r.estimate - t*r.se), np.exp(r.estimate + t*r.se))
sup = cases.support(df, design, cases.GRID, [CASE], m.predict(df))
print(sup)
# PSU structure of worked case and alcohol-removed cell
mask = np.ones(len(df), bool)
for n, v in CASE.items(): mask &= (df[cases.GRID[n][0]].astype(str) == v).to_numpy()
print("worked case: PSUs", len(set(design.cluster[mask])), "strata", len(set(design.stratum[mask])),
      "weight sum", design.weight[mask].sum(), "max wt share", design.weight[mask].max()/design.weight[mask].sum(),
      "deaths by year", df.loc[mask].groupby("YEAR").drv_killed.agg(["size","sum"]).to_dict())
