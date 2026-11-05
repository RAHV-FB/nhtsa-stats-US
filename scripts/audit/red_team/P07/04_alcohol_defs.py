"""P07 attack: alcohol definition and context. (a) imputed (NHTSA V_ALCH_IM) vs police-reported
alcohol in the same saturated model; crosstab with death rate. (b) coarsen the context: drop
night and/or single-vehicle from the grid -> alcohol RR for 'exceeded+alcohol+unbelted' (c) pool
speeding (any speeding vs none). Look at RR_alcohol and CI vs the published 1.41 (0.84-2.35)."""
import sys; sys.path.insert(0, "scripts/audit/red_team/P07")
from common import *
df, design = cases.case_frame()
print(pd.crosstab(df.own_alcohol_im, df.own_alcohol_police, margins=True))
y = df.drv_killed.to_numpy(); w = design.weight
for a in ["own_alcohol_im", "own_alcohol_police"]:
    for v in df[a].unique():
        mk = (df[a] == v).to_numpy(); print(a, v, "n", int(mk.sum()), "deaths", int(y[mk].sum()), "wtd rate", round(float((w[mk]*y[mk]).sum()/w[mk].sum()),4))

def run(label, factors, case, drop_cols=()):
    covs = [c for c in cases.COVARIATES if c not in drop_cols]
    m, cells, cd, _ = fit_alt(df, design, factors, "all", covs=covs)
    k = cases.scenario_key(case); kw = cases.scenario_key(dict(case, alcohol="no"))
    ms = m.margins(cells, scen_funcs(factors, [case, dict(case, alcohol="no")]))
    t = cd.tcrit(); r = ms.log_ratio(k, kw)
    mk = np.ones(len(df), bool)
    for n, v in case.items(): mk &= (df[factors[n][0]].astype(str) == v).to_numpy()
    mw = np.ones(len(df), bool)
    for n, v in dict(case, alcohol="no").items(): mw &= (df[factors[n][0]].astype(str) == v).to_numpy()
    print(f"{label}: case n={int(mk.sum())} d={int(y[mk].sum())}; comparator n={int(mw.sum())} d={int(y[mw].sum())}; RR_alcohol {np.exp(r.estimate):.2f} ({np.exp(r.estimate-t*r.se):.2f}-{np.exp(r.estimate+t*r.se):.2f})")

G = cases.GRID
run("project (imputed alcohol), 5 factors", G, CASE)
G2 = dict(G, alcohol=("own_alcohol_police", ["no", "yes"]))
run("police-reported alcohol, 5 factors", G2, CASE)
# coarser contexts (imputed alcohol)
G3 = {k: v for k, v in G.items() if k != "single_vehicle"}
run("drop single_vehicle (4 factors)", G3, {k: v for k, v in CASE.items() if k != "single_vehicle"}, ("n_vehicles",))
G4 = {k: v for k, v in G.items() if k not in ("single_vehicle", "night")}
run("exceeded+alcohol+unbelted only (3 factors)", G4, {k: v for k, v in CASE.items() if k in G4})
# pooled speeding: any speeding
df["any_speeding"] = df.case_speeding.map({"none": "none", "exceeded_limit": "speeding", "other_speeding": "speeding"}).fillna("unknown")
G5 = dict(G, speeding=("any_speeding", ["none", "speeding"]))
run("any speeding (pooled) + alcohol + unbelted + night + single", G5, dict(CASE, speeding="speeding"))
