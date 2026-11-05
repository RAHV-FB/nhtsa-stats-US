"""F06 attacks 1-5: reproduce RIR; culpability-definition sensitivity; relaxed pair rule;
excluded (both/neither/unknown) crashes; unknown-age bounds; PSU-jackknife vs published CI.
Look at: rows 'primary' vs variants for 15-20 and 75+; excluded-crash age shares.
"""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats.analysis import exposure as ex

OUT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F06/"
pd.set_option("display.width", 200)
drv = ex.build_drivers()
sp = pl.col("SPEEDREL").is_between(2, 5)
pcc = pl.col("P_CRASH2").is_in(ex.PC2_CULPABLE)
pcn = pl.col("P_CRASH2").is_in(ex.PC2_NONCULPABLE)
pcz = pl.col("P_CRASH2").is_in(ex.PC2_NEUTRAL)
err = pl.col("error"); unk = pl.col("drf_unknown")

def mk(culp, non):
    return pl.when(culp).then(pl.lit(1, dtype=pl.Int8)).when(non & ~culp).then(pl.lit(0, dtype=pl.Int8)).otherwise(None)

drv = drv.with_columns(
    v_noerr=mk(sp | pcc, (pl.col("SPEEDREL") == 0) & (pcn | pcz)),
    v_erronly=mk(err, ~unk & ~err),
    v_pc2only=mk(pcc, pcn),                       # strict: nonculp must be struck/encroached
    v_nospeed=mk(pcc | err, (pcn | pcz) & ~unk),
    v_pc2_noneutral_err=mk(sp | pcc | err, (pl.col("SPEEDREL") == 0) & pcn & ~unk),
    v_relaxed=pl.coalesce(pl.col("culp_c1"), pl.lit(0, dtype=pl.Int8)),
)
psu = pl.read_parquet(ex.config.PROCESSED_DIR / "crss_crash.parquet", columns=["YEAR","case_id","PSUSTRAT","PSU_VAR","WEIGHT"]).to_pandas()

def rir(df, col="age_band", jk=False):
    df = df.copy(); df["w"] = df["WEIGHT"]
    g = df.groupby([col, "culpable"])["w"].sum().unstack(fill_value=0)
    r = g[1] / g[0]
    out = pd.DataFrame({"n": df.groupby(col).size(), "rir": r})
    if jk:
        df["cl"] = df["PSUSTRAT"].astype(str) + "_" + df["PSU_VAR"].astype(str)
        cell = df.groupby(["PSUSTRAT", "cl", col, "culpable"])["w"].sum().unstack([col, "culpable"], fill_value=0)
        tot = cell.sum()
        var = pd.Series(0.0, index=r.index)
        for h, sub in cell.groupby(level=0):
            nh = len(sub)
            if nh < 2: continue
            th = []
            for i in range(nh):
                t = tot - sub.iloc[i]
                th.append(np.log(pd.Series({lv: t[(lv, 1)] / t[(lv, 0)] for lv in r.index})))
            th = pd.concat(th, axis=1); m = th.mean(axis=1)
            var += (nh - 1) / nh * ((th.sub(m, axis=0)) ** 2).sum(axis=1)
        se = np.sqrt(var); out["se_log_jk"] = se
        out["lo"] = np.exp(np.log(r) - 2.02*se); out["hi"] = np.exp(np.log(r) + 2.02*se)
    return out

res = {}
for name, col in [("primary","culp_c1"),("no_errcodes","v_noerr"),("err_only","v_erronly"),
                  ("pc2_strict","v_pc2only"),("no_speed","v_nospeed"),("nonculp=struck_only","v_pc2_noneutral_err"),
                  ("relaxed(1 culp, other any)","v_relaxed")]:
    q = ex.qualifying(drv, col)
    t = rir(q, jk=(name=="primary"))
    res[name] = t
    print(f"\n== {name}: crashes={len(q)//2}")
    print(t.loc[["15-20","21-24","65-74","75+","45-54","35-44"]].round(3))
    if name == "primary":
        q.to_pickle(OUT+"primary_sample.pkl")
tab = pd.DataFrame({k: v["rir"] for k, v in res.items()}).round(3)
print("\nRIR by definition:\n", tab)
print("\nRatio 15-20 / 35-44 and 75+/35-44:\n", (tab.loc["15-20"]/tab.loc["35-44"]).round(2).to_dict(), (tab.loc["75+"]/tab.loc["35-44"]).round(2).to_dict())

# excluded crashes: both culpable / neither / unknown, among candidate crashes
crash = pl.read_parquet(ex.config.PROCESSED_DIR/"crss_crash.parquet", columns=["YEAR","case_id","WEIGHT","n_veh_in_transport","any_nonmotorist","hit_and_run"])
cand = ex.candidate_crashes(crash)
d = drv.join(cand.select(["YEAR","case_id"]), on=["YEAR","case_id"], how="semi")
a = d.group_by(["YEAR","case_id"]).agg(
    pl.col("culp_c1").sum().alias("nc"), pl.col("culp_c1").is_null().sum().alias("nu"),
    (pl.col("PER_TYP").is_null() | (pl.col("DR_PRES")!=1)).sum().alias("nodrv"))
a = a.with_columns(cat=pl.when(pl.col("nodrv")>0).then(pl.lit("no_driver")).when((pl.col("nc")==1)&(pl.col("nu")==0)).then(pl.lit("qualifying"))
    .when(pl.col("nc")==2).then(pl.lit("both_culp")).when((pl.col("nc")==0)&(pl.col("nu")==0)).then(pl.lit("neither_culp_both_nonculp"))
    .otherwise(pl.lit("has_undetermined")))
d = d.join(a.select(["YEAR","case_id","cat"]), on=["YEAR","case_id"]).to_pandas()
d = d.merge(psu[["YEAR","case_id","WEIGHT"]], on=["YEAR","case_id"])
print("\nCandidate crash categories (crash counts, weighted share):")
cc = d.groupby("cat").agg(drivers=("age","size"), w=("WEIGHT","sum")); cc["crashes"]=cc.drivers//2; cc["wshare"]=cc.w/cc.w.sum(); print(cc.round(3))
d["teen"] = (d["age_band"]=="15-20"); d["old"]=(d["age_band"]=="75+")
print("\nDriver share teen/75+ by category (weighted):")
print(d.groupby("cat").apply(lambda x: pd.Series({"teen":np.average(x.teen,weights=x.WEIGHT),"75+":np.average(x.old,weights=x.WEIGHT)})).round(4))
# unknown-age bounds: reassign 'unknown' age drivers' culpability counts proportionally
q = pd.read_pickle(OUT+"primary_sample.pkl")
g = q.groupby(["age_band","culpable"])["WEIGHT"].sum().unstack()
tc, tn = g[1].sum(), g[0].sum()
u = g.loc["unknown"]
for lab, (uc, un) in {"unknown all to teens": (u[1], u[0]), "none": (0,0)}.items():
    print(lab, "teen RIR", round((g.loc["15-20",1]+uc)/(g.loc["15-20",0]+un),3) if uc else round(g.loc["15-20",1]/g.loc["15-20",0],3))
# unknown share by culpability
print("unknown-age share among culp / nonculp:", (g.loc["unknown"]/g.sum()).round(4).to_dict())
