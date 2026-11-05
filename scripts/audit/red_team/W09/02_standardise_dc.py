"""W09: do the unbelted-share/unhelmeted-share ranges reflect state *behaviour* or just who dies?
Direct standardisation of the known-restraint unbelted share to the national mix of killed PV
occupants by rural/urban (acc_aux A_RU) x night? (not used) x age group x sex; and for helmets
by rural x age. Also the DC 2019->2024 change (23 -> 47 deaths) with an exact Poisson/ conditional
binomial CI. Look at: standardised range vs crude range 34.6-69.4 / 3.5-74.0."""
import glob, numpy as np, polars as pl, pandas as pd
from scipy import stats
R="data/interim/FARS/"
def rd(t,cols):
    out=[]
    for f in sorted(glob.glob(f"{R}{t}/*.parquet")):
        y=int(f.split('/')[-1].split('.')[0]); d=pl.read_parquet(f); out.append(d.select([c for c in cols if c in d.columns]).with_columns(pl.lit(y).alias("Y")))
    return pl.concat(out,how="diagonal")
per=rd("person",["ST_CASE","STATE","VEH_NO","PER_NO","INJ_SEV","AGE","SEX"]).filter(pl.col("INJ_SEV")==4)
pa=rd("per_aux",["ST_CASE","VEH_NO","PER_NO","A_PTYPE","A_RESTUSE","A_HELMUSE"])
va=rd("veh_aux",["ST_CASE","VEH_NO","A_BODY"])
ac=rd("acc_aux",["ST_CASE","A_RU"])
print("A_RU values",ac["A_RU"].unique().to_list())
d=per.join(pa,on=["Y","ST_CASE","VEH_NO","PER_NO"],how="left").join(va,on=["Y","ST_CASE","VEH_NO"],how="left").join(ac,on=["Y","ST_CASE"],how="left").to_pandas()
d["occ"]=d.A_PTYPE.isin([1,2])
d["age"]=pd.cut(d.AGE.where(d.AGE<120),[-1,15,24,34,44,54,64,74,200],labels=False).fillna(9)
d["sex"]=d.SEX.where(d.SEX.isin([1,2]),9)
d["ru"]=d.A_RU.where(d.A_RU.isin([1,2]),9)
def std(flag,col,cells,name):
    x=d[flag & d[col].isin([1,2])].copy(); x["bad"]=(x[col]==2)
    x["cell"]=list(zip(*[x[c] for c in cells]))
    g=x.groupby(["STATE","cell"]).bad.agg(["sum","count"]).reset_index()
    nat=x.groupby("cell").size(); w=nat/nat.sum()
    res={}
    for st,gg in g.groupby("STATE"):
        gg=gg[gg["count"]>0]; rate=gg.set_index("cell")["sum"]/gg.set_index("cell")["count"]
        ww=w.reindex(rate.index); res[st]=(rate*ww).sum()/ww.sum()   # renormalised over cells present
    s=pd.Series(res); crude=x.groupby("STATE").bad.mean()
    print(f"\n{name}: crude min {crude.min():.3f}({crude.idxmin()}) max {crude.max():.3f}({crude.idxmax()}) sd {crude.std():.3f}")
    print(f"{name}: standardised min {s.min():.3f}({s.idxmin()}) max {s.max():.3f}({s.idxmax()}) sd {s.std():.3f}; corr crude/std {np.corrcoef(crude.reindex(s.index),s)[0,1]:.3f}")
pv=d.occ & d.A_BODY.isin([1,2,3,4,5]); mc=d.occ & (d.A_BODY==7)
std(pv,"A_RESTUSE",["ru","age","sex"],"UNBELTED std rural x age x sex")
std(mc,"A_HELMUSE",["ru","age"],"UNHELMETED std rural x age")
# DC change
for a,b,lab in [(23,47,"DC 2019->2024")]:
    # conditional binomial: b ~ Bin(a+b, 0.5) under no change; Poisson ratio CI via Clopper-Pearson
    lo,hi=stats.beta.ppf([0.025,0.975],[b,b+1],[a+1,a])
    r=lambda p: p/(1-p)
    print(lab,"ratio",round(b/a,2),"95% exact CI",round(r(lo),2),round(r(hi),2),"=> % change",round((r(lo)-1)*100),round((r(hi)-1)*100))
# multi-year DC deaths
print(d[d.STATE==11].groupby("Y").size().to_dict())
