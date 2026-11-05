"""F03: reproduce speeding-type adjusted RRs (model A) and test robustness of the
'too fast for conditions ~ null' and 'exceeded ~ 5x' claims to specification / population:
 base, no surface+weather adjustment, + crash_type & n_vehicles (model B), single-vehicle only,
 dry roads only, wet/snow/ice only, speed limit <50 vs >=50, years 2016-19 vs 2020-24,
 outcome KA. Look at adj_rr for exceeded_limit_or_racing (EX) and too_fast_for_conditions (TF)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
OUT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F03/"
BASE = [c if c != "speeding" else "speeding_type" for c in specs.PRE_CRASH]

def run(label, outcome="fatal", drop=(), add=(), keep=None, years=None):
    df, design = severity.load(outcome) if years is None else severity.load(outcome, years=years)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    if keep is not None:
        k = keep(df).to_numpy()
        df = df.loc[k].reset_index(drop=True); design = design.subset(k)
    covs = [c for c in BASE if c not in drop] + list(add)
    m = severity.fit(df, design, outcome, covs)
    lv = severity.observed_levels(df, "speeding_type")
    r = severity.factor_contrasts(m, df, "speeding_type", lv).set_index("level")
    row = {"variant": label, "outcome": outcome, "n": len(df)}
    for k, n in (("exceeded_limit_or_racing", "EX"), ("too_fast_for_conditions", "TF"), ("speeding_unspecified", "UN")):
        if k in r.index:
            row[n] = f"{r.loc[k,'adj_rr']:.2f} ({r.loc[k,'adj_rr_low']:.2f}-{r.loc[k,'adj_rr_high']:.2f})"
    print(row, flush=True); return row

rows = []
rows.append(run("limit_le45", keep=lambda d: d["speed_limit"].astype(str).isin(["<=25","30-35","40-45"])))
rows.append(run("limit_ge50", keep=lambda d: d["speed_limit"].astype(str).isin(["50-55","60-65","70+"])))
rows.append(run("years_2016_19", years=list(range(2016, 2020))))
rows.append(run("years_2020_24", years=list(range(2020, 2025))))
rows.append(run("KA_base", outcome="ka"))
rows.append(run("KA_dry_only", outcome="ka", keep=lambda d: d["surface"].astype(str) == "dry", drop=("surface",)))
pd.DataFrame(rows).to_csv(OUT + "01_variants.csv", index=False)
