"""P07 attack: does the worked-case reading (alcohol RR 1.41, 'not distinguishable') and the
non-additivity story depend on the saturated spec? Fits: product order (all / pairs / main) x
covariates (project / none). Prints case risk, alcohol-removed RR+CI, RD, all one-factor RRs.
Also design Wald tests for >=3-way and for all product terms (is the saturation needed?)."""
import sys; sys.path.insert(0, "scripts/audit/red_team/P07")
from common import *
df, design = cases.case_frame()
print("alcohol levels (rows):", df.own_alcohol_im.value_counts().to_dict())
print("case-frame levels speeding:", df.case_speeding.value_counts().to_dict())
k = cases.scenario_key(CASE)
sc = [CASE] + [dict(CASE, **{n: REF[n]}) for n in CASE]
fn = scen_funcs(cases.GRID, sc)
out = []
for covname, covs in [("project covs", None), ("no covs", [])]:
    for prod in ["all", "pairs", "main"]:
        m, cells, cd, prods = fit_alt(df, design, cases.GRID, prod, covs=covs)
        ms = m.margins(cells, fn); t = cd.tcrit()
        e = ms.estimate(k); row = dict(spec=f"{prod} / {covname}", risk=e.estimate)
        for n in CASE:
            kw = cases.scenario_key(dict(CASE, **{n: REF[n]}))
            r = ms.log_ratio(k, kw)
            row[f"RR_{n}"] = f"{np.exp(r.estimate):.2f} ({np.exp(r.estimate-t*r.se):.2f}-{np.exp(r.estimate+t*r.se):.2f})"
            if n == "alcohol":
                d = ms.difference(k, kw); row["RD_alc_pp"] = f"{100*d.estimate:.1f} ({100*(d.estimate-t*d.se):.1f}..{100*(d.estimate+t*d.se):.1f})"
        out.append(row)
        if prod == "all" and covs is None:
            lay = m.spec.layout(); names = m.names_
            def nm(i): return names[i[2]]
            hi = [nm(l) for l in lay if l[0].startswith("product") and len(l[1]) >= 3]
            p2 = [nm(l) for l in lay if l[0].startswith("product") and len(l[1]) == 2]
            allp = [nm(l) for l in lay if l[0].startswith("product")]
            for lab, tt in [("3+-way products", hi), ("2-way products", p2), ("all products", allp)]:
                w = m.wald_test(tt); print(f"Wald {lab}: q={w['q']} F={w['F']:.2f} p={w['p']:.4f}")
        if prod == "pairs" and covs is None:
            lay = m.spec.layout(); names = m.names_
            allp = [names[l[2]] for l in lay if l[0].startswith("product")]
            w = m.wald_test(allp); print(f"[pairs model] Wald 2-way products: q={w['q']} F={w['F']:.2f} p={w['p']:.4f}")
print(pd.DataFrame(out).to_string())
