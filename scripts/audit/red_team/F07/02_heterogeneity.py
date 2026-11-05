"""F07 part 2 (heterogeneity): reproduce DPC 65.8% / tipping 21%, then attacks on the data.
Tests: (C) heterogeneity by year, crash type, rollover, veh age, driver alcohol,
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


#C
print("\nC. heterogeneity (reduction, crash-boot 95% CI n=200, pairs with death)")
def rep(label, sub):
    pr = mk(sub)
    if len(pr)<500: print(f" {label:28s} n_pairs {len(pr)} too small"); return
    cc=m.cell_counts(pr); r=red(cc)
    ci=cboot(pr) if np.isfinite(r) else (np.nan,np.nan)
    print(f" {label:28s} pairs {len(pr):6d} death-pairs {int(((pr.k_d+pr.k_p)>0).sum()):6d} red {r:.3f} CI {ci[0]:.3f}-{ci[1]:.3f}")

print(elig.crash_type.value_counts().to_dict(), elig.ejected.value_counts().to_dict(), elig.veh_rollover.value_counts().to_dict())
for y in sorted(elig.YEAR.unique()): rep(f"year {y}", elig[elig.YEAR==y])
pass
rep("rollover yes", elig[elig.veh_rollover==1]); rep("rollover no", elig[elig.veh_rollover==0])
rep("not ejected(both)", elig[elig.ejected==0])
rep("veh_age<=5", elig[elig.veh_age<=5]); rep("veh_age>=11", elig[elig.veh_age>=11])
rep("airbag deployed", elig[elig.airbag_deployed==1]); rep("airbag not deployed", elig[elig.airbag_deployed==0])
rep("age 25-64 only", elig[(elig.age>=25)&(elig.age<=64)]); rep("age 13-24", elig[elig.age<=24]); rep("age 65+", elig[elig.age>=65])
rep("female", elig[elig.sex=="female"]) if "female" in set(elig.sex.unique()) else print(elig.sex.unique())
print("pr_alcohol values", elig.pr_alcohol.value_counts(dropna=False).to_dict())
