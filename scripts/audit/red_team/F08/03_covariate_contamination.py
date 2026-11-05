"""F08 attack 7: covariates that are post-crash / severity-linked or have coding drift.
Re-run the published decomposition (model B, imputed fatal) dropping (a) NHTSA-imputed alcohol
(documented to be possibly severity-informed), (b) surface alone (unknown surface 1.6% -> 4.4%,
largest single composition contributor), (c) alcohol + junction + weather + surface.
Look at: composition share (pp scale, ref P0 / ref P1) and within RR vs published 49%/37%, 1.11.
Run: $RT/bin/rt_py scripts/audit/red_team/F08/03_covariate_contamination.py
"""
import logging
import numpy as np, pandas as pd
from nhtsa_stats.analysis import trends as T
logging.disable(logging.WARNING)
df_all, design_all = T.load()
df, design = T.outcome_frame(df_all, design_all, "fatal")
B = T.COVARIATE_SETS["B"]
variants = {
    "B (published)": B,
    "B minus alcohol_im": [c for c in B if c != "alcohol_im"],
    "B minus surface": [c for c in B if c != "surface"],
    "B minus alcohol_im, junction, weather, surface": [c for c in B if c not in ("alcohol_im", "junction", "weather", "surface")],
}
rows = []
for k, covs in variants.items():
    d = T.decompose(df, design, covs, "fatal", k)
    tab = T.decomposition_table(d, design).set_index("quantity")
    r = {"variant": k}
    for q in ("composition_share_of_change_ref_P0", "composition_share_of_change_ref_P1", "risk_ratio_within_ref_P0"):
        r[q] = f"{tab.loc[q,'estimate']:.3f} ({tab.loc[q,'low']:.3f} to {tab.loc[q,'high']:.3f})"
    rows.append(r); print(r, flush=True)
pd.DataFrame(rows).to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F08/03_contamination.csv", index=False)
