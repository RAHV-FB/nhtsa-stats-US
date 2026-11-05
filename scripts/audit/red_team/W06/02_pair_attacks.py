"""W06 attacks on the helmet DPC (31%, 20-40%): rebuild the 4,735 rider-passenger pairs from
interim FARS, then (A) reproduce counts/RR, (B) helmet misreport sensitivity (survivors coded
'helmet' truly not), (C) alternative pair sets (standard motorcycles only, adults only, 'other
helmet' code 16 as unhelmeted not available in A_HELMUSE -> use raw codes), (D) period split,
(E) component heterogeneity (Q), (F) naive discordant contrast, (G) selection/transport:
helmet share on 2-up bikes vs all bikes. Output: RR and 95% vehicle-bootstrap CI per variant."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats.analysis import matched as M
d = pl.read_parquet("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W06/person_all.parquet").to_pandas()
d["src"] = np.where(d.Y <= 2018, d.REST_USE, d.HELM_USE)
mc = d[(d.A_BODY == 7) & d.A_PTYPE.isin([1, 2]) & d.INJ_SEV.isin([0,1,2,3,4])].copy()
mc["veh"] = mc.Y * 10**9 + mc.ST_CASE * 100 + mc.VEH_NO
mc["crash"] = mc.Y * 10**7 + mc.ST_CASE
mc["killed"] = (mc.INJ_SEV == 4).astype(int)
rng = np.random.default_rng(1)

def build(df, helm_rule):
    k = df[df.A_HELMUSE.isin([1, 2])].copy()
    k["x"] = helm_rule(k)
    k = k.rename(columns={"veh": "vehicle_id", "crash": "crash_id"})
    k["x"] = k["x"].astype(int)
    p = M.pair_frame(k.assign(helmeted=k.x), "helmeted", k.A_PTYPE == 1, k.A_PTYPE == 2)
    return p

def est(p, label, nb=1000):
    c = M.cell_counts(p); lg, var = M.dpc_components(c); comb = float(M.dpc_combined(c))
    b = M.dpc_combined(M.bootstrap_counts(p, nb, rng)); lo, hi = np.nanquantile(b, [.025, .975])
    dd, dp = M.death_counts(c)
    print(f"{label:48s} pairs={len(p):5d} disc={int(c[1,:,0,:].sum()+c[0,:,1,:].sum()):4d} RR={np.exp(comb):.3f} [{np.exp(lo):.3f},{np.exp(hi):.3f}] red={1-np.exp(comb):.3f} comps={np.round(np.exp(lg),3)}")
    return c
base = lambda k: (k.A_HELMUSE == 1)
p0 = build(mc, base); c0 = est(p0, "A baseline")
print("cells [x_d,k_d,x_p,k_p] vehicles:", c0.astype(int).ravel())
# B misreport sensitivity
for f in (0.02, 0.05, 0.10, 0.20):
    cf = M.reclassify(c0, f); bs = M.dpc_combined(M.reclassify(M.bootstrap_counts(p0, 1000, rng), f))
    print(f"B misreport f={f}: RR={np.exp(M.dpc_combined(cf)):.3f} CI=[{np.exp(np.nanquantile(bs,.025)):.3f},{np.exp(np.nanquantile(bs,.975)):.3f}]")
# C alternatives
std = mc[mc.BODY_TYP.isin([80, 81])]; est(build(std, base), "C1 BODY_TYP 80/81 only")
est(build(mc[mc.BODY_TYP == 80], base), "C1b BODY_TYP 80 only")
ad = mc[(mc.AGE >= 18) & (mc.AGE < 120)]; est(build(ad, base), "C2 adults 18+ (both known)")
est(build(mc, lambda k: np.isin(k.src, [5, 19])), "C3 code16 'other helmet' as unhelmeted")
est(build(mc, lambda k: np.isin(k.src, [5])), "C4 DOT-compliant only (16,19 unhelmeted)")
est(p0[(p0.k_d + p0.k_p) > 0], "C5 pairs with >=1 pair death")
# D period
for lab, sel in (("2016-2019", mc.Y <= 2019), ("2020-2024", mc.Y >= 2020), ("2016-2018 (REST_USE)", mc.Y <= 2018), ("2019-2024 (HELM_USE)", mc.Y >= 2019)):
    est(build(mc[sel], base), "D " + lab)
for y in (0, 1):
    est(build(mc[mc.ST_CASE % 2 == y], base), f"D' random half {y}")
# E heterogeneity
lg, var = M.dpc_components(c0); w = 1 / var; m = (w * lg).sum() / w.sum(); Q = float((w * (lg - m) ** 2).sum())
from scipy.stats import chi2; print(f"E Q={Q:.2f} df=3 p={chi2.sf(Q,3):.3f}; poisson se comps={np.round(np.sqrt(var),3)}")
# F naive discordant
dd, dp = M.death_counts(c0)
h = dd[1, 0] + dp[0, 1]; u = dd[0, 1] + dp[1, 0]; n10 = c0[1,:,0,:].sum(); n01 = c0[0,:,1,:].sum()
print(f"F naive discordant: helmeted deaths {h:.0f}/{n10+n01:.0f}, unhelmeted {u:.0f}/{n10+n01:.0f}, RR={h/u:.3f}")
print("F concordant death rates driver/passenger: HH", dd[1,1]/c0[1,:,1,:].sum(), dp[1,1]/c0[1,:,1,:].sum(), " UU", dd[0,0]/c0[0,:,0,:].sum(), dp[0,0]/c0[0,:,0,:].sum())
# G transport
allr = mc[mc.A_HELMUSE.isin([1, 2])]
paired = allr[allr.veh.isin(set(p0.vehicle_id))]
print("G helmet-known mc occupants:", len(allr), " in pairs:", len(paired))
for lab, df_ in (("all occupants", allr), ("in analysed pairs", paired)):
    print(f"G {lab}: unhelmeted share (all persons, killed or not)={ (df_.A_HELMUSE==2).mean():.3f}; killed share={(df_.killed).mean():.3f}; of killed unhelmeted={(df_[df_.killed==1].A_HELMUSE==2).mean():.3f}; mean age={df_.AGE[df_.AGE<120].mean():.1f}")
kk = allr[allr.killed == 1]
twoup = allr.groupby("veh").size().rename("nocc"); kk = kk.join(twoup, on="veh")
print("G killed unhelmeted riders on bikes with >=2 recorded occupants:", int(((kk.nocc >= 2) & (kk.A_HELMUSE == 2)).sum()), "of", int((kk.A_HELMUSE == 2).sum()))
# H trend counts
k = allr[allr.killed == 1]; t = k.groupby("Y").A_HELMUSE.agg(unh=lambda s: (s == 2).sum(), hel=lambda s: (s == 1).sum())
t["share"] = t.unh / (t.unh + t.hel); print(t)
print("H unhelmeted deaths 2019->2024: %+.1f%%, helmeted: %+.1f%%" % (100*(t.unh[2024]/t.unh[2019]-1), 100*(t.hel[2024]/t.hel[2019]-1)))
