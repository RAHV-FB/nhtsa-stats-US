"""P05 attack 2: is 'speeding does not change belt RR' a marginal coincidence (Simpson)?
Speeding/BAC are concentrated in single-vehicle crashes where belt RR is lower. Estimate
speeding and BAC>=.08 contrasts WITHIN single/multi-vehicle (and within rollover/no rollover),
then an inverse-variance pooled within-configuration ratio. Output: ratio of RRs + CI."""
import sys
import numpy as np, pandas as pd, polars as pl
from scipy import stats
sys.path.insert(0, "src")
from nhtsa_stats import config
from nhtsa_stats.analysis import matched, restraint_behaviour as rb
NB=200; rng=np.random.default_rng(5)
elig=rb.fars_pairs_frame()
per=pl.read_parquet(config.PROCESSED_DIR/"fars_person.parquet",columns=["YEAR","case_id","VEH_NO","veh_rollover"]).to_pandas()
rv=per.groupby(["YEAR","case_id","VEH_NO"],as_index=False)["veh_rollover"].max()
elig=elig.merge(rv,on=["YEAR","case_id","VEH_NO"],how="left")
st=elig["own_speeding_type"].astype(str)
spd=st.isin(["exceeded_limit_or_racing","too_fast_for_conditions","speeding_unspecified"]); nos=st=="no"
bhi=elig["drv_p_p08"]>0.5; blo=~bhi
single=(elig["n_vehicles"].astype(str)=="1"); roll=elig["veh_rollover"]==1
print("share of speeding pairs that are single-vehicle: %.3f ; of not-speeding: %.3f"%(single[spd].mean(),single[nos].mean()))
print("share BAC>=.08 single-vehicle: %.3f ; BAC<.08: %.3f"%(single[bhi].mean(),single[blo].mean()))
print("share speeding rollover %.3f vs not %.3f"%(roll[spd].mean(),roll[nos].mean()))
def est(mask):
    sub=elig.loc[mask]
    d=(sub["ptype"]=="driver")&(sub["SEAT_POS"]==matched.SEAT_POS_DRIVER)
    r=(sub["ptype"]=="passenger")&(sub["SEAT_POS"]==matched.SEAT_POS_RIGHT_FRONT)
    res=matched.dpc_analysis(matched.pair_frame(sub,"belted",d,r),"x","belted",rng,NB)
    c=res[res["component"].str.startswith("combined")].iloc[0]
    return c.rr_x1_vs_x0,c.se_log_bootstrap,int(c.n_pairs)
def contrast(name,exp,ref,layers):
    L=[];W=[]
    for ln,lm in layers.items():
        a=est(ref&lm);b=est(exp&lm)
        d=np.log(b[0])-np.log(a[0]);se=np.hypot(a[1],b[1])
        print(f"{name} | {ln}: ref {a[0]:.3f} (n={a[2]}) exp {b[0]:.3f} (n={b[2]}) ratio {np.exp(d):.3f} CI {np.exp(d-1.96*se):.3f}-{np.exp(d+1.96*se):.3f}",flush=True)
        L.append(d);W.append(1/se**2)
    L=np.array(L);W=np.array(W);m=(L*W).sum()/W.sum();s=W.sum()**-.5
    print(f"{name} | pooled within layers: ratio {np.exp(m):.3f} CI {np.exp(m-1.96*s):.3f}-{np.exp(m+1.96*s):.3f} p={2*stats.norm.sf(abs(m/s)):.3g}\n")
contrast("speeding vs not, by single/multi",spd,nos,{"single":single,"multi":~single})
contrast("speeding vs not, by rollover",spd,nos,{"rollover":roll,"no rollover":~roll})
contrast("speeding vs not, by single/multi x rollover",spd,nos,{"s&r":single&roll,"s&nr":single&~roll,"m&r":~single&roll,"m&nr":~single&~roll})
contrast("BAC>=.08 vs <.08, by single/multi",bhi,blo,{"single":single,"multi":~single})
contrast("BAC>=.08 vs <.08, by single/multi x rollover",bhi,blo,{"s&r":single&roll,"s&nr":single&~roll,"m&r":~single&roll,"m&nr":~single&~roll})
