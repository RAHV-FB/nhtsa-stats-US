"""P06 attack 6: do the predictive shares (config 47%, env 20%, alcohol 8%, speeding 6%) depend on the
train/test years? Re-fits a 5-block lattice (speeding_type, alcohol, environment, mix, configuration;
drugs dropped for time -> 32 fits) with the project's own fit_cells/predict on SPLIT given by env var
P06_SPLIT in {pub, early, mid}. Compare Shapley shares of full test R2 with the published ones
(published 6-block: config 46.6, env 20.3, mix 15.1, alcohol 7.5, speeding 6.0, drugs 4.3)."""
import itertools, math, os, numpy as np
from nhtsa_stats.analysis import multifactor
from nhtsa_stats.analysis import contributions as C
S=os.environ.get("P06_SPLIT","pub")
tr_y,te_y={"pub":((2016,2017,2018,2019,2020,2021),(2023,2024)),
           "early":((2019,2020,2021,2022,2023,2024),(2016,2017)),
           "mid":((2016,2017,2018,2022,2023,2024),(2019,2020,2021))}[S]
df,design=multifactor.crash_frame()
yr=df["YEAR"].astype(int).to_numpy(); tr=np.isin(yr,tr_y); te=np.isin(yr,te_y)
print(S,"train",tr.sum(),"test",te.sum())
dtr,dte=df.loc[tr].reset_index(drop=True),df.loc[te].reset_index(drop=True)
sd=design.subset(tr); y=dte["fatal"].to_numpy(float); w=design.weight[te]
p0=float(np.average(dtr["fatal"],weights=sd.weight))
P={k:v for k,v in C.PRED_BLOCKS.items() if k!="drugs_police"}
if "environment" in P and S!="pub": pass
B=list(P); val={}
for r in range(len(B)+1):
    for s in itertools.combinations(B,r):
        covs=[c for b in s for c in P[b]]
        if not covs: val[frozenset()]=0.0; continue
        m,_,_=C.fit_cells(dtr,sd,covs,"fatal"); p=m.predict(dte)
        val[frozenset(s)]=C._r2(y,p,w,p0)
full=frozenset(B); n=len(B); fr=val[full]; print("full R2",round(fr,4))
for j in B:
    o=[b for b in B if b!=j]; t=0
    for r in range(n):
        wg=math.factorial(r)*math.factorial(n-r-1)/math.factorial(n)
        for s in itertools.combinations(o,r): t+=wg*(val[frozenset(s)|{j}]-val[frozenset(s)])
    print(f"{j:20s} alone {val[frozenset([j])]:.4f}  removed-last {fr-val[full-{j}]:.4f}  shapley share {t/fr:6.1%}")
