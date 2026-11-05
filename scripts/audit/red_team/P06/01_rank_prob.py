"""P06 attack 1-3: is P(exceeded > alcohol) ~0.97 robust?
Reproduces rank_probabilities (published spec), then (a) compares joint-vcov vs independent-SE
probability, (b) re-fits with other adjustment sets (env only, +drugs, +config), (c) pools
exceeded+other speeding into 'any speeding' and ranks it against alcohol, (d) adds drugs as a
rankable factor in the same model. Look at: p_joint, p_indep, corr, diff/se per spec."""
import numpy as np, pandas as pd
from scipy.stats import norm
from nhtsa_stats.analysis import multifactor
from nhtsa_stats.analysis import contributions as C

df, design = multifactor.crash_frame()
print(df.shape, [c for c in ["exceeded","alcohol_im","drugs","crash_type","fatal"] if c in df])
print(df["exceeded"].value_counts(dropna=False).to_dict())
ENV, MIX, CFG = C.ENVIRONMENT, C.MIX, C.CONFIG
specs = {
 "env only": [*ENV, "exceeded", "alcohol_im"],
 "PUBLISHED env+mix": [*ENV, "exceeded", "alcohol_im", *MIX],
 "+drugs": [*ENV, "exceeded", "alcohol_im", *MIX, "drugs"],
 "+config": [*ENV, "exceeded", "alcohol_im", *MIX, "drugs", *CFG],
}
rows=[]
for name, covs in specs.items():
    m, cells, cd = C.fit_cells(df, design, covs, "fatal")
    names=["exceeded","speeding_other","alcohol"] + (["drugs_police"] if "drugs" in covs else [])
    ms = C.factor_margins(m, cells, names)
    fns=[C._log_rr(n) for n in names]
    est=np.array([f(ms.values) for f in fns])
    z=np.column_stack([C._contrast_influence(ms,f) for f in fns]); vc=cd.vcov_total(z)
    d=est[0]-est[2]; se_j=np.sqrt(vc[0,0]+vc[2,2]-2*vc[0,2]); se_i=np.sqrt(vc[0,0]+vc[2,2])
    corr=vc[0,2]/np.sqrt(vc[0,0]*vc[2,2])
    r=dict(spec=name,RR_exc=np.exp(est[0]),RR_alc=np.exp(est[2]),ratio=np.exp(d),corr=corr,
           se_joint=se_j,se_indep=se_i,p_joint=norm.cdf(d/se_j),p_indep=norm.cdf(d/se_i))
    if "drugs_police" in names:
        r["RR_drugs"]=np.exp(est[3])
        dd=est[0]-est[3]; sj=np.sqrt(vc[0,0]+vc[3,3]-2*vc[0,3]); r["p_exc_gt_drugs"]=norm.cdf(dd/sj)
        da=est[3]-est[2]; sa=np.sqrt(vc[3,3]+vc[2,2]-2*vc[3,2]); r["p_drugs_gt_alc"]=norm.cdf(da/sa)
    rows.append(r)
    if name.startswith("PUBLISHED"):
        # Monte Carlo replicate of published table
        rng=np.random.default_rng(C.SEED); dr=rng.multivariate_normal(est,vc,size=20000)
        print("MC P(exc rank1) published spec:", np.mean(dr[:,0]>np.maximum(dr[:,1],dr[:,2])))
print(pd.DataFrame(rows).round(4).T.to_string())

# any-speeding vs alcohol (pooled), published adjustment set
d2=df.copy(); d2["anysp"]=np.where(d2["exceeded"].astype(str)=="no","no","yes")
covs=[*ENV,"anysp","alcohol_im",*MIX]
d2["anysp"]=d2["anysp"].astype(object)
m,cells,cd=C.fit_cells(d2,design,covs,"fatal")
sc={}
for n,col,e,r_ in [("any","anysp","yes","no"),("alc","alcohol_im","yes","no")]:
    sc[f"{n}|1"]=lambda d,c=col,v=e: d.assign(**{c:v}); sc[f"{n}|0"]=lambda d,c=col,v=r_: d.assign(**{c:v})
ms=m.margins(cells,sc)
fns=[C._log_rr("any"),C._log_rr("alc")]; est=np.array([f(ms.values) for f in fns])
z=np.column_stack([C._contrast_influence(ms,f) for f in fns]); vc=cd.vcov_total(z)
d=est[0]-est[1]; se=np.sqrt(vc[0,0]+vc[1,1]-2*vc[0,1])
print("ANY SPEEDING RR",np.exp(est[0]),"ALC RR",np.exp(est[1]),"P(any>alc)",norm.cdf(d/se),"z",d/se)
print("prevalence any speeding / exceeded (unweighted):",(d2.anysp=="yes").mean(),(d2.exceeded.astype(str)=="yes").mean())
