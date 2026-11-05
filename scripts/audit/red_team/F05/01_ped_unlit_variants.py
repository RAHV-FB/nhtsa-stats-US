"""F05 attack: is the pedestrian x unlit amplification (IC 93.6/1000, RRR 1.62) robust to the
standardisation population, the comparator for 'pedestrian', the light-factor definition and the
covariate set?  Reproduces published row first (variant V0).  Look at ic, ratio_of_rr columns."""
import sys, dataclasses
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, interactions as I
from nhtsa_stats.analysis.survey import interaction_contrasts

df, design = severity.load("fatal")
print(df.crash_type.value_counts().to_dict()); print(df.light.value_counts().to_dict())
print(pd.crosstab(df.crash_type == "pedestrian", df.n_vehicles))
I.DOMAINS["ped"] = lambda d: (d["crash_type"] == "pedestrian").to_numpy()
I.DOMAINS["nonped"] = lambda d: (d["crash_type"] != "pedestrian").to_numpy()
I.DOMAINS["ped_or_cyc"] = lambda d: d["crash_type"].isin(["pedestrian", "cyclist"]).to_numpy()
I.DOMAINS["nonsv"] = lambda d: (~d["crash_type"].str.startswith("sv_")).to_numpy()
base = next(c for c in I.PAIRS if c.name == "pedestrian x dark_unlit")
P = I.PEDESTRIAN
def pe(ref): return dataclasses.replace(P, reference=ref)
MV = ("mv_angle","mv_rear_end","mv_sideswipe","mv_head_on","mv_other")
DL = dataclasses.replace(I.DARK_UNLIT, exposed=("dark_not_lighted",), reference=("daylight","dark_lighted"))
DK = dataclasses.replace(I.DARK_UNLIT, exposed=("dark_not_lighted","dark_lighted"))
V = {
 "V0 published": base,
 "V1 std over pedestrian crashes only (ATT)": dataclasses.replace(base, domain="ped"),
 "V2 std over non-pedestrian crashes": dataclasses.replace(base, domain="nonped"),
 "V3 std over ped+cyclist crashes": dataclasses.replace(base, domain="ped_or_cyc"),
 "V4 comparator = cyclist only": dataclasses.replace(base, exposures=(pe(("cyclist",)), I.DARK_UNLIT)),
 "V5 comparator = multi-vehicle only": dataclasses.replace(base, exposures=(pe(MV), I.DARK_UNLIT), domain="multi_vehicle"),
 "V6 covariates A (no circumstance)": dataclasses.replace(base, covariates="A"),
 "V7 unlit vs daylight+dark_lighted": dataclasses.replace(base, exposures=(P, DL)),
 "V8 any dark vs daylight": dataclasses.replace(base, exposures=(P, DK)),
}
rows=[]
for k,c in V.items():
    try:
        m, term = I._fit(df, design, "fatal", c)
        ms = I.combo_margins(m, df, design, c)
        ic = interaction_contrasts(ms,"p11","p10","p01","p00")
        r = ic["ic"]; q = ic["log_ratio_of_rr"]
        p = {n: ms.estimate(n).estimate for n in ("p00","p10","p01","p11")}
        rows.append(dict(variant=k, **{n: round(v*1000,2) for n,v in p.items()},
            ic=round(r.estimate*1000,1), ic_lo=round((r.estimate-1.96*r.se)*1000,1), ic_hi=round((r.estimate+1.96*r.se)*1000,1),
            rrr=round(float(np.exp(q.estimate)),3), rrr_lo=round(float(np.exp(q.estimate-1.96*q.se)),3), rrr_hi=round(float(np.exp(q.estimate+1.96*q.se)),3)))
    except Exception as e:
        rows.append(dict(variant=k, err=repr(e)[:150]))
    print(rows[-1], flush=True)
out = pd.DataFrame(rows); pd.set_option("display.width",250); print(out.to_string())
import os; out.to_csv(os.environ.get("RT_OUT","/tmp")+"/F05_variants.csv", index=False)
