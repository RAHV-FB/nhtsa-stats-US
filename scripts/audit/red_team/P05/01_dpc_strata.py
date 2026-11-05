"""P05 attack 1-4: reproduce DPC belt RR by driver-behaviour strata, then test
(a) equivalence/CI of speeding vs not ratio, (b) speeding within single vs multi-vehicle (Simpson),
(c) BAC measured-only vs MI-based, thresholds, (d) other crash-circumstance strata (speed limit,
rollover) that the 'independent of how crash happened' wording implies should not matter.
Look at: rr, CI, ratio of RR with 95% CI (strata disjoint -> independent), n pairs."""
import sys
import numpy as np, pandas as pd, polars as pl
from scipy import stats
sys.path.insert(0, "src")
from nhtsa_stats import config
from nhtsa_stats.analysis import matched, restraint_behaviour as rb

NB = 200
rng = np.random.default_rng(20261105)
elig = rb.fars_pairs_frame()
drv = pl.read_parquet(config.PROCESSED_DIR / "fars_driver.parquet",
    columns=["YEAR","case_id","VEH_NO","drv_bac08_measured","drv_alc_test_status","speed_limit_mph","drv_restraint","drv_age"]).to_pandas()
per = pl.read_parquet(config.PROCESSED_DIR / "fars_person.parquet",
    columns=["YEAR","case_id","VEH_NO","PER_NO","veh_rollover"]).to_pandas()
rv = per.groupby(["YEAR","case_id","VEH_NO"],as_index=False)["veh_rollover"].max()
elig = elig.merge(drv,on=["YEAR","case_id","VEH_NO"],how="left").merge(rv,on=["YEAR","case_id","VEH_NO"],how="left")
print("elig rows",len(elig))
print(elig["own_speeding_type"].astype(str).value_counts(dropna=False))
print("alc test status", elig["drv_alc_test_status"].astype(str).value_counts(dropna=False).head(8))
print("bac08_measured", elig["drv_bac08_measured"].value_counts(dropna=False))
print("rollover", elig["veh_rollover"].value_counts(dropna=False))

st = elig["own_speeding_type"].astype(str)
spd = st.isin(["exceeded_limit_or_racing","too_fast_for_conditions","speeding_unspecified"])
nos = st=="no"
p = elig["drv_p_p08"]
single = elig["n_vehicles"].astype(str)=="1"
meas = elig["drv_bac08_measured"]
sl = elig["speed_limit_mph"]
def est(mask,label):
    sub=elig.loc[mask]
    d=(sub["ptype"]=="driver")&(sub["SEAT_POS"]==matched.SEAT_POS_DRIVER)
    r=(sub["ptype"]=="passenger")&(sub["SEAT_POS"]==matched.SEAT_POS_RIGHT_FRONT)
    pairs=matched.pair_frame(sub,"belted",d,r)
    res=matched.dpc_analysis(pairs,label,"belted",rng,NB)
    c=res[res["component"].str.startswith("combined")].iloc[0]
    return dict(label=label,n=int(c.n_pairs),deaths_pairs=int(c.n_pairs_with_death),rr=c.rr_x1_vs_x0,lo=c.rr_low_crash_boot,hi=c.rr_high_crash_boot,se=c.se_log_bootstrap)
specs = {
 "A all":np.ones(len(elig),bool),
 "A not speeding":nos, "A speeding":spd,
 "B single & not spd":single&nos,"B single & spd":single&spd,
 "B multi & not spd":(~single)&nos,"B multi & spd":(~single)&spd,
 "C BAC measured<.08":(meas==0),"C BAC measured>=.08":(meas==1),
 "C BAC MI p<=.5 & not measured":(p<=.5)&meas.isna(),"C BAC MI p>.5 & not measured":(p>.5)&meas.isna(),
 "C BAC p>0.2":(p>0.2),"C BAC p<=0.2":(p<=0.2),
 "C BAC p>0.8":(p>0.8),
 "D limit<=35":(sl<=35),"D limit 40-50":(sl>=40)&(sl<=50),"D limit>=55":(sl>=55),
 "D rollover":(elig["veh_rollover"]==1),"D no rollover":(elig["veh_rollover"]==0),
}
rows=[]
for k,m in specs.items():
    r=est(m.fillna(False).to_numpy() if hasattr(m,"fillna") else m,k); rows.append(r); print(r,flush=True)
out=pd.DataFrame(rows); out.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/P05/01_strata.csv",index=False)
def ratio(a,b):
    A=out.set_index("label").loc[a];B=out.set_index("label").loc[b]
    d=np.log(B.rr)-np.log(A.rr);se=np.hypot(A.se,B.se)
    print(f"{b} / {a}: ratio {np.exp(d):.3f} 95% CI {np.exp(d-1.96*se):.3f}-{np.exp(d+1.96*se):.3f} p={2*stats.norm.sf(abs(d/se)):.3g}")
for a,b in [("A not speeding","A speeding"),("B single & not spd","B single & spd"),("B multi & not spd","B multi & spd"),
            ("C BAC measured<.08","C BAC measured>=.08"),("C BAC p<=0.2","C BAC p>0.2"),("D limit<=35","D limit>=55"),("D no rollover","D rollover")]:
    ratio(a,b)
