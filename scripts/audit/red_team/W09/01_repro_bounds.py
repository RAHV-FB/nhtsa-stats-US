"""W09 claim: unbelted share of PV occupants killed ranges 35%-69% by state; unhelmeted share of
motorcyclists killed 4%-74%. Independent recomputation from FARS interim person/per_aux/veh_aux
(INJ_SEV 4, 2016-2024), then (a) unknown->belted / unknown->unbelted bounds per state,
(b) Wilson 95% CIs for the extreme states, (c) year-by-year stability, (d) state-by-state
ranking after worst-case bounds. Look at: min/max reproduction, whether ranges survive bounds."""
import glob, numpy as np, polars as pl, pandas as pd
from math import sqrt
R="data/interim/FARS/"
def rd(t,cols):
    fs=sorted(glob.glob(f"{R}{t}/*.parquet")); out=[]
    for f in fs:
        y=int(f.split('/')[-1].split('.')[0]); d=pl.read_parquet(f); 
        c=[x for x in cols if x in d.columns]; out.append(d.select(c).with_columns(pl.lit(y).alias("Y")))
    return pl.concat(out,how="diagonal")
per=rd("person",["ST_CASE","STATE","VEH_NO","PER_NO","INJ_SEV","PER_TYP"]).filter(pl.col("INJ_SEV")==4)
pa=rd("per_aux",["ST_CASE","VEH_NO","PER_NO","A_PTYPE","A_RESTUSE","A_HELMUSE"])
va=rd("veh_aux",["ST_CASE","VEH_NO","A_BODY"])
d=per.join(pa,on=["Y","ST_CASE","VEH_NO","PER_NO"],how="left").join(va,on=["Y","ST_CASE","VEH_NO"],how="left")
occ=pl.col("A_PTYPE").is_in([1,2])
d=d.with_columns((occ&pl.col("A_BODY").is_in([1,2,3,4,5])).alias("pv"),(occ&(pl.col("A_BODY")==7)).alias("mc"))
print("PV",d["pv"].sum(),"MC",d["mc"].sum())
def tab(flag,col,bad):
    t=(d.filter(pl.col(flag)).group_by(["STATE","Y"]).agg(
        pl.len().alias("n"),(pl.col(col)==bad).sum().alias("bad"),(pl.col(col)==(3-bad)).sum().alias("good")).to_pandas())
    return t
def wilson(k,n,z=1.96):
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return c-h,c+h
for name,flag,col,bad in [("UNBELTED","pv","A_RESTUSE",2),("UNHELMETED","mc","A_HELMUSE",2)]:
    t=tab(flag,col,bad); s=t.groupby("STATE")[["n","bad","good"]].sum()
    s["unk"]=s.n-s.bad-s.good; s["unk_sh"]=s.unk/s.n; s["known_sh"]=s.bad/(s.bad+s.good)
    s["lo_unk_good"]=s.bad/s.n          # unknown -> not-bad
    s["hi_unk_bad"]=(s.bad+s.unk)/s.n   # unknown -> bad
    ci=[wilson(r.bad,r.bad+r.good) for r in s.itertuples()]
    s["ci_lo"]=[c[0] for c in ci]; s["ci_hi"]=[c[1] for c in ci]
    s["rank"]=s.known_sh.rank()
    print("\n==",name); print(s.sort_values("known_sh").round(3).to_string())
    print("known range",s.known_sh.min().round(4),s.known_sh.idxmin(),s.known_sh.max().round(4),s.known_sh.idxmax())
    print("all-unk->notbad range",s.lo_unk_good.min().round(3),s.lo_unk_good.max().round(3),"| all-unk->bad range",s.hi_unk_bad.min().round(3),s.hi_unk_bad.max().round(3))
    # sharpest case: min state gets unk->bad, max state gets unk->notbad
    mn=s.known_sh.idxmin(); mx=s.known_sh.idxmax()
    print("extreme states gap under adversarial unknowns: min-state upper",s.loc[mn,"hi_unk_bad"].round(3),"max-state lower",s.loc[mx,"lo_unk_good"].round(3))
    # year stability
    t["sh"]=t.bad/(t.bad+t.good); t["nk"]=t.bad+t.good
    w=t.pivot(index="STATE",columns="Y",values="sh")
    print("year-sd of share (mean over states)",w.std(axis=1).mean().round(3),"; between-state sd of pooled",s.known_sh.std().round(3))
    for st in [mn,mx]:
        print("state",st,"yearly",w.loc[st].round(2).to_dict())
    # 3-yr windows min/max
    for a,b in [(2016,2018),(2019,2021),(2022,2024)]:
        tt=t[(t.Y>=a)&(t.Y<=b)].groupby("STATE")[["bad","nk"]].sum(); tt["sh"]=tt.bad/tt.nk
        print(a,b,"min",tt.sh.idxmin(),tt.sh.min().round(3),"max",tt.sh.idxmax(),tt.sh.max().round(3))
    s.to_csv(f"/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W09/{name}.csv")
    # permutation-free chance test: heterogeneity chi2 of known shares
    p0=s.bad.sum()/(s.bad.sum()+s.good.sum()); nk=s.bad+s.good
    z=(s.known_sh-p0)/np.sqrt(p0*(1-p0)/nk); print("pooled p",round(p0,3),"chi2",round((z**2).sum(),0),"df",len(s)-1,"max|z|",z.abs().max().round(1))
    # expected range under null of equal p0 w/ binomial noise
    rng=np.random.default_rng(1); mins=[];maxs=[]
    for _ in range(2000):
        x=rng.binomial(nk.values,p0)/nk.values; mins.append(x.min()); maxs.append(x.max())
    print("null (all states same p) range: min 2.5-97.5%",np.percentile(mins,[2.5,97.5]).round(3),"max",np.percentile(maxs,[2.5,97.5]).round(3))
