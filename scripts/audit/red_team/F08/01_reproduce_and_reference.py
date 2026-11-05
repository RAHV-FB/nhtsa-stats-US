"""F08 attack 1-3: reproduce 49%/37% composition share and 54% denominator share, then vary
the reference period (baseline/comparison years) and the scale of the percentage share.
Look at: composition share (pp scale) vs log-RR scale, for P0/P1 reference, per period choice.
Run: $RT/bin/rt_py scripts/audit/red_team/F08/01_reproduce_and_reference.py
"""
import numpy as np, pandas as pd, logging
from nhtsa_stats.analysis import trends as T
logging.disable(logging.WARNING)
df_all, design_all = T.load()
df, design = T.outcome_frame(df_all, design_all, "fatal")
covs = T.COVARIATE_SETS["B"]
rows = []
def go(label, p0, p1, covs=covs):
    d = T.decompose(df, design, covs, "fatal", label, p0_years=p0, p1_years=p1)
    v = d.values
    tot = v["p1"] - v["p0"]
    rows.append(dict(label=label, p0=v["p0"], p1=v["p1"], RR=v["p1"]/v["p0"],
        comp_pp_refP0=(v["p01"]-v["p0"])/tot, comp_pp_refP1=(v["p1"]-v["p10"])/tot,
        comp_log_refP0=np.log(v["p01"]/v["p0"])/np.log(v["p1"]/v["p0"]),
        comp_log_refP1=np.log(v["p1"]/v["p10"])/np.log(v["p1"]/v["p0"]),
        within_RR_refP0=v["p1"]/v["p01"]))
    print(rows[-1], flush=True)
go("published 2016-19 vs 2020-24", T.P0_YEARS, T.P1_YEARS)
go("P0=2017-19", (2017,2018,2019), T.P1_YEARS)
go("P0=2018-19", (2018,2019), T.P1_YEARS)
go("P0=2016-18 (drop 2019)", (2016,2017,2018), T.P1_YEARS)
go("P0=2017-19, P1=2021-24", (2017,2018,2019), (2021,2022,2023,2024))
go("P0=2016-19, P1=2022-24", T.P0_YEARS, (2022,2023,2024))
out = pd.DataFrame(rows); out.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F08/01_reference.csv", index=False)
print(out.round(3).to_string())

# numerator/denominator scale alternatives from the committed table
n = pd.read_csv("outputs/tables/trends/numerator_denominator.csv")
for oc in ("fatal", "fatal_cc"):
    q = n[(n.outcome == oc) & (n.comparison == "2020-2024 vs 2016-2019")].set_index("quantity").estimate
    K = q.ratio_fatal_crashes_numerator; N = q.ratio_reported_crashes_denominator
    s0 = q.fatal_share_base; s1 = q.fatal_share_comparison; tot = s1 - s0
    # linear scale, three orderings of the exact two-factor split s1/s0 = K / N
    den_a = (s1 - s1 * N) / tot            # numerator first (k0 -> k1 at n0), then denominator at k1
    den_b = (s0 / N - s0) / tot            # denominator first, then numerator
    print(oc, dict(log_den=-np.log(N)/np.log(K/N), lin_den_numfirst=(s1 - s1*N)/tot if False else 1 - (s1*N - s0)/tot,
                   lin_den_denfirst=(s0/N - s0)/tot, lin_den_shapley=0.5*((s1 - s1*N)/tot*0 + 1 - (s1*N - s0)/tot + (s0/N - s0)/tot)))
