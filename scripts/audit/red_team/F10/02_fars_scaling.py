"""F10 attack 4: FARS scaling. (i) deaths per fatal crash by speeding / alcohol in FARS 2022-24
(AF x deaths assumes averted crashes carry average deaths/crash); (ii) exposure prevalence among
fatal crashes in CRSS (weighted, alcohol_im / speeding) vs FARS; (iii) AF from the exposed-crash
formula pE_fatal*(1-1/RR) using FARS prevalence instead of CRSS prevalence (RR from published table)."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data
f = data.fars_crash((2022,2023,2024))
print("FARS fatal crashes/yr", len(f)/3, "deaths/yr", f.FATALS.sum()/3, "deaths per crash", f.FATALS.mean())
for col in ["speeding","alcohol_driver","driver_bac08_prob"]:
    print(col, f[col].value_counts(dropna=False).head(6).to_dict())
sp = f.speeding.eq(1)
print("speeding: share of crashes %.3f, share of deaths %.3f, deaths/crash yes %.3f no %.3f" % (sp.mean(), f.FATALS[sp].sum()/f.FATALS.sum(), f.FATALS[sp].mean(), f.FATALS[~sp].mean()))
al = f.alcohol_driver.eq(1)
print("alcohol_driver yes: share crashes %.3f deaths %.3f; deaths/crash yes %.3f no %.3f" % (al.mean(), f.FATALS[al].sum()/f.FATALS.sum(), f.FATALS[al].mean(), f.FATALS[~al].mean()))
p = pd.to_numeric(f.driver_bac08_prob, errors="coerce")
print("expected share crashes with BAC>=.08 driver (prob):", p.mean(), " expected-death share", (p*f.FATALS).sum()/f.FATALS.sum())
sp_both = sp & al
print("deaths/crash speeding&alcohol", f.FATALS[sp_both].mean())
# CRSS
from nhtsa_stats.analysis import severity
c, d = severity.load("fatal")
w = c.WEIGHT; fa = c.fatal==1
for yrs,lab in [(range(2016,2025),"all"),(range(2022,2025),"2022-24")]:
    m = c.YEAR.isin(list(yrs)) & fa
    print(lab, "CRSS fatal: speeding yes %.3f  alcohol_im yes %.3f" % (w[m & c.speeding.eq("yes")].sum()/w[m].sum(), w[m & c.alcohol_im.eq("yes")].sum()/w[m].sum()),
          " n fatal sample", int(m.sum()))
# formula check
for nm,pE_crss,rr in [("speeding",None,1.82118),("alcohol",None,4.24382)]:
    pass
m = fa
pE_s = w[m & c.speeding.eq("yes")].sum()/w[m].sum(); pE_a = w[m & c.alcohol_im.eq("yes")].sum()/w[m].sum()
print("formula AF speeding CRSS prev:", pE_s*(1-1/1.82118), " FARS prev:", sp.mean()*(1-1/1.82118))
print("formula AF alcohol CRSS prev:", pE_a*(1-1/4.24382), " FARS driver_alcohol prev:", al.mean()*(1-1/4.24382), " FARS prob prev:", p.mean()*(1-1/4.24382))
print("FARS speeding unknown(nan) share", f.speeding.isna().mean(), " speeding yes among known", f.speeding.eq(1).sum()/f.speeding.notna().sum())
