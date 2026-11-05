"""P06 attacks 4-5 (tables only, no data): (a) reproduce 47% configuration share from
predictive_lattice; (b) Shapley share under other block groupings (behaviour merged, config split not
possible), removed-last and alone shares, order-sensitivity range; (c) simple QBA: ratio exceeded/alcohol
adjusted RR under differential recording of exceedance in non-fatal crashes (sensitivity s)."""
import itertools, math, numpy as np, pandas as pd
L=pd.read_csv("outputs/tables/contributions/predictive_lattice.csv")
v={frozenset([] if b=="intercept" else b.split("+")):r for b,r in zip(L.blocks,L.test_r2)}
B=["speeding_type","alcohol","drugs_police","environment","driver_vehicle_mix","configuration"]
full=frozenset(B); print("full R2",v[full])
def shap(players, val):
    n=len(players); out={}
    for j in players:
        o=[p for p in players if p!=j]; t=0
        for r in range(n):
            w=math.factorial(r)*math.factorial(n-r-1)/math.factorial(n)
            for s in itertools.combinations(o,r):
                s0=frozenset(x for p in s for x in p[1]) if False else None
        out[j]=None
    return out
# generic shapley over groups (each group = tuple of blocks)
def shapley_groups(groups):
    n=len(groups); res={}
    for gi,g in enumerate(groups):
        others=[h for k,h in enumerate(groups) if k!=gi]; t=0
        for r in range(n):
            w=math.factorial(r)*math.factorial(n-r-1)/math.factorial(n)
            for s in itertools.combinations(others,r):
                s0=frozenset(b for h in s for b in h); t+=w*(v[s0|frozenset(g)]-v[s0])
        res[g]=t
    return res
fr=v[full]
print("\n6 blocks (published):"); 
for g,x in shapley_groups([(b,) for b in B]).items(): print(f"  {g[0]:20s} {x/fr:6.1%}")
print("\nbehaviour merged (speed+alc+drugs):")
for g,x in shapley_groups([("speeding_type","alcohol","drugs_police"),("environment",),("driver_vehicle_mix",),("configuration",)]).items(): print("  ",g,f"{x/fr:6.1%}")
print("\nbehaviour merged excl. drugs (speed+alc):")
vv=v
for g,x in shapley_groups([("speeding_type","alcohol"),("drugs_police",),("environment",),("driver_vehicle_mix",),("configuration",)]).items(): print("  ",g,f"{x/fr:6.1%}")
print("\nconfig share by ordering: min/max of marginal gain of configuration over all subsets of others")
oth=[b for b in B if b!="configuration"]; g=[]
for r in range(6):
    for s in itertools.combinations(oth,r):
        s0=frozenset(s); g.append((v[s0|{'configuration'}]-v[s0], s0))
gm=[x for x,_ in g]; print(" marginal gain range %.4f..%.4f ; as share of full: %.1f%%..%.1f%%"%(min(gm),max(gm),100*min(gm)/fr,100*max(gm)/fr))
for b in ["alcohol","speeding_type"]:
    o=[x for x in B if x!=b]; gg=[v[frozenset(s)|{b}]-v[frozenset(s)] for r in range(6) for s in itertools.combinations(o,r)]
    print(f" {b}: marginal gain range {min(gg)/fr:.1%}..{max(gg)/fr:.1%}")
# per-ordering: share if only environment+configuration+mix considered ('non-behaviour')
print("\nbehaviour (3 blocks, Shapley merged) share:", [x/fr for g_,x in shapley_groups([("speeding_type","alcohol","drugs_police"),("environment",),("driver_vehicle_mix",),("configuration",)]).items()][0])
# QBA
print("\nQBA: published adjusted RR exceeded 5.197, alcohol 4.112 (ratio 1.264)")
for s in [1,0.9,0.8,0.79,0.7,0.5]:
    print(f" non-fatal exceedance recorded at {s:.2f} of fatal-crash completeness -> approx RR {5.1972*s:.2f} (rare-exposure approx), ratio to alcohol {5.1972*s/4.1122:.2f}")
print(" breakeven s =",4.1122/5.1972)
# exact crude version: prevalence all .00851769, fatal .0732252, crude RR 10.0301
pa,pf,rr=0.00851769,0.0732252,10.0301
# fatal share of crashes q from RR identity: pf = q? derive q: P(fatal)=q; pa=q*pf+(1-q)*pn
# solve pn from RR=(pf/pa-weighted)...: P(exp|fatal)=pf; P(exp|nonfatal)=pn; RR=pf/(q pf+(1-q)pn)/ ... use RR=[pf/pn]*[(1-pn)/(1-pf)]approx? do numeric
from scipy.optimize import brentq
q_f=lambda q:(q*pf)/(q*pf+(1-q)*((pa-q*pf)/(1-q)))
q=brentq(lambda q: (pf/(pa))*q - 0.0, 1e-9,0.5) if False else None
