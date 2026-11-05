"""P05 attack 3: CRSS 46->28->19. Is the attenuation order-dependent / what does 'violent crash'
mean? Re-fit the unbelted RR with covariate blocks in other orders and alone, same sample
as the published nested table; also drop unknown-restraint rows (published sample keeps UNK as a
third level that is neither belted nor unbelted). Output: RR per covariate set."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from nhtsa_stats.analysis import factorial, multifactor
from nhtsa_stats.analysis.restraint_behaviour import UNBELTED
df, design = multifactor.person_frame()
base = (df["relation"].isin(["driver","passenger"]).to_numpy()
  & df["body"].isin(list(multifactor.LPV_BODY_GROUPS)).to_numpy()
  & ~df["age_band"].isin(["0-14", multifactor.UNK]).to_numpy() & df["killed"].notna().to_numpy())
print("restraint distribution (LPV 15+):\n", df.loc[base,"restraint"].value_counts(dropna=False))
w=design.weight if hasattr(design,"weight") else None
ENV=multifactor.ENV; PER=["age_band","sex","role","body"]; BEH=["lnk_speeding","lnk_alcohol_im"]; CFG=["crash_type","n_vehicles"]
sets={"crude":[],"config only":CFG,"behaviour only":BEH,"person only":PER,"env only":ENV,
 "config+person":PER+CFG,"behaviour+person":PER+BEH,"person+config+behaviour (no env)":PER+BEH+CFG,"all":ENV+PER+BEH+CFG}
def run(maskname,mask):
    sub=df.loc[mask].reset_index(drop=True); sd=design.subset(mask)
    print(f"\n== {maskname}: n={len(sub)}",flush=True)
    for k,c in sets.items():
        res=factorial.fit_factorial(sub,sd,[UNBELTED],c,"killed")
        mt=factorial.margins_table(res).set_index("key")
        print(f"{k:38s} RR {mt.loc['1','rr_vs_none']:.1f} ({mt.loc['1','rr_vs_none_low']:.1f}-{mt.loc['1','rr_vs_none_high']:.1f}) RD {mt.loc['1','rd_vs_none']:.4f}",flush=True)
run("published sample (belted/none/UNK)", base & df["restraint"].isin(["belted","none",multifactor.UNK]).to_numpy())
run("known restraint only", base & df["restraint"].isin(["belted","none"]).to_numpy())
