"""F05 attack (functional form / population at risk): replace the single-logistic-plus-one-product
-term model by fully stratified models (every covariate effect free to differ by stratum) and
standardise within each stratum's own crashes. For stratifier S in {pedestrian crash, speeding}:
RR and RD of unlit darkness vs daylight in S=1 and S=0, ratio of RRs and difference of RDs.
Strata share PSUs, so the covariance is ignored (independent-models approximation: SE slightly
off, point estimates exact).  Compare ratio/diff with published 1.62 / 93.6 (ped) and 0.94 /1.8 (speeding)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis.survey import SurveyDesign

def strat(df, outcome, mask, covs):
    sub = df[mask].copy()
    d = SurveyDesign.from_frame(sub)
    sub = sub[sub.light.isin(["daylight","dark_not_lighted"])].copy()  # fit on the two levels only? keep all, setter below
    return sub
def run(outcome, name, maskfun, covs_drop):
    df, design = severity.load(outcome)
    res = {}
    for s in (1, 0):
        m = maskfun(df) == s
        sub = df[m].copy(); d = SurveyDesign.from_frame(sub)
        covs = [c for c in (specs.PRE_CRASH + (specs.CIRCUMSTANCE if name=="ped" else [])) if c not in covs_drop[s]]
        mod = severity.fit(sub, d, outcome, covs)
        ft = severity.factor_contrasts(mod, sub, "light", ["daylight","dark_not_lighted"])
        r = ft[ft.level=="dark_not_lighted"].iloc[0]; b = ft[ft.level=="daylight"].iloc[0]
        res[s] = dict(n=len(sub), events=int(sub[outcome].sum()), base=b.adj_rate, unlit=r.adj_rate, rr=r.adj_rr, rr_lo=r.adj_rr_low, rr_hi=r.adj_rr_high, rd=r.adj_rd)
        print(outcome, name, "S=%d"%s, {k:(round(v,4) if isinstance(v,float) else v) for k,v in res[s].items()}, flush=True)
    print(f"==> {outcome} {name}: ratio of RRs (S1/S0) = {res[1]['rr']/res[0]['rr']:.3f};  diff of RDs per 1000 = {1000*(res[1]['rd']-res[0]['rd']):.1f}")
ped = lambda d: (d.crash_type=="pedestrian").astype(int).to_numpy()
spd = lambda d: (d.speeding=="yes").astype(int).to_numpy()
run("fatal","ped",ped,{1:["crash_type","n_vehicles"],0:[]})
run("fatal","speeding",spd,{1:["speeding"],0:["speeding"]})
run("ka","speeding",spd,{1:["speeding"],0:["speeding"]})
