"""X4-02  (i) Table-2 fallacy: re-estimate headline model-A RRs with exposure-specific adjustment
sets (hand-built DAG, outside reasoning, labelled in output) and compare with model A and crude;
(ii) standardisation population: ATE (all crashes, published) vs ATT (exposed crashes);
(iii) positivity: weighted share of crashes whose (exposure-level x crash_type x urbanicity) cell
has <30 sample crashes -- the cells the "everyone exposed" counterfactual extrapolates into.
"""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import severity, specs
pd.set_option("display.width", 220, "display.max_columns", 30)
df, design = severity.load("fatal")
w = design.weight
CORE = ["YEAR", "region", "urbanicity"]
SETS = {  # exposure -> (factor, level, adjustment set)
 "night 00-05": ("tod", "00-05", CORE + ["weekend"]),
 "dark_not_lighted": ("light", "dark_not_lighted", CORE + ["tod", "weekend", "interstate", "speed_limit", "junction"]),
 "speed 50-55": ("speed_limit", "50-55", CORE + ["interstate"]),
 "speed 70+": ("speed_limit", "70+", CORE + ["interstate"]),
 "interstate": ("interstate", "yes", CORE),
 "motorcycle": ("any_motorcycle", "yes", CORE + ["tod", "weekend", "weather"]),
 "heavy truck": ("any_heavy_truck", "yes", CORE + ["tod", "weekend", "interstate"]),
 "older driver 65+": ("older_driver", "yes", CORE + ["tod", "weekend"]),
 "alcohol (imputed)": ("alcohol_im", "yes", CORE + ["tod", "weekend", "young_driver", "older_driver"]),
 "speeding (any)": ("speeding", "yes", CORE + ["tod", "weekend", "young_driver", "older_driver", "any_motorcycle", "any_heavy_truck", "weather"]),
}
mA = severity.fit(df, design, "fatal", specs.PRE_CRASH)
def get(model, f, lv, domain=None):
    lv_all = severity.observed_levels(df, f)
    ref = lv_all[0]
    ms = model.margins(df, {str(l): (lambda d, l=l: d.assign(**{f: l})) for l in (ref, lv)}, domain=domain)
    e = ms.log_ratio(str(lv), str(ref)); lo, hi = e.ci()
    return np.exp(e.estimate), np.exp(lo), np.exp(hi)
rows = []
for name, (f, lv, adj) in SETS.items():
    crude = severity.crude_table(df, design, "fatal", f, severity.observed_levels(df, f), df.YEAR.nunique()).set_index("level").loc[lv, "crude_rr"]
    a = get(mA, f, lv)
    m = severity.fit(df, design, "fatal", adj + [f])
    s = get(m, f, lv)
    # ATT: model A, standardised to exposed crashes
    dom = (df[f] == lv).to_numpy()
    att = get(mA, f, lv, domain=dom)
    # positivity share
    cell = df.assign(_x=(df[f] == lv)).groupby(["_x", "crash_type", "urbanicity"]).size().rename("cn")
    j = df.assign(_x=(df[f] == lv)).join(cell, on=["_x", "crash_type", "urbanicity"])
    # share of weighted crashes for which the *exposed* cell with same type x urbanicity has < 30 crashes
    ex = df.assign(_x=(df[f] == lv)).query("_x").groupby(["crash_type", "urbanicity"]).size()
    key = pd.MultiIndex.from_frame(df[["crash_type", "urbanicity"]])
    cn = pd.Series(ex.reindex(key).fillna(0).to_numpy())
    thin = float(w[(cn < 30).to_numpy()].sum() / w.sum())
    rows.append({"exposure": name, "crude": crude, "A_ATE": a[0], "A_lo": a[1], "A_hi": a[2], "specific_set": s[0], "sp_lo": s[1], "sp_hi": s[2],
                 "A_ATT": att[0], "ATT_lo": att[1], "ATT_hi": att[2], "w_share_thin_exposed_cell": thin, "n_exposed": int(dom.sum())})
r = pd.DataFrame(rows); r["spec/A"] = r.specific_set / r.A_ATE; r["ATT/ATE"] = r.A_ATT / r.A_ATE
print(r.round(3).to_string(index=False))
r.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/X4/02.csv", index=False)
