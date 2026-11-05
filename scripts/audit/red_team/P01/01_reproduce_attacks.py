"""P01: reproduce 109% / 65% / 1.68 / ~70% independently (own code, per-implicate union) and run
sensitivity attacks: (A) per-implicate union vs expected; (B) drug-undetermined handling
(lower/upper bound, determinate-only subset); (C) unknown-restraint handling; (D) victim-type
restriction (occupants only); (E) per-year stability; (F) null-BAC drivers.
Look at: union share, sum/union, share of speeding deaths with another factor."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats import config
P = config.PROCESSED_DIR
drv = pl.read_parquet(P/"fars_driver.parquet", columns=["YEAR","case_id","drv_drug_any",*[f"drv_bac08_mi_{i}" for i in range(1,11)]])
print("driver rows", drv.height, "null BAC mi_1:", drv["drv_bac08_mi_1"].null_count(), "null drug:", drv["drv_drug_any"].null_count())
crash = drv.group_by(["YEAR","case_id"]).agg(
    *[pl.col(f"drv_bac08_mi_{i}").max().fill_null(0).alias(f"a{i}") for i in range(1,11)],
    pl.when((pl.col("drv_drug_any")==1).any()).then(pl.lit("yes"))
     .when(pl.col("drv_drug_any").null_count()==0).then(pl.lit("no")).otherwise(pl.lit("undetermined")).alias("drug"),
    (pl.col("drv_bac08_mi_1").null_count()>0).alias("bacnull"), pl.len().alias("ndrv"))
per = pl.read_parquet(P/"fars_person.parquet", columns=["YEAR","case_id","killed","restraint","body","PER_TYP","speeding"]).filter(pl.col("killed")==1)
per = per.join(crash, on=["YEAR","case_id"], how="left").to_pandas()
per["drug"]=per["drug"].fillna("undetermined")
A = per[[f"a{i}" for i in range(1,11)]].fillna(0).to_numpy()
S=(per.speeding==1).to_numpy(); Un=((per.restraint=="none")&per.PER_TYP.isin([1,2,9])).to_numpy()
D=(per.drug=="yes").to_numpy(); Dund=(per.drug=="undetermined").to_numpy()
N=len(per); print("deaths",N, "no driver rows (crash NaN ndrv):", int(per.ndrv.isna().sum()))
def stats(S,A,D,U,label,mask=None):
    if mask is None: mask=np.ones(len(S),bool)
    S,A,D,U=S[mask],A[mask],D[mask],U[mask]; n=mask.sum()
    res=[]
    for i in range(A.shape[1]):
        a=A[:,i].astype(bool); anyf=S|a|D|U; k=S.astype(int)+a+D+U
        res.append((S.sum()+a.sum()+D.sum()+U.sum(), anyf.sum(), (S&(a|D|U)).sum()/S.sum(), a.sum(), k.mean()))
    r=np.array(res,float); m=r.mean(0); lo=r.min(0); hi=r.max(0)
    print(f"{label:55s} n={n} sum%={m[0]/n:.3f} union%={m[1]/n:.3f} ratio={m[0]/m[1]:.3f} (impl range {lo[0]/lo[1]:.3f}-{hi[0]/hi[1]:.3f}; union% {lo[1]/n:.4f}-{hi[1]/n:.4f}) spd_other={m[2]:.3f} bac={m[3]:.0f}")
    return m
stats(S,A,D,Un,"A published def (per-implicate union, mean)")
# union of averaged indicator (A>=.5)
Ab=(A.mean(1)>=0.5)[:,None].astype(int); stats(S,Ab,D,Un,"A2 majority-vote BAC (mean>=.5)")
# B drugs
stats(S,A,np.ones(N,bool)&Dund|D,Un,"B1 drug upper bound (undetermined=positive)")
stats(S,A,D,Un,"B2 determinate crashes only",mask=~Dund)
print("determinate share of deaths", (~Dund).mean(), "drug+ share among determinate", D[~Dund].mean())
# drug-pos rate among determinate by year
per["det"]=~Dund; per["D"]=D
print(per.groupby("YEAR").agg(det=("det","mean"),drugpos_of_det=("D",lambda x: np.nan)).round(3).T)
y=per.groupby("YEAR").apply(lambda g: pd.Series({"det_share":g.det.mean(),"dpos_det":g.D[g.det].mean()}))
print(y.round(3))
# C unknown restraint
print(per[per.PER_TYP.isin([1,2,9])].restraint.value_counts(normalize=True).round(3).to_dict())
Uunk=((per.restraint.isin(["none","unknown"]))&per.PER_TYP.isin([1,2,9])).to_numpy()
stats(S,A,D,Uunk,"C1 unbelted incl unknown restraint")
# D occupants only (vehicle occupants PER_TYP 1,2,9)
occ=per.PER_TYP.isin([1,2,9]).to_numpy()
stats(S,A,D,Un,"D1 occupants only",mask=occ)
stats(S,A,D,Un,"D2 non-occupants (ped/cyc/other) only",mask=~occ)
# E per-year
for yr in sorted(per.YEAR.unique()):
    stats(S,A,D,Un,f"E year {yr}",mask=(per.YEAR==yr).to_numpy())
# F: crashes w/o drivers (hit and run) 
print("deaths in crashes with null ndrv:", int(per.ndrv.isna().sum()), "with some null BAC:", int(per.bacnull.fillna(False).sum()))
# G: 3 factors w/o drugs (fully measured)
stats(S,A,np.zeros(N,bool),Un,"G three fully-measured factors (no drugs)")
# joint distribution of "speeding by other factors" without drugs
