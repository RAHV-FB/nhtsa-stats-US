"""W07 claim: adjusted RR of death 18+ vs 0-3 yr vehicles = 2.22 (A) / 1.76 (B).
Reproduces A and B with the project's own functions, then re-fits under alternative
populations/adjustment sets (drivers only, belted only, period split, single/multi vehicle,
fewer/more covariates, K-or-A outcome). Look at the RR_18 column vs reference 2.22/1.76."""
import numpy as np, pandas as pd, sys
from nhtsa_stats.analysis import person as P, specs
OUT="/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W07/"
df, design = P.load_occupants("killed")
pops = P.build_populations(df, design); del df
lpv = pops["lpv"]
print("n",len(lpv.df),"events",int(lpv.df.killed.sum()))
base = [*lpv.person_covariates, *lpv.crash_covariates]
rows=[]
def run(name, pop, covs, outcome="killed"):
    covs=[c for c in covs]
    m = P.fit_model(pop, outcome, covs)
    lean = pop.df[[*dict.fromkeys(covs), outcome]]
    lv = P.levels_for(pop,"veh_age_band")
    # drop levels absent
    present=[l for l in lv if (pop.df.veh_age_band==l).any()]
    con = P.factor_contrasts(m, lean, "veh_age_band", present)
    r = con.set_index("level")
    for lvl in ["4-7","8-12","13-17","18+"]:
        if lvl in r.index:
            rows.append(dict(variant=name,outcome=outcome,level=lvl,n=len(pop.df),events=int(pop.df[outcome].sum()),
              rr=r.loc[lvl,'adj_rr'],
              lo=r.loc[lvl,'adj_rr_low'], hi=r.loc[lvl,'adj_rr_high']))
    print(rows[-1], flush=True)

D=lpv.df
CIRC=list(specs.CIRCUMSTANCE)
drop=lambda *x:[c for c in base if c not in x]
run("A_published", lpv, base)
run("B_published", lpv, base+CIRC)
# fewer / different adjustment
run("A_minus_speeding_alcohol", lpv, drop("speeding","alcohol_im"))
run("person_only+YEAR", lpv, ["age_band","sex","role","restraint","body","veh_age_band","YEAR"])
run("A_minus_other_vehicle_body", lpv, drop("other_vehicle_body"))
# sub-populations
def sub(mask,n): return lpv.subset(np.asarray(mask),n,n)
run("drivers_only", sub(D.role=="driver","drv"), drop("role"))
run("belted_only", sub(D.restraint=="belted","belted"), drop("restraint"))
run("belted_drivers_age25-64", sub((D.restraint=="belted")&(D.role=="driver")&D.age_band.isin(["25-34","35-44","45-54","55-64"]),"bd"), drop("restraint","role"))
for nm,msk in [("2016-2019",D.YEAR<=2019),("2020-2024",D.YEAR>=2020),("2016-2019_B",D.YEAR<=2019),("2020-2024_B",D.YEAR>=2020)]:
    run("period_"+nm, sub(msk,nm), drop("YEAR")+(CIRC if nm.endswith("_B") else []))
run("single_vehicle_only", sub(D.n_vehicles.astype(str).isin(["1"]) ,"sv"), drop("other_vehicle_body","any_motorcycle","any_heavy_truck")+[])
run("urban_only", sub(D.urbanicity.astype(str)=="urban","urb"), drop("urbanicity"))
run("rural_only", sub(D.urbanicity.astype(str)=="rural","rur"), drop("urbanicity"))
run("A_K_or_A_outcome(not run here)", lpv, base) if False else None
pd.DataFrame(rows).to_csv(OUT+"01_variants.csv",index=False)
print(pd.DataFrame(rows).query("level=='18+'").round(3).to_string())
print(D.n_vehicles.astype(str).value_counts().head(), D.urbanicity.astype(str).value_counts())
