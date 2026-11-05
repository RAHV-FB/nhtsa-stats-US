"""Verifier F03: rerun first-six variants of attacker 01 (base, no surface/weather, model B, single-veh, dry, wet), limits, + crude/adj by limit."""
import pandas as pd
from nhtsa_stats.analysis import severity, specs
BASE = [c if c != "speeding" else "speeding_type" for c in specs.PRE_CRASH]
def run(label, outcome="fatal", drop=(), add=(), keep=None):
    df, design = severity.load(outcome)
    df["speeding_type"] = df["speeding_type"].fillna("unknown")
    if keep is not None:
        k = keep(df).to_numpy(); df = df.loc[k].reset_index(drop=True); design = design.subset(k)
    m = severity.fit(df, design, outcome, [c for c in BASE if c not in drop] + list(add))
    r = severity.factor_contrasts(m, df, "speeding_type", severity.observed_levels(df, "speeding_type")).set_index("level")
    out = {"variant": label, "n": len(df)}
    for k, n in (("exceeded_limit_or_racing","EX"),("too_fast_for_conditions","TF")):
        if k in r.index: out[n] = f"{r.loc[k,'adj_rr']:.2f} ({r.loc[k,'adj_rr_low']:.2f}-{r.loc[k,'adj_rr_high']:.2f})"
    print(out, flush=True)
run("A_base")
run("A_no_surf_weather", drop=("surface","weather"))
run("B_add_crashtype_nveh", add=specs.CIRCUMSTANCE)
run("B_ka", outcome="ka", add=specs.CIRCUMSTANCE)
run("limit_le45", keep=lambda d: d["speed_limit"].astype(str).isin(["<=25","30-35","40-45"]))
run("limit_ge50", keep=lambda d: d["speed_limit"].astype(str).isin(["50-55","60-65","70+"]))
run("limit_ge50_nolimitadj", keep=lambda d: d["speed_limit"].astype(str).isin(["50-55","60-65","70+"]), drop=("speed_limit",))
