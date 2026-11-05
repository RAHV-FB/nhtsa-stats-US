"""P03 step 1: reproduce crash-level alcohol-only RR 4.66 and pedestrian 1.22, then profile the
pedestrian population: link coverage by outcome, unknown-driver-alcohol share by outcome,
and absolute (risk difference) vs relative scale.  Look at: RR rows, 'linked' share by killed,
share of 'unknown' alcohol, RD."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import multifactor as mf, factorial
from nhtsa_stats.analysis.factorial import Factor

crash = mf.crash_frame(); per_df, per_design = mf.person_frame()
per_df = mf._other_vehicle_behaviour(per_df)
def run(df, design, sa, sl, covs, outcome, mask=None):
    if mask is None: mask = np.ones(len(df), bool)
    sub, sd = df.loc[mask].reset_index(drop=True), design.subset(mask)
    f=[Factor("speeding", sa, ("yes",), ("no",)), Factor("alcohol", sl, ("yes",), ("no",))]
    covs=[c for c in covs if c not in (sa, sl)]
    r = factorial.fit_factorial(sub, sd, f, covs, outcome)
    m = factorial.margins_table(r).set_index("key")
    return m.loc["01"], m.loc["00"], r.n_events, len(sub)
df, d = crash
m, m0, ne, n = run(df, d, "speeding", "alcohol_im", [*mf.ENV, *mf.MIX], "fatal")
print("CRASH alc-only RR %.3f (%.3f-%.3f) n=%d ev=%d" % (m.rr_vs_none, m.rr_vs_none_low, m.rr_vs_none_high, n, ne))
ped = (per_df.PER_TYP == 5)
print("peds total rows", ped.sum(), "killed known", per_df.loc[ped,'killed'].notna().sum())
pk = per_df[ped & per_df.killed.notna()].copy()
pk['linked'] = pk.linked_veh_no.notna()
w = pk.WEIGHT
print("linked share by killed (weighted):")
print(pk.groupby('killed').apply(lambda g: pd.Series({'n':len(g),'linked_w':np.average(g.linked, weights=g.WEIGHT)})))
pl_ = pk[pk.linked]
print("alcohol_im of linked driver by killed (weighted shares):")
print(pl_.groupby(['killed','lnk_alcohol_im']).WEIGHT.sum().unstack().pipe(lambda x: x.div(x.sum(1),axis=0)))
print(pl_.groupby(['killed','lnk_speeding']).WEIGHT.sum().unstack().pipe(lambda x: x.div(x.sum(1),axis=0)))
mask = (per_df.PER_TYP == 5).to_numpy() & per_df.killed.notna().to_numpy() & per_df.linked_veh_no.notna().to_numpy()
m, m0, ne, n = run(per_df, per_design, "lnk_speeding", "lnk_alcohol_im", [*mf.ENV, "age_band", "sex", "lnk_body"], "killed", mask)
print("PED alc-only RR %.3f (%.3f-%.3f) RD %.4f (%.4f to %.4f) base %.4f n=%d ev=%d" % (m.rr_vs_none, m.rr_vs_none_low, m.rr_vs_none_high, m.rd_vs_none, m.rd_vs_none_low, m.rd_vs_none_high, m0.adj_risk, n, ne))
