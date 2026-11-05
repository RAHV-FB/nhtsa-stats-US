"""F07: reproduce DPC 65.8% / tipping 21%, then attacks on the data.
Tests: (A) unknown-restraint exclusion bounds; (B) misreporting model variants
(reverse/differential); (C) heterogeneity by year, crash type, rollover, veh age, driver alcohol,
age; (D) restraint-code mix. Look at 'red' = 1-RR (reduction) per scenario.
"""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import matched as m

rng = np.random.default_rng(1)
df = m.load_fars_occupants()
elig, flow = m.lpv_flow_and_eligible(df)
elig["belted"] = 1 - elig["unbelted"]

# merge extra covariates from processed person (same row order not guaranteed -> key merge)
import polars as pl
from nhtsa_stats import config
ex = pl.read_parquet(config.PROCESSED_DIR / "fars_person.parquet",
    columns=["YEAR","case_id","VEH_NO","PER_NO","ejected","pr_alcohol","veh_age","veh_rollover","crash_type","REST_USE","REST_MIS","airbag_deployed","n_vehicles"]).to_pandas()
for d in (elig, ex):
    d["k"] = d["YEAR"].astype(int)*10**9 + d["case_id"].astype(int)*10**3 + d["VEH_NO"].astype(int)
    d["kk"] = d["k"]*100 + d["PER_NO"].astype(int)
elig = elig.merge(ex.drop(columns=["YEAR","case_id","VEH_NO","PER_NO","k"]), on="kk", how="left", validate="one_to_one")

def red(c):
    r = m.dpc_combined(c); return 1-float(np.exp(r))
def mk(sub):
    drv = (sub["ptype"]=="driver")&(sub["SEAT_POS"]==11)
    rf = (sub["ptype"]=="passenger")&(sub["SEAT_POS"]==13)
    return m.pair_frame(sub,"belted",drv,rf,carry=["age"])
def cboot(pairs, n=200):
    b = m.bootstrap_counts(pairs, n, rng, cluster="crash_id")
    v = 1-np.exp(m.dpc_combined(b)); v = v[np.isfinite(v)]
    return np.percentile(v,[2.5,97.5])

pairs = mk(elig); c = m.cell_counts(pairs)
print("REPRO pairs", len(pairs), "with death", int(((pairs.k_d+pairs.k_p)>0).sum()),
      "reduction", round(red(c),4), "tipping", round(m.dpc_tipping_point(c),4))
for f in (.1,.2): print(" f",f, round(red(m.reclassify(c,f)),4))

# ---- A: unknown restraint
print("\nA. unknown restraint among driver/RF occupants (all LPV, ages>=13 present in df)")
o = df[df.ptype.isin(["driver","passenger"]) & df.body.isin(m.LPV_BODIES) & df.SEAT_POS.isin([11,13]) & (df.age>=13)]
o = o.assign(unk=(o.restraint=="unknown").astype(int))
print(o.groupby("killed").unk.agg(["mean","sum","size"]).round(4))
print(o.groupby(["SEAT_POS","killed"]).unk.mean().round(4))
print(o.restraint.value_counts())
# all driver+RF vehicles, restraint incl unknown
d_ = o[o.SEAT_POS==11].drop_duplicates("vehicle_id",keep=False); p_ = o[o.SEAT_POS==13].drop_duplicates("vehicle_id",keep=False)
J = d_[["vehicle_id","crash_id","restraint","killed"]].merge(p_[["vehicle_id","restraint","killed"]],on="vehicle_id",suffixes=("_d","_p"))
J = J[(J.killed_d.notna())&(J.killed_p.notna())&((J.killed_d+J.killed_p)>0)]
J["ud"]=J.restraint_d.isin(["unknown"]); J["up"]=J.restraint_p.isin(["unknown"])
print("pairs w/ >=1 death, any restraint codes in {belted,none,unknown}:", len(J[J.restraint_d.isin(["belted","none","unknown"])&J.restraint_p.isin(["belted","none","unknown"])]),
      " with unknown:", int(((J.ud|J.up)&J.restraint_d.isin(["belted","none","unknown"])&J.restraint_p.isin(["belted","none","unknown"])).sum()))
def code_unknown(how):
    s = df[df.ptype.isin(["driver","passenger"]) & df.body.isin(m.LPV_BODIES) & df.SEAT_POS.isin([11,13]) & (df.age>=13) & df.killed.notna()].copy()
    s["killed"]=s["killed"].astype(int)
    if how=="belted": ok = s.restraint.isin(["belted","none","unknown"]); s["belted"]=(s.restraint!="none").astype(int)
    elif how=="unbelted": ok = s.restraint.isin(["belted","none","unknown"]); s["belted"]=(s.restraint=="belted").astype(int)
    elif how=="unk_dead_unb_surv_bel":  # worst case: unknown deaths unbelted, unknown survivors belted -> raises effect
        ok = s.restraint.isin(["belted","none","unknown"]); s["belted"]=np.where(s.restraint=="unknown",1-s.killed,(s.restraint=="belted").astype(int))
    elif how=="unk_dead_bel_surv_unb":  # adverse: unknown deaths belted, unknown survivors unbelted
        ok = s.restraint.isin(["belted","none","unknown"]); s["belted"]=np.where(s.restraint=="unknown",s.killed,(s.restraint=="belted").astype(int))
    s=s[ok]
    return mk(s)
print("\nA2. DPC with unknown restraint recoded (vehicles with that pair)")
for how in ("belted","unbelted","unk_dead_unb_surv_bel","unk_dead_bel_surv_unb"):
    pr = code_unknown(how); cc = m.cell_counts(pr)
    print(f" {how:24s} pairs {len(pr)} reduction {red(cc):.4f}")

# ---- B: misreporting variants on c: cells [xd,kd,xp,kp]
print("\nB. misreporting variants")
def reclass2(c, f_surv, g_dead):
    """f_surv: share of survivors coded belted truly unbelted; g_dead: share of deaths coded belted truly unbelted
    (differential: dead occupants' belt status coded 'belted' wrongly, e.g. assumed)"""
    out = np.array(c,float,copy=True)
    for (axk) in ("d","p"):
        pass
    # driver
    mv = f_surv*out[1,0,:,:]; out[1,0,:,:]-=mv; out[0,0,:,:]+=mv
    mv = g_dead*out[1,1,:,:]; out[1,1,:,:]-=mv; out[0,1,:,:]+=mv
    mv = f_surv*out[:,:,1,0]; out[:,:,1,0]-=mv; out[:,:,0,0]+=mv
    mv = g_dead*out[:,:,1,1]; out[:,:,1,1]-=mv; out[:,:,0,1]+=mv
    return out
for fs,gd in [(.1,0),(.1,.02),(.1,.05),(.05,.05),(0,.05),(0,.10),(0,-0.0)]:
    print(f" survivors f={fs}, belted-coded deaths truly unbelted g={gd}: reduction {red(reclass2(c,fs,gd)):.4f}")
# reverse: unbelted-coded deaths truly belted (bias to null? ) h share of x=0 deaths truly belted
def reclass_rev(c,h):
    out=np.array(c,float,copy=True)
    mv=h*out[0,1,:,:]; out[0,1,:,:]-=mv; out[1,1,:,:]+=mv
    mv=h*out[:,:,0,1]; out[:,:,0,1]-=mv; out[:,:,1,1]+=mv
    return out
for h in (.02,.05,.10): print(f" unbelted-coded deaths truly belted h={h}: reduction {red(reclass_rev(c,h)):.4f}")
# survivor misclassification in either direction symmetrical (unbelted survivors truly belted)
def reclass_surv_unb(c,h):
    out=np.array(c,float,copy=True)
    mv=h*out[0,0,:,:]; out[0,0,:,:]-=mv; out[1,0,:,:]+=mv
    mv=h*out[:,:,0,0]; out[:,:,0,0]-=mv; out[:,:,1,0]+=mv
    return out
for h in (.05,.10): print(f" unbelted-coded survivors truly belted h={h}: reduction {red(reclass_surv_unb(c,h)):.4f}")

