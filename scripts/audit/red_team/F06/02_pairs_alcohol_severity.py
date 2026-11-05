"""F06 attacks 6-9: (a) head-to-head pair contrast (no pool assumption); (b) RIR by crash type
(collision) i.e. composition of non-culpable pool; (c) alcohol: imputed vs police-known split,
unknown share by culpability, teen night/day excluding alcohol crashes; (d) severity comparison
within the QIE sample (like-for-like with involvement?).  Needs 01's primary_sample.pkl.
"""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats import config
from nhtsa_stats.ingestion.cache import load_table
OUT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F06/"
pd.set_option("display.width", 200)
q = pd.read_pickle(OUT+"primary_sample.pkl")
cr = pl.read_parquet(config.PROCESSED_DIR/"crss_crash.parquet", columns=["YEAR","case_id","collision","crash_type","speed_limit","fatal","ka","injury","junction","weekend"]).to_pandas()
q = q.merge(cr, on=["YEAR","case_id"], how="left", suffixes=("","_c"))
q["k"] = (q.kabco==4).astype(int)  # check coding
print("kabco values:", q.kabco.value_counts(dropna=False).to_dict())
# (a) head-to-head
q = q.sort_values(["YEAR","case_id"]); q["pos"] = q.groupby(["YEAR","case_id"]).cumcount()
a = q[q.pos==0].reset_index(drop=True); b = q[q.pos==1].reset_index(drop=True)
assert (a.case_id.values==b.case_id.values).all()
def h2h(g1, g2="35-44"):
    m1 = (a.age_band==g1)&(b.age_band==g2); m2 = (b.age_band==g1)&(a.age_band==g2)
    w = np.r_[a.WEIGHT[m1], a.WEIGHT[m2]]; c = np.r_[a.culpable[m1], b.culpable[m2]]
    n = len(w); p = (w*c).sum()/w.sum()
    return n, p, p/(1-p)
print("\n(a) head-to-head vs 35-44 partner: n pairs, P(g culpable), odds  [compare RIR odds ratio vs 35-44 crude]")
for g in ["15-20","21-24","25-34","45-54","55-64","65-74","75+"]:
    print(g, tuple(round(x,3) for x in h2h(g)))
print("teen vs 75+:", tuple(round(x,3) for x in h2h("15-20","75+")), " teen vs 65-74:", tuple(round(x,3) for x in h2h("15-20","65-74")))
# age mixing
print("\npartner age of teen: share of teen drivers' partners aged <25:", end=" ")
t = np.r_[b.age_band[a.age_band=="15-20"], a.age_band[b.age_band=="15-20"]]; print(round(np.mean(np.isin(t,["15-20","21-24"])),3))
# (b) by crash type
def rirs(df):
    g = df.groupby(["age_band","culpable"])["WEIGHT"].sum().unstack(fill_value=0); return (g[1]/g[0])
print("\n(b) RIR by collision type (n drivers):")
rows={}
for c, df in q.groupby("collision"):
    r = rirs(df); rows[c] = {"n":len(df),"teen":r.get("15-20"),"75+":r.get("75+"),"65-74":r.get("65-74"),"35-44":r.get("35-44")}
print(pd.DataFrame(rows).T.round(2))
# (c) alcohol
veh = load_table("CRSS","vehicle",list(config.YEARS),["CASENUM","VEH_NO","VEH_ALCH","V_ALCH_IM"]).to_pandas().rename(columns={"CASENUM":"case_id"})
pass
print("\n(c) VEH_ALCH codes by period:\n", pd.crosstab(q.period, q.VEH_ALCH, normalize="index").round(3))
q["pol_known"] = q.VEH_ALCH.isin([1,2])
for per, df in q.groupby("period"):
    print(f"\nperiod {per}")
    for lab, s in [("police-known", df[df.pol_known]), ("police-unknown", df[~df.pol_known])]:
        g = s.groupby(["alcohol_im","culpable"])["WEIGHT"].sum().unstack(fill_value=0)
        r = (g[1]/g[0]); sh = s.groupby("culpable").apply(lambda x: np.average(x.alcohol_im=="yes",weights=x.WEIGHT))
        print(f"  {lab}: n={len(s)} imputed-yes RIR={r.get('yes',np.nan):.2f}  imputed-yes share culp/nonculp={sh.get(1):.4f}/{sh.get(0):.4f}")
    sh = df.groupby("culpable").apply(lambda x: np.average(~x.pol_known,weights=x.WEIGHT)); print("  police-unknown share nonculp/culp:", sh.round(4).to_dict())
# teen night vs day excluding any alcohol-involved driver
ac = q.groupby(["YEAR","case_id"]).apply(lambda x: (x.alcohol_police=="yes").any()).rename("anyalc").reset_index()
q = q.merge(ac, on=["YEAR","case_id"])
for lab, s in [("all",q),("no police-alcohol driver in crash",q[~q.anyalc])]:
    for nt in ["day","night"]:
        r = rirs(s[s.night==nt]); print(f"teen RIR {lab} {nt}: {r['15-20']:.2f}  (75+ {r['75+']:.2f})")
# unknown-hour
print("night counts:", q.night.value_counts().to_dict())
# (d) severity in QIE sample, crash level
c = q[q.pos==0].copy() if "pos" in q else None
cq = q.groupby(["YEAR","case_id"]).agg(w=("WEIGHT","first"), kabco=("kabco","first"), teen=("age_band",lambda s:(s=="15-20").any()),
    old=("age_band",lambda s:(s=="75+").any()), s65=("age_band",lambda s:(s=="65-74").any()), night=("night","first"), urb=("urbanicity","first"), sl=("speed_limit","first"),
    coll=("collision","first")).reset_index()
cq["K"]=(cq.kabco==4); cq["KA"]=cq.kabco.isin([3,4]); 
def wp(x,col): return np.average(x[col],weights=x.w)
print("\n(d) crash-level severity in QIE sample, crude (weighted):")
for lab, m in [("teen involved",cq.teen),("no teen",~cq.teen),("75+ involved",cq.old),("65-74 involved",cq.s65)]:
    s=cq[m]; print(f"  {lab}: crashes={len(s)} P(K)={wp(s,'K'):.5f} P(KA)={wp(s,'KA'):.4f}")
# direct standardisation on night x urb x speedlimit-band x collision
cq["slb"]=cq.sl.astype(str)
cq["cell"]=cq.night.astype(str)+cq.urb.astype(str)+cq.slb+cq.coll.astype(str)
def std_ratio(flag, out):
    ref = cq[~cq[flag]]; w_ref = ref.groupby("cell").w.sum()
    num=den=0
    for cell, wtot in cq[cq[flag]].groupby("cell").w.sum().items():
        if cell in w_ref.index:
            ex = np.average(ref[ref.cell==cell][out],weights=ref[ref.cell==cell].w)
            ob = np.average(cq[(cq.cell==cell)&cq[flag]][out],weights=cq[(cq.cell==cell)&cq[flag]].w)
            num+=wtot*ob; den+=wtot*ex
    return num/den
for f in ["teen","old","s65"]:
    print(f"  standardised RR KA {f}: {std_ratio(f,'KA'):.2f}   K: {std_ratio(f,'K'):.2f}")
# role split: severity when teen is culpable vs non-culpable
tc = q[q.age_band=="15-20"].merge(cq[["YEAR","case_id","KA","K"]],on=["YEAR","case_id"])
for r_, s in tc.groupby("culpable"): print(f"  teen role culpable={r_}: crashes {len(s)} P(KA)={np.average(s.KA,weights=s.WEIGHT):.4f}")
