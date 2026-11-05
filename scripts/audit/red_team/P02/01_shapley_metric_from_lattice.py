"""P02 attack 1: is 'alcohol accounts for 9% of the crude log-RR' a robust accounting?
Reads the committed lattice (outputs/tables/speeding/lattice.csv, 2^7 standardised fits, no data load).
Recomputes the Shapley share (a) as published (7 players, log RR), (b) with the five
environment blocks merged into one player (3-5 players), (c) on the risk-difference scale
and the RR scale, (d) alcohol vs each single ordering. Look at how much alcohol's share moves with the
partition of blocks and with the metric. Also reproduces crude 10.03 and all-blocks 4.88."""
import itertools, math
import pandas as pd
l = pd.read_csv('outputs/tables/speeding/lattice.csv')
x = l[(l.exposure=='exceeded')&(l.outcome=='fatal')].copy()
x['key']=x.blocks.apply(lambda s: frozenset() if s=='crude' else frozenset(s.split('+')))
x['rd']=x.adj_rate_exposed-x.adj_rate_reference
x['rr_']=x.adj_rate_exposed/x.adj_rate_reference
x['lrr']=x.log_rr
v={'log':dict(zip(x.key,x.lrr)),'rd':dict(zip(x.key,x.rd)),'rr':dict(zip(x.key,x.rr_))}
ALL=frozenset(['calendar_area','time','light','road_environment','driver_vehicle_mix','alcohol','configuration'])
print('crude RR',x[x.key==frozenset()].rr.iloc[0],'all',x[x.key==ALL].rr.iloc[0])
def shap(groups,metric,target):
    names=list(groups); n=len(names); f=v[metric]
    def val(S): return f[frozenset().union(*[groups[g] for g in S])] if S else f[frozenset()]
    tot=0
    for k in range(n):
        for S in itertools.combinations([g for g in names if g!=target],k):
            w=math.factorial(k)*math.factorial(n-k-1)/math.factorial(n)
            tot+=w*(val(S+(target,))-val(S))
    crude=f[frozenset()]; full=f[ALL]
    # share of the crude-to-full reduction and of the crude metric (metric measured from null: log RR 0, RD 0, RR 1)
    null=1.0 if metric=='rr' else 0.0
    return tot/(crude-null), -tot/(crude-full)   # (share of crude excess, share of total reduction crude->all)
env=['calendar_area','time','light','road_environment']
parts={'published 7 players':{b:frozenset([b]) for b in ALL},
 'env4 merged (4 players: env,dvm,alc,cfg)':{'env':frozenset(env),'driver_vehicle_mix':frozenset(['driver_vehicle_mix']),'alcohol':frozenset(['alcohol']),'configuration':frozenset(['configuration'])},
 '3 players: alc, cfg, everything else':{'rest':frozenset(env+['driver_vehicle_mix']),'alcohol':frozenset(['alcohol']),'configuration':frozenset(['configuration'])},
 '2 players: alc vs everything else':{'rest':frozenset(env+['driver_vehicle_mix','configuration']),'alcohol':frozenset(['alcohol'])},
 '7 blocks, env split finer? (n/a)':None}
for name,g in parts.items():
    if g is None: continue
    for m in ['log','rd','rr']:
        a,b=shap(g,m,'alcohol'); print(f'{name:45s} {m:4s} alcohol: share of crude excess {-a:6.3f}  share of crude->full reduction {b:6.3f}')
# alcohol's share also expressed against the 'removable' part
