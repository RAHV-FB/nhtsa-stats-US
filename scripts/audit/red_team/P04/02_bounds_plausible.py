"""P04 claim: CRSS crude fatal RR for police-reported drugs ranges 1.7-73 (2019-2024) depending
on allocation of the 54% unknown.  Test: (a) which grid cells give the extremes (corner
differential cases); (b) the range under non-differential and monotone (k_fatal>=k_nonfatal)
allocations; (c) FARS-calibrated k: tox positivity among police-unknown vs police-known drivers
(proxy for how prevalent drugs are in 'unknown'); (d) unknown share by year in CRSS."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import drugs as D, data
b=pd.read_csv("outputs/tables/drugs/crss_bounds.csv")
for per in ("2016-2018","2019-2024","2016-2024"):
    k=b[(b.period==per)&(b.scenario=="k scenario")]
    print(per,"all grid: min %.2f max %.2f"%(k.rr.min(),k.rr.max()),
      "| nondiff (kf=kn): %.2f-%.2f"%(k[k.k_fatal==k.k_nonfatal].rr.min(),k[k.k_fatal==k.k_nonfatal].rr.max()),
      "| monotone kf>=kn: %.2f-%.2f"%(k[k.k_fatal>=k.k_nonfatal].rr.min(),k[k.k_fatal>=k.k_nonfatal].rr.max()),
      "| kf,kn in [0,1] nondiff-or-mild(|diff|<=0.5): %.2f-%.2f"%(
        k[(abs(k.k_fatal-k.k_nonfatal)<=0.5)&(k.k_fatal<=1)].rr.min(),k[(abs(k.k_fatal-k.k_nonfatal)<=0.5)&(k.k_fatal<=1)].rr.max()),
      "| allneg/allpos:",b[(b.period==per)&(b.scenario=="all unknown negative")].rr.round(2).tolist(),b[(b.period==per)&(b.scenario=="all unknown positive")].rr.round(2).tolist())
    print("   argmin",k.loc[k.rr.idxmin(),["k_fatal","k_nonfatal"]].tolist(),"argmax",k.loc[k.rr.idxmax(),["k_fatal","k_nonfatal"]].tolist())
# (d) CRSS unknown share and complete-case RR by year, and by alcohol known
df,design=data.crss_crash(outcome="fatal"); w=design.weight; y=df.fatal.to_numpy(float); x=df.drugs.to_numpy(float)
for yr in range(2016,2025):
    s=(df.YEAR==yr).to_numpy(); kn=s&~np.isnan(x)
    a=w[kn&(x==1)&(y==1)].sum();bb=w[kn&(x==1)&(y==0)].sum();c=w[kn&(x==0)&(y==1)].sum();dd=w[kn&(x==0)&(y==0)].sum()
    print(yr,"unknown share %.2f"%(w[s&np.isnan(x)].sum()/w[s].sum()),"cc RR %.1f"%((a/(a+bb))/(c/(c+dd))),"P(drug|known) fatal %.3f nonfatal %.3f"%(a/(a+c),bb/(bb+dd)))
# (c) FARS calibration
f=D.load_fars_drivers(); f=f[(f.survival!="unknown")&(f.drug_tested==1)&f.drv_drug_any.notna()]
for s in ("killed","survived"):
    g=f[f.survival==s]
    print(s,"tox-pos: police yes %.3f no %.3f unknown %.3f | n"%tuple(g[g.drv_pr_drugs.isna() if v=='u' else g.drv_pr_drugs==v].drv_drug_any.mean() for v in (1,0,'u')),
          [int(len(g[g.drv_pr_drugs.isna() if v=='u' else g.drv_pr_drugs==v])) for v in (1,0,'u')])
