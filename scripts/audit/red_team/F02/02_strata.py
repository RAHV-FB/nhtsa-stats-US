"""F02: stratified (weighted, point-estimate) fatal rates. Tests (a) interstate vs non-interstate within
speed-limit stratum (is the reversal a speed-limit artefact / positivity problem?), (b) rain vs clear within
surface, (c) older-driver crashes by speed limit/urbanicity/n_vehicles, with n of events."""
import pandas as pd, numpy as np
from nhtsa_stats.analysis import severity
df, design = severity.load("fatal")
print([c for c in df.columns][:60])
y = [c for c in df.columns if c in ("fatal","y","outcome")][0] if any(c in df.columns for c in ("fatal","y","outcome")) else None
print("outcome col", y)
w = df["WEIGHT"]
def rate(g): 
    return pd.Series({"n": len(g), "ev": int(g[y].sum()), "rate": (g[y]*g.WEIGHT).sum()/g.WEIGHT.sum()})
def cross(rows, cols, label):
    t = df.groupby([rows, cols]).apply(rate).unstack(cols)
    print("\n==", label); print(t.round(4).to_string())
for lvl in ["interstate"]:
    t = df.groupby(["speed_limit","interstate"]).apply(rate).reset_index()
    p = t.pivot(index="speed_limit", columns="interstate", values=["n","ev","rate"]); print(p.round(4).to_string())
    p["RR"] = p[("rate","yes")]/p[("rate","no")]; print(p["RR"].round(2))
t = df[df.weather.isin(["clear","rain"])].groupby(["surface","weather"]).apply(rate).reset_index()
p = t.pivot(index="surface", columns="weather", values=["n","ev","rate"]); p["RR"]=p[("rate","rain")]/p[("rate","clear")]; print(p.round(4).to_string())
t = df.groupby(["speed_limit","older_driver"]).apply(rate).reset_index().pivot(index="speed_limit",columns="older_driver",values=["n","rate"]); t["RR"]=t[("rate","yes")]/t[("rate","no")]; print(t.round(4).to_string())
t = df.groupby(["n_vehicles","older_driver"]).apply(rate).reset_index().pivot(index="n_vehicles",columns="older_driver",values=["n","rate"]); t["RR"]=t[("rate","yes")]/t[("rate","no")]; print(t.round(4).to_string())
