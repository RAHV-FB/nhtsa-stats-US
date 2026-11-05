"""F09 attacks 1-3: reproduce FARS testing + police-vs-BAC; test whether '87% vs 98%' is
verification-bias driven (survivors tested on suspicion).
Look at: (a) reproduced 2016/2023 test shares & sensitivity; (b) sensitivity of police 'DRINKING'
among tested survivors by state-year survivor-testing tercile (if suspicion-driven, higher
testing -> lower sensitivity); (c) threshold sensitivity (BAC>=.01/.05/.08/.10); (d) PPV."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data
per = data.fars_person()
d = per[per.ptype == "driver"].copy()
d["status"] = np.where(d.killed == 1, "killed", np.where(d.killed == 0, "survived", "unk"))
t = d.groupby(["YEAR", "status"]).agg(n=("alc_tested", "size"), tested=("alc_tested", lambda s: 100*(s == 1).mean()),
    unk=("alc_tested", lambda s: 100*s.isna().mean())).round(1)
print("(a) tested % / status-unknown %\n", t.loc[[2016, 2023]])
# sensitivity
b = d[d.bac_measured.notna() & d.pr_alcohol.notna() & d.status.isin(["killed", "survived"])].copy()
def sens(g, thr):
    p = g.bac_measured >= thr
    return pd.Series({"n": len(g), "prev": p.mean(), "sens": (g.pr_alcohol[p] == 1).mean(),
                      "ppv": (g.bac_measured[g.pr_alcohol == 1] >= thr).mean()})
print("\n(a2) reproduce sens .08\n", b.groupby("status").apply(lambda g: sens(g, .08)).round(3))
print("\n(c) threshold sensitivity\n")
for thr in (.01, .05, .08, .10, .15):
    print(thr, b.groupby("status").apply(lambda g: sens(g, thr)).round(3)[["sens", "ppv"]].to_dict("index"))
# (b) state-year survivor testing rate terciles
rate = d[d.status == "survived"].groupby(["STATE", "YEAR"]).alc_tested.apply(lambda s: (s == 1).mean()).rename("surv_rate")
b = b.merge(rate, on=["STATE", "YEAR"])
b["terc"] = pd.qcut(b.surv_rate, 3, labels=["low", "mid", "high"])
print("\n(b) sensitivity by state-year survivor test-rate tercile (tested drivers)")
print(b.groupby(["status", "terc"], observed=True).apply(lambda g: sens(g, .08)).round(3))
krate = d[d.status == "killed"].groupby(["STATE", "YEAR"]).alc_tested.apply(lambda s: (s == 1).mean()).rename("k_rate")
b = b.merge(krate, on=["STATE", "YEAR"]); b["kterc"] = pd.qcut(b.k_rate, 3, labels=["low", "mid", "high"])
print("\n(b2) by killed test-rate tercile (killed only)")
print(b[b.status == "killed"].groupby("kterc", observed=True).apply(lambda g: sens(g, .08)).round(3))
# police-report prevalence among tested vs untested (killed)
k = d[d.status == "killed"]
print("\n(d) killed: police alcohol=yes share, tested vs not tested:\n",
      k.groupby(k.alc_tested.fillna(-1)).pr_alcohol.apply(lambda s: (s == 1).sum()/s.notna().sum()).round(3))
s = d[d.status == "survived"]
print("survivors:\n", s.groupby(s.alc_tested.fillna(-1)).pr_alcohol.apply(lambda s: (s == 1).sum()/s.notna().sum()).round(3))
