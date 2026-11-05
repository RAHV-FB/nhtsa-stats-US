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
              rr=r.loc[lvl,"adj_rr"] if "adj_rr" in r else r.loc[lvl].iloc[0],
              lo=r.loc[lvl,"adj_rr_low"] if "adj_rr_low" in r else np.nan, hi=r.loc[lvl,"adj_rr_high"] if "adj_rr_high" in r else np.nan))
    print(rows[-1], flush=True)
import inspect
# probe columns of contrasts once
m = P.fit_model(lpv,"killed",base); lean=lpv.df[[*dict.fromkeys(base),"killed"]]
con = P.factor_contrasts(m, lean,"veh_age_band",P.levels_for(lpv,"veh_age_band")); print(con.columns.tolist())
