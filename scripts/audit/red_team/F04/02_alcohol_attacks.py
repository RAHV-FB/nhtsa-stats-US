"""F04 alcohol attacks (CRSS fatal, model A with alcohol swapped).
(a) Is the ALCHL_IM imputation outcome-informed? weighted share imputed 'yes' among police-unknown crashes, by fatal status
    vs share 'yes' among police-known, by fatal status. If imputed-yes share is much higher in fatal unknowns than the known
    fatal share relative to nonfatal, imputation uses severity (leakage-like).
(b) three-level coding (no/yes/unknown separate; use all rows) RR yes vs no.
(c) restrict to night, single vehicle, excl motorcycle: IM vs complete-case RR.
(d) complete-case RR by year (the 'stable across break' claim) with CI."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
df, design = severity.load("fatal")
w = design.weight if hasattr(design,"weight") else None
w = np.asarray(design.weight)
df["w"]=w
unk = df["alcohol"]=="unknown"
print("alcohol values", df["alcohol"].value_counts().to_dict(), "| im", df["alcohol_im"].value_counts().to_dict())
for per,yrs in (("16-18",[2016,2017,2018]),("19-24",range(2019,2025))):
    s = df[df.YEAR.isin(list(yrs))]
    for lab,sub in (("police-unknown",s[s.alcohol=="unknown"]),("police-known",s[s.alcohol!="unknown"])):
        for f in (0,1):
            t = sub[sub.fatal==f]
            print(per,lab,"fatal=%d"%f,"n=%d"%len(t),"wtd P(alc_im=yes)=%.3f"%(np.average(t.alcohol_im=="yes",weights=t.w)),
                  "P(unknown)=%.3f"%np.nan if False else "")
    for f in (0,1):
        t=s[s.fatal==f]; print(per,"fatal=%d"%f,"wtd share police-unknown=%.3f"%np.average(t.alcohol=="unknown",weights=t.w))
def rr(d,des,var,covs=None,levels=("no","yes")):
    covs = covs or [c for c in specs.PRE_CRASH if c!="alcohol_im"]+[var]
    m = severity.fit(d,des,"fatal",covs)
    lv = severity.observed_levels(d,var,list(levels))
    t = severity.factor_contrasts(m,d,var,lv).set_index("level").loc["yes"]
    return "%.2f (%.2f-%.2f)"%(t.adj_rr,t.adj_rr_low,t.adj_rr_high)
# (b) 3-level: unknown own category, all rows
print("(b) police alcohol 3-level, all rows:", rr(df,design,"alcohol",levels=("no","yes","unknown")))
print("    published-style IM all:", rr(df,design,"alcohol_im"))
# (c) subsets
subsets = {"night(dark any)": df.light.str.startswith("dark").to_numpy(),
           "single-vehicle": (df.n_vehicles.astype(str).isin(["1"])).to_numpy() if "n_vehicles" in df else None,
           "no motorcycle": (df.any_motorcycle=="no").to_numpy()}
print(df.n_vehicles.value_counts().head(5).to_dict())
for name,k in subsets.items():
    if k is None: continue
    d=df.loc[k].reset_index(drop=True); des=design.subset(k)
    covs=[c for c in specs.PRE_CRASH if c not in("alcohol_im","n_vehicles","any_motorcycle")]
    try:
        a=rr(d,des,"alcohol_im",covs=covs+["alcohol_im"])
        kk=(d.alcohol!="unknown").to_numpy(); d2=d.loc[kk].reset_index(drop=True)
        b=rr(d2,des.subset(kk),"alcohol",covs=covs+["alcohol"])
        print(f"(c) {name}: n={len(d)} IM {a} | CC {b}",flush=True)
    except Exception as e: print(name,"fail",e)
# (d) CC by year groups
for yrs in ([2016,2017],[2018,2019],[2020,2021],[2022,2023,2024]):
    k=(df.YEAR.isin(yrs)&(df.alcohol!="unknown")).to_numpy(); d=df.loc[k].reset_index(drop=True)
    covs=[c for c in specs.PRE_CRASH if c not in("alcohol_im","YEAR")]+["alcohol"]
    print("(d) CC",yrs,"n=%d ev=%d"%(len(d),d.fatal.sum()),rr(d,design.subset(k),"alcohol",covs=covs),flush=True)
