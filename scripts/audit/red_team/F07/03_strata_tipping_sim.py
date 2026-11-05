"""F07 part 3: (a) tipping-point f and reduction by crash type / rollover / alcohol-driver strata;
(b) simulation of DPC under logistic (non-multiplicative) risk with a shared crash-severity latent and
within-pair belt correlation + unmeasured driver-specific frailty: does 1-RR recover the true
marginal risk reduction? Look at 'DPC' vs 'true'."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats.analysis import matched as m
from nhtsa_stats import config
df = m.load_fars_occupants(); elig,_ = m.lpv_flow_and_eligible(df); elig["belted"]=1-elig["unbelted"]
ex = pl.read_parquet(config.PROCESSED_DIR/"fars_person.parquet",columns=["YEAR","case_id","VEH_NO","PER_NO","pr_alcohol","crash_type","veh_rollover","speeding"]).to_pandas()
for d in (elig,ex): d["kk"]=(d["YEAR"].astype(int)*10**9+d["case_id"].astype(int)*10**3+d["VEH_NO"].astype(int))*100+d["PER_NO"].astype(int)
elig=elig.merge(ex[["kk","pr_alcohol","crash_type","veh_rollover","speeding"]],on="kk",how="left",validate="one_to_one")
def mk(sub):
    drv=(sub.ptype=="driver")&(sub.SEAT_POS==11); rf=(sub.ptype=="passenger")&(sub.SEAT_POS==13)
    return m.pair_frame(sub,"belted",drv,rf)
rng=np.random.default_rng(3)
def row(label,sub):
    pr=mk(sub); 
    if len(pr)<800: print(label,"small",len(pr)); return
    c=m.cell_counts(pr); r=1-float(np.exp(m.dpc_combined(c))); t=m.dpc_tipping_point(c)
    b=m.bootstrap_counts(pr,200,rng,cluster="crash_id"); v=1-np.exp(m.dpc_combined(b)); v=v[np.isfinite(v)]
    print(f"{label:26s} pairs {len(pr):6d} red {r:.3f} ({np.percentile(v,2.5):.3f}-{np.percentile(v,97.5):.3f}) tipping f {t:.3f}")
print("A. strata"); row("all",elig)
for ct in ["mv_angle","sv_off_roadway","mv_head_on","mv_rear_end","sv_rollover_first","mv_sideswipe"]: row(ct,elig[elig.crash_type==ct])
row("driver alcohol=1",elig[elig.pr_alcohol==1]); row("driver alcohol=0",elig[elig.pr_alcohol==0])
row("speeding=1",elig[elig.speeding==1]); row("speeding=0",elig[elig.speeding==0])
row("rollover no",elig[elig.veh_rollover==0]); row("rollover yes",elig[elig.veh_rollover==1])

print("\nB. simulation: truth vs DPC")
def sim(sd_sev, rho_belt, frail_sd, N=2_000_000, beta=-1.9, base=-3.2, seat_rf=0.0):
    z=rng.normal(0,sd_sev,N)               # shared crash severity
    u=rng.normal(0,1,N)<0  # placeholder
    # belt use correlated within pair via shared propensity
    shared=rng.normal(0,1,N)
    def belt(): 
        e=np.sqrt(rho_belt)*shared+np.sqrt(1-rho_belt)*rng.normal(0,1,N); return (e< 0.55).astype(int)  # ~71% belted
    xd,xp=belt(),belt()
    fd,fp=rng.normal(0,frail_sd,N),rng.normal(0,frail_sd,N)
    # unmeasured driver-specific confounding: unbelted drivers more frail
    fd=fd+0.0
    def p(x,f,s): return 1/(1+np.exp(-(base+z+f+beta*x*(-1)*-1+s)))
    # beta<0 for belted: logit effect of belt = beta
    pd_=p(xd,fd,0.0); pp_=p(xp,fp,seat_rf)
    kd=rng.random(N)<pd_; kp=rng.random(N)<pp_
    pairs=pd.DataFrame({"x_d":xd,"k_d":kd.astype(int),"x_p":xp,"k_p":kp.astype(int)})
    c=m.cell_counts(pairs); dpc=1-float(np.exp(m.dpc_combined(c)))
    # true marginal RR among all occupants: counterfactual all belted vs all unbelted
    p1=lambda f,s:1/(1+np.exp(-(base+z+f+beta+s))); p0=lambda f,s:1/(1+np.exp(-(base+z+f+s)))
    true=1-(p1(fd,0).sum()+p1(fp,seat_rf).sum())/(p0(fd,0).sum()+p0(fp,seat_rf).sum())
    return dpc,true
for sd in (0.5,1.5,2.5):
    for rho in (0.0,0.5):
        for base in (-5.0,-3.0,-1.0):
            d,t=sim(sd,rho,0.5,base=base); print(f"sev_sd {sd} belt_corr {rho} base {base}: DPC {d:.3f} true {t:.3f}")
