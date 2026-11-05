"""F07 part 4: combined two-sided misreporting from committed double_pair_counts.csv (belt_driver_rf rows).
Survivors coded belted truly unbelted (f) AND unbelted-coded deaths truly belted (h) AND belted-coded deaths truly unbelted (g)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import matched as m
t=pd.read_csv("outputs/tables/matched/double_pair_counts.csv"); t=t[t.analysis=="belt_driver_rf"]
# build cell table [xd,kd,xp,kp] from vehicles/driver_deaths/other_deaths/both_died
c=np.zeros((2,2,2,2))
for _,r in t.iterrows():
    xd,xp=int(r.driver_x),int(r.other_x); v,dd,od,b=r.vehicles,r.driver_deaths,r.other_deaths,r.both_died
    c[xd,1,xp,1]=b; c[xd,1,xp,0]=dd-b; c[xd,0,xp,1]=od-b; c[xd,0,xp,0]=v-(dd+od-b)
red=lambda c:1-float(np.exp(m.dpc_combined(c)))
print("base",round(red(c),4))
def mix(c,f,g,h):
    o=np.array(c,float)
    for sl in ("d","p"):
        for k,rate in ((0,f),(1,g)):  # belted-coded survivors / deaths truly unbelted
            if sl=="d": mv=rate*o[1,k,:,:]; o[1,k,:,:]-=mv; o[0,k,:,:]+=mv
            else: mv=rate*o[:,:,1,k]; o[:,:,1,k]-=mv; o[:,:,0,k]+=mv
        # unbelted-coded deaths truly belted (h)
        if sl=="d": mv=h*o[0,1,:,:]; o[0,1,:,:]-=mv; o[1,1,:,:]+=mv
        else: mv=h*o[:,:,0,1]; o[:,:,0,1]-=mv; o[:,:,1,1]+=mv
    return o
for f,g,h in [(.1,0,0),(.1,0,.03),(.1,0,.05),(.1,.03,.05),(.2,0,.05),(.05,0,.05),(.15,0,.05),(0,0,.1)]:
    print(f"f={f} g={g} h={h}: reduction {red(mix(c,f,g,h)):.3f}")
