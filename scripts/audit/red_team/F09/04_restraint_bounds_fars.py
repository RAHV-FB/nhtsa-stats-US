"""F09 attack 8: restraint gap 98.7% vs 50.8%. (a) Manski bounds treating unknown as belted/unbelted
using committed restraint_reporting; (b) FARS killed LPV occupants belted-among-known (independent census
of the same killed population) vs CRSS killed 50.8; (c) FARS killed belted share by year/age/ejection."""
import numpy as np, pandas as pd
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.analysis import data
r = pd.read_csv("outputs/tables/measurement/restraint_reporting.csv")
for _, x in r[r.kabco.isin([0, 4])].iterrows():
    u = x.pct_unknown/100; b = x.pct_belted_among_known/100
    print(f"CRSS kabco {int(x.kabco)}: known-belted {100*b:.1f}; bounds with unknown: [{100*b*(1-u):.1f}, {100*(b*(1-u)+u):.1f}]")
p = data.fars_person()
o = p[p.body.isin(h.LPV_BODY_GROUPS) & (p.age >= 13) & (p.killed == 1)]
print("FARS killed LPV occupants n", len(o))
k = o[o.restraint.isin(["belted", "none"])]
print("FARS killed belted among known: %.1f  unknown %.1f" % (100*(k.restraint == "belted").mean(), 100*(o.restraint == "unknown").mean()))
print(k.groupby("YEAR").restraint.apply(lambda s: round(100*(s == "belted").mean(), 1)).to_dict())
print("ejected:", k.groupby(k.ejected.astype(str)).restraint.apply(lambda s: round(100*(s == "belted").mean(), 1)).to_dict())
