"""X5-04: Is 42 design df right for the narrow domains behind the 'no effect' claims?
Counts, for several event domains, the strata in which the domain contributes any variance (>=1 event in
at least one PSU of a 2-PSU stratum) -> effective df ~ number of such strata.  Prints the t quantile at
42 vs effective df vs z and the factor by which a 95% CI half-width changes.  Also prints the design:
clusters, strata, df.  Look at: eff df for exceed x dark-unlit cells and events in 'too fast' domain.
"""
import numpy as np
from scipy import stats
from nhtsa_stats.analysis import severity
df, design = severity.load("fatal")
print("clusters", design.n_clusters, "strata", design.n_strata, "df", design.df, "n", design.n)
y = df["fatal"].to_numpy()
doms = {
 "fatal events (all)": y == 1,
 "fatal & too-fast": (y == 1) & (df.speeding_type == "too_fast_for_conditions") if "speeding_type" in df else None,
 "fatal & speeding": (y == 1) & (df.speeding == "yes"),
 "fatal & speeding & unlit": (y == 1) & (df.speeding == "yes") & (df.light == "dark_not_lighted"),
 "fatal & young & night(tod)": (y == 1) & (df.young_driver == "yes"),
 "fatal & motorcycle & alcohol": (y == 1) & (df.any_motorcycle == "yes") & (df.alcohol_im == "yes"),
 "fatal & ped-config?": None,
}
print("tod levels", sorted(df.tod.unique())[:6], "light levels", sorted(df.light.unique())[:6])
for k, m in doms.items():
    if m is None: continue
    m = np.asarray(m, bool)
    z = design.cluster_totals(m.astype(float))[:, 0]
    st = design.cluster_stratum
    psus = int((z > 0).sum())
    strata_with = len({int(st[i]) for i in np.nonzero(z > 0)[0]})
    eff = max(psus - strata_with, 1)   # effective df = PSUs with events - strata with events (Korn-Graubard style)
    t42, te = stats.t.ppf(.975, design.df), stats.t.ppf(.975, max(eff, 1))
    print(f"{k:32s} events={int(m.sum()):6d} PSUs with >=1 event={psus:3d} strata with events={strata_with:3d} eff df={eff:3d}  t42={t42:.3f} t_eff={te:.3f} z=1.960  CI half-width x{te/t42:.3f} vs t42")
