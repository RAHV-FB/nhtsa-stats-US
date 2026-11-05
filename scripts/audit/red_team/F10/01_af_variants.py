"""F10 attacks 1-3: reproduce speeding/alcohol AF, then vary the estimand.
 (a) published spec (all years); (b) refit 2022-24 only (FARS scaling window);
 (c) police-reported alcohol ('alcohol') instead of NHTSA-imputed 'alcohol_im', years 2019-24;
 (d) alcohol_im with same 2019-24 years. Prints AF (CI).  Look at: does alcohol AF drop when
 imputed alcohol is replaced by police-reported (unknown treated as own level)?"""
import numpy as np
from nhtsa_stats.analysis import severity, specs
from nhtsa_stats.analysis import burden as b
from nhtsa_stats.analysis.burden import Shift

def run(label, years, alc):
    df, design = severity.load("fatal", years)
    covs = [alc if c == "alcohol_im" else c for c in specs.PRE_CRASH]
    if years is not None and len(set(years)) < 3 and "YEAR" in covs:
        pass
    m = severity.fit(df, design, "fatal", covs)
    sh = [Shift("speeding_removed","speeding",("yes",),"no","s"),
          Shift("alcohol_removed",alc,("yes",),"no","a")]
    rows = b._af_rows(m, df, design, sh, "fatal", 41000.0, 37829.3)
    for r in rows:
        print(f"{label:28s} {r['shift']:16s} AF={r['af']:.4f} ({r['af_low']:.4f}-{r['af_high']:.4f}) nexp={r['n_exposed_crss']} deaths={r['fars_scaled_deaths_per_year']:.0f}", flush=True)
    return df, design

df, design = run("A published all yrs", None, "alcohol_im")
w = df["WEIGHT"] if "WEIGHT" in df else None
if w is not None:
    tot = (w*df["fatal"]).groupby(df["YEAR"]).sum()
    print("CRSS weighted fatal crashes by year:\n", tot.round(0).to_string())
    print("mean per yr all:", tot.mean().round(0), " 2022-24:", tot.loc[2022:2024].mean().round(0))
run("B 2022-24 only", [2022,2023,2024], "alcohol_im")
run("C 2019-24 alcohol_im", list(range(2019,2025)), "alcohol_im")
run("D 2019-24 police alcohol", list(range(2019,2025)), "alcohol")
run("E 2016-18 alcohol_im", [2016,2017,2018], "alcohol_im")
run("F 2016-18 police alcohol", [2016,2017,2018], "alcohol")
