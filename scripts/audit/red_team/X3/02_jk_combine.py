"""X3 test 1b: combine JKn replicates from 01 and compare SE(log RR) with published Taylor CIs.
Output: table of published vs JKn 95% CI (t42) for adjusted fatal RRs (model A). Pure pandas; no data load."""
import glob, numpy as np, pandas as pd
from scipy import stats
RT = "/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/X3"
d = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(f"{RT}/jk_*_*.csv"))]).sort_values("rep")
full = d[d.rep == -1].iloc[0]; rep = d[d.rep >= 0]
print("replicates:", len(rep), "strata:", rep.stratum.nunique())
pub = pd.read_csv("outputs/tables/severity/fatal_crude_vs_adjusted.csv")
t = stats.t.ppf(0.975, 42)
rows = []
for f, lvl in [("light","dark_not_lighted"),("any_motorcycle","yes"),("speeding","yes"),("alcohol_im","yes"),
               ("speed_limit","50-55"),("interstate","yes"),("older_driver","yes"),("tod","00-05")]:
    lr = lambda r: np.log(r[f"{f}|lv"]/r[f"{f}|ref"])
    th = lr(full); reps = np.log(rep[f"{f}|lv"]/rep[f"{f}|ref"])
    v_full = ((rep.nh-1)/rep.nh * (reps - th)**2).sum()
    # centred on stratum means
    v_cen = 0
    for h, g in rep.assign(l=reps).groupby("stratum"):
        v_cen += (g.nh.iloc[0]-1)/g.nh.iloc[0] * ((g.l-g.l.mean())**2).sum()
    p = pub[(pub.factor==f)&(pub.level==lvl)].iloc[0]
    se_pub = (np.log(p.A_adj_rr_high)-np.log(p.A_adj_rr_low))/(2*t)
    rows.append(dict(factor=f, level=lvl, rr_rerun=np.exp(th), rr_pub=p.A_adj_rr, se_pub=se_pub,
        se_jk=np.sqrt(v_full), se_jk_cen=np.sqrt(v_cen), ratio_jk_over_pub=np.sqrt(v_full)/se_pub,
        pub_ci=f"{p.A_adj_rr_low:.2f}-{p.A_adj_rr_high:.2f}",
        jk_ci=f"{np.exp(th-t*np.sqrt(v_full)):.2f}-{np.exp(th+t*np.sqrt(v_full)):.2f}"))
r = pd.DataFrame(rows); pd.set_option("display.width", 250); print(r.round(3).to_string())
r.to_csv(f"{RT}/jk_compare.csv", index=False)
