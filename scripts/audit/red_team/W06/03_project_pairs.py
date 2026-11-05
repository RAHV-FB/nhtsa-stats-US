"""W06: use the project's own harmonised occupant frame to build the published 4,735 pairs;
compare against the raw-A_HELMUSE pair set (script 02: 4,753 pairs, RR 0.657) to see which
rows differ, and compute the helmet DPC tipping-point misreport fraction (belts: 0.21).
Also: published-pair-set leave-one-out (drop each year), and what the discordant core is."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import matched as M
df = M.load_fars_occupants()
mc = df.loc[df.ptype.isin(M.OCCUPANT_PTYPES) & (df.body == "motorcycle") & df.helmet.isin(["helmet", "none"]) & df.killed.notna()].copy()
mc["killed"] = mc.killed.astype(int); mc["helmeted"] = (mc.helmet == "helmet").astype(int)
p = M.pair_frame(mc, "helmeted", mc.ptype == "driver", mc.ptype == "passenger")
c = M.cell_counts(p); print("pairs", len(p), "RR", np.exp(M.dpc_combined(c)), "cells", c.astype(int).ravel())
print("tipping point f (helmet) =", M.dpc_tipping_point(c))
rng = np.random.default_rng(2)
for f in (0.02, 0.05, 0.10):
    bs = M.dpc_combined(M.reclassify(M.bootstrap_counts(p, 1000, rng), f))
    print(f"misreport f={f}: RR={np.exp(M.dpc_combined(M.reclassify(c,f))):.3f} CI=[{np.exp(np.nanquantile(bs,.025)):.3f},{np.exp(np.nanquantile(bs,.975)):.3f}]")
yr = mc.set_index("vehicle_id").YEAR.groupby(level=0).first()
p["Y"] = p.vehicle_id.map(yr)
for y in range(2016, 2025):
    q = p[p.Y != y]; print("drop", y, "RR %.3f" % np.exp(M.dpc_combined(M.cell_counts(q))), "pairs", len(q))
# crash-level leave-out: is any single cell-driven? jackknife of discordant vehicles
dd, dp = M.death_counts(c); print("deaths driver", dd.astype(int).tolist(), "other", dp.astype(int).tolist())
# stricter pair: driver and passenger both age>=18 with known ages, same sex excluded? check sex/age composition of discordant pairs
a = mc.set_index("vehicle_id")
pp = p.copy()
d_age = a.loc[pp.vehicle_id][a.loc[pp.vehicle_id].ptype == "driver"]
print("discordant pairs:", int(((pp.x_d != pp.x_p)).sum()), " of which driver helmeted:", int(((pp.x_d == 1) & (pp.x_p == 0)).sum()))
print("passenger unhelmeted share among published pairs:", 1 - pp.x_p.mean(), " driver:", 1 - pp.x_d.mean())
