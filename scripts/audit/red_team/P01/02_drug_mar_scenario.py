"""P01 attack B3: drug-positive imputed for undetermined-drug crashes under MAR given (speeding,
BAC implicate-mean bin, unbelted, year) using determinate-crash positivity rates; report expected
sum%, union%, ratio, speeding-with-other. Shows how far 65%/1.68/70% move under a plausible
(not claimed) scenario. Also MAR by year-only (weaker conditioning)."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats import config
P=config.PROCESSED_DIR
drv=pl.read_parquet(P/"fars_driver.parquet",columns=["YEAR","case_id","drv_drug_any",*[f"drv_bac08_mi_{i}" for i in range(1,11)]])
crash=drv.group_by(["YEAR","case_id"]).agg(*[pl.col(f"drv_bac08_mi_{i}").max().fill_null(0).alias(f"a{i}") for i in range(1,11)],
 pl.when((pl.col("drv_drug_any")==1).any()).then(pl.lit("yes")).when(pl.col("drv_drug_any").null_count()==0).then(pl.lit("no")).otherwise(pl.lit("undetermined")).alias("drug"))
per=pl.read_parquet(P/"fars_person.parquet",columns=["YEAR","case_id","killed","restraint","PER_TYP","speeding"]).filter(pl.col("killed")==1).join(crash,on=["YEAR","case_id"],how="left").to_pandas()
A=per[[f"a{i}" for i in range(1,11)]].fillna(0).to_numpy(); abar=A.mean(1)
S=(per.speeding==1).to_numpy(); U=((per.restraint=="none")&per.PER_TYP.isin([1,2,9])).to_numpy()
det=(per.drug!="undetermined").to_numpy(); Dy=(per.drug=="yes").to_numpy()
N=len(per)
def run(keys,label):
    df=pd.DataFrame({"S":S,"U":U,"ab":(abar>0.5),"Y":per.YEAR.values,"c":0,"det":det,"D":Dy})
    kk=[k for k in ["S","U","ab","Y"] if k in keys] or ["c"]
    rate=df[df.det].groupby(kk).D.mean().rename("r")
    df=df.join(rate,on=kk); p=np.where(det,Dy.astype(float),df.r.fillna(df[df.det].D.mean()).to_numpy())
    res=[]
    for i in range(10):
        a=A[:,i].astype(bool)
        # expected union: P(not any)=(1-S|a|U)*(1-p) ; expected k
        base=S|a|U; pu=1-(~base)*(1-p)
        k=S.astype(int)+a+U+p
        res.append((k.sum()/N, pu.sum()/N, k.sum()/pu.sum(), ((S&a)|(S&U)|(S&~a&~U)*p).sum()/S.sum() if False else (S*(1-(~(a|U))*(1-p))).sum()/S.sum(), p.sum()))
    m=np.mean(res,0); print(f"{label:40s} sum%={m[0]:.3f} union%={m[1]:.3f} ratio={m[2]:.3f} spd_other={m[3]:.3f} drugdeaths={m[4]:.0f}")
run(["S","U","ab"],"MAR | S,U,BAC")
run(["S","U","ab","Y"],"MAR | S,U,BAC,year")
run([],"MAR marginal (single rate)")
