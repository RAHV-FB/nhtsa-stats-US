"""P03: (1) which covariates move the driver-killed alcohol RR from 6.2 (common spec) to the
published 2.7 (belt? other driver's behaviour?), and the passenger analogue; (2) is the
crash-level sub-multiplicativity (exceeded x alcohol) present in single-vehicle crashes when the
crash-level estimand/covariates are used, and in multi-vehicle crashes? (3) same-driver
exceeded x alcohol RRR in multi-vehicle crashes (own behaviour, other driver adjusted).
Output: RR and RRR with CIs."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import multifactor as mf, factorial
from nhtsa_stats.analysis.factorial import Factor
frames = mf.load_frames()
def fit(df,d,mask,fa,fb,covs,outc):
    sub,sd=df.loc[mask].reset_index(drop=True),d.subset(mask)
    r=factorial.fit_factorial(sub,sd,[Factor("a",fa,("yes",),("no",)),Factor("b",fb,("yes",),("no",))],[c for c in covs if c not in (fa,fb)],outc)
    m=factorial.margins_table(r).set_index("key"); it=factorial.interaction_table(r).iloc[0]
    return r,m,it
V={v.name.split(" (")[0]:v for v in mf.VICTIMS}
for nm in ["driver killed","passenger killed"]:
    v=V[nm]; df,d=frames[v.frame]; mask=v.select(df); s,a=v.behaviour_cols
    base=v.covariates
    drop={"published":base,"minus other_*":[c for c in base if not c.startswith("other_")],
          "minus unbelted":[c for c in base if c!="unbelted"],
          "minus both":[c for c in base if c!="unbelted" and not c.startswith("other_")]}
    if nm=="passenger killed":
        # add other vehicle's driver alcohol/speeding (like the other-vehicle spec)
        pass
    for k,cv in drop.items():
        r,m,it=fit(df,d,mask,s,a,cv,v.outcome); x=m.loc["01"]
        print(f"{nm:18s} {k:15s} alcRR {x.rr_vs_none:.2f} ({x.rr_vs_none_low:.2f}-{x.rr_vs_none_high:.2f})",flush=True)
# passenger with the OTHER vehicle's driver behaviour added
df,d=frames["person"]; v=V["passenger killed"]; mask=v.select(df)
df["oth_speeding"]=df["oth_speeding"]; 
r,m,it=fit(df,d,mask,"lnk_speeding","lnk_alcohol_im",[*v.covariates,"oth_speeding","oth_alcohol_im"],"killed"); x=m.loc["01"]
print("passenger + other driver's behaviour: alcRR %.2f (%.2f-%.2f)"%(x.rr_vs_none,x.rr_vs_none_low,x.rr_vs_none_high))
# (2) crash-level exceeded x alcohol by number of vehicles
df,d=frames["crash"]
print(df.n_vehicles.value_counts().to_dict())
for nm,mk in [("crash SV",df.n_vehicles.astype(str).isin(["1"])),("crash MV",~df.n_vehicles.astype(str).isin(["1","unknown"]))]:
    r,m,it=fit(df,d,mk.to_numpy(),"exceeded","alcohol_im",[*mf.ENV,*mf.MIX],"fatal")
    print(nm,"n_events",r.n_events,"RRR %.2f (%.2f-%.2f)"%(it.multiplicative_ratio,it.multiplicative_ratio_low,it.multiplicative_ratio_high),"RR11 %.1f"%m.loc["11","rr_vs_none"],"cell n",m.n.to_dict())
# (3) own-behaviour exceeded x alcohol, drivers in MV crashes vs SV
df,d=frames["driver"]
print(df.n_vehicles.value_counts().to_dict())
lp=mf._lpv(df["body"])&df["drv_killed"].notna().to_numpy()
for nm,mk in [("driver MV (crash fatal)",df.n_vehicles.astype(str).isin(["2","3","4"])),("driver SV (crash fatal)",df.n_vehicles.astype(str).isin(["1"]))]:
    for outc in ["fatal","drv_killed"]:
        mask=mk.to_numpy()&df[outc].notna().to_numpy()
        try:
            r,m,it=fit(df,d,mask,"own_exceeded","own_alcohol_im",[*mf.ENV,*mf.PERSON_COVS,"other_speeding","other_alcohol_im"],outc)
            print(nm,outc,"ev",r.n_events,"RRR %.2f (%.2f-%.2f)"%(it.multiplicative_ratio,it.multiplicative_ratio_low,it.multiplicative_ratio_high),"cells",m.n.to_dict(),m.n_events.to_dict(),flush=True)
        except Exception as e: print(nm,outc,"fail",e)
