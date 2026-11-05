"""P03 attack: are the unit RRs (2.7/4.3/3.6/4.7/1.22) comparable?  Re-fit alcohol-only RR of each
unit under (A) published spec, (B) one common spec: YEAR+ENV+age+sex only (no belt, no other
driver's behaviour, no vehicle mix), (C) YEAR only; plus crash-level RR stratified by crash type.
Look at RR column across units within a spec."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import multifactor as mf, factorial
from nhtsa_stats.analysis.factorial import Factor
frames = mf.load_frames()
print("PERSON_COVS", mf.PERSON_COVS)
res=[]
def go(unit, spec, df, design, sa, sl, covs, outc, mask):
    sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
    f=[Factor("s",sa,("yes",),("no",)),Factor("a",sl,("yes",),("no",))]
    covs=[c for c in covs if c not in (sa,sl)]
    r=factorial.fit_factorial(sub,sd,f,covs,outc); m=factorial.margins_table(r).set_index("key").loc["01"]
    res.append((unit,spec,m.rr_vs_none,m.rr_vs_none_low,m.rr_vs_none_high,m.rd_vs_none*100,r.n_events)); print(res[-1],flush=True)
for v in mf.VICTIMS:
    df,d=frames[v.frame]; mask=v.select(df); s,a=v.behaviour_cols
    name=v.name.split(" (")[0]
    agesex = ["age_band","sex"] if v.frame!="driver" else mf.PERSON_COVS
    go(name,"A published",df,d,s,a,v.covariates,v.outcome,mask)
    go(name,"B ENV+age/sex",df,d,s,a,[*mf.ENV,*agesex] if v.frame!="crash" else mf.ENV,v.outcome,mask)
    go(name,"C YEAR only",df,d,s,a,["YEAR"],v.outcome,mask)
# crash level by crash type
df,d=frames["crash"]
print(df.crash_type.value_counts().to_dict())
print(df.groupby("crash_type").apply(lambda g: pd.Series({"n":len(g),"fatal":g.fatal.sum()})).T)
for ct in ["pedestrian","single_vehicle","two_vehicle"]:
    pass
cts = df.crash_type.value_counts().index[:8]
for ct in cts:
    mask=(df.crash_type==ct).to_numpy()
    try: go("crash|"+ct,"A (ENV+MIX)",df,d,"speeding","alcohol_im",[*mf.ENV,*mf.MIX],"fatal",mask)
    except Exception as e: print(ct,"fail",e)
pd.DataFrame(res,columns=["unit","spec","RR","lo","hi","RD_pp","events"]).to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/P03/03.csv",index=False)
