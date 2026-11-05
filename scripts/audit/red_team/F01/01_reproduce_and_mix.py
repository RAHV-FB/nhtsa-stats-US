"""F01 claim: ped share of CRSS crashes 1.2%, of FARS fatal 18.6%, ratio 15.6.
Reproduces from processed data (own computation), then compares the mixed-system ratio
(FARS numerator / CRSS denominator) with the CRSS-internal ratio (CRSS fatal share / CRSS all share)
and compares weighted CRSS fatal-crash totals with FARS counts per year.
Look at: mixed vs internal ratio per factor; weighted CRSS fatal / FARS fatal by year."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.survey import svy_mean
from nhtsa_stats.analysis import specs
facs = {"crash_type":"pedestrian","speeding_type":"exceeded_limit_or_racing","any_motorcycle":"yes",
        "young_driver":"yes","junction":"intersection","surface":"wet","weather":"rain"}
tri=[v for v in facs if v in specs.CRASH_TRI]
df,design=data.crss_crash(outcome=None,tri_state_cols=tri)
fars=data.fars_crash()
for v in tri:
    if v in fars.columns: fars[v]=data.tri_state(fars[v])
fat=df["fatal"].to_numpy(float); isf=fat==1
print("CRSS cols with year:",[c for c in df.columns if 'YEAR' in c.upper()][:3], "n",len(df),"n_fatal",int(isf.sum()))
rows=[]
for v,lv in facs.items():
    ind=(df[v]==lv).to_numpy(float)
    a=svy_mean(design,ind); f=svy_mean(design,ind,isf)
    fv=fars[v]
    if v=="young_driver": fv=fv[fv!="unknown"]
    sf=float((fv==lv).mean())
    rows.append(dict(f=v,lv=lv,share_all=a.estimate,crss_fatal=f.estimate,fars=sf,mixed=sf/a.estimate,internal=f.estimate/a.estimate,
                     int_lo=(f.estimate/a.estimate)*np.exp(-design.tcrit()*np.hypot(f.se/f.estimate,a.se/a.estimate)),
                     int_hi=(f.estimate/a.estimate)*np.exp(design.tcrit()*np.hypot(f.se/f.estimate,a.se/a.estimate))))
r=pd.DataFrame(rows); print(r.round(4).to_string()); r.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F01/mix.csv",index=False)
# weighted totals by year
yc=[c for c in df.columns if c.upper()=="YEAR"]
if yc:
    w=design.weight if hasattr(design,"weight") else None
    print("design attrs",[a for a in dir(design) if not a.startswith("_")])
