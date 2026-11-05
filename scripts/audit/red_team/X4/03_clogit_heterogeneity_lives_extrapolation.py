"""X4-03  Does the front-seat, 13+ within-vehicle belt estimate transfer to every seat/age/body?
(lives-saved extrapolation, W04/F07) and is the conditional-logit OR homogeneous?

Tests: conditional logit (vehicle strata, crash-robust) of killed on unbelted with
unbelted x {second_row seat, driver vs passenger, body type, age 65+, 2-occupant vs 3+ vehicle}
interactions.  Also counts how the 94,400 'unbelted known-restraint killed' used by
deaths/potential_lives split across seats/ages/bodies relative to what the matched sample covers.
Look at: OR ratio of the interaction terms, p, and the death shares.
"""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import matched as M
pd.set_option("display.width", 200, "display.max_columns", 30)
df = M.load_fars_occupants()
elig, flow = M.lpv_flow_and_eligible(df)
print(flow.to_string(index=False))
sets = M.matched_sets(elig, "vehicle_id")["discordant"].copy()
sets["size"] = sets.groupby("vehicle_id")["killed"].transform("size")
x0 = M.occupant_covariates(sets)
def fit(extra_cols):
    x = x0.copy()
    for k, v in extra_cols.items(): x[k] = v
    r = M.fit_clogit(sets["killed"].to_numpy(), x, sets["vehicle_id"].to_numpy(), sets["crash_id"].to_numpy())
    return r.table.set_index("term")
u = sets["unbelted"].to_numpy().astype(float)
base = fit({}); print("base unbelted OR", base.loc["unbelted", ["odds_ratio", "or_low", "or_high"]].round(3).tolist())
tests = {
 "second_row": (sets.seat == "second_row").to_numpy(float),
 "driver": (sets.ptype == "driver").to_numpy(float),
 "age65+": (sets.age >= 65).to_numpy(float),
 "age13-20": (sets.age <= 20).to_numpy(float),
 "pickup": (sets.body == "pickup").to_numpy(float),
 "suv": (sets.body == "suv").to_numpy(float),
 "van": (sets.body == "van").to_numpy(float),
 "size3+": (sets["size"] >= 3).to_numpy(float),
}
rows = []
for k, z in tests.items():
    t = fit({f"unb_x_{k}": u * z})
    rows.append({"modifier": k, "n_unbelted_in_modifier": int((u * z).sum()), "OR_unbelted_ref": t.loc["unbelted", "odds_ratio"],
                 "OR_ratio_modifier": t.loc[f"unb_x_{k}", "odds_ratio"], "lo": t.loc[f"unb_x_{k}", "or_low"], "hi": t.loc[f"unb_x_{k}", "or_high"],
                 "p": t.loc[f"unb_x_{k}", "p_robust"]})
print(pd.DataFrame(rows).round(3).to_string(index=False))
# who is in the 94,400?  All FARS killed occupants of in-transport pass. vehicles, known restraint
a = df[df.ptype.isin(["driver", "passenger"]) & df.killed.eq(1) & df.restraint.isin(["belted", "none"])]
lpv = a[a.body.isin(M.LPV_BODIES)]
ub = a[a.restraint == "none"]
print("unbelted known killed (all bodies)", len(ub), " in LPV", int(lpv.restraint.eq('none').sum()))
print("unbelted killed share by seat (all):"); print(ub.seat.value_counts(normalize=True).round(3).to_string())
print("unbelted killed share age<13 / 13-20 / 65+:", [round(float(((ub.age<13)).mean()),3), round(float(((ub.age>=13)&(ub.age<=20)).mean()),3), round(float((ub.age>=65).mean()),3)])
print("unbelted killed by body:"); print(ub.body.value_counts(normalize=True).round(3).head(8).to_string())
# Sets where pair design is eligible: share of unbelted killed who sit in a vehicle with >=2 eligible occupants
elig_ids = set(sets.vehicle_id)
print("share of eligible unbelted killed in discordant matched sets:", round(float(elig[(elig.unbelted==1)&(elig.killed==1)].vehicle_id.isin(elig_ids).mean()),3))
print("share of all unbelted killed (known) who were eligible (LPV, seat, 13+):", round(float(len(elig[(elig.unbelted==1)&(elig.killed==1)]) / len(ub)),3))
