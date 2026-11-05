"""F01 attacks: (a) does pooling hide year instability / COVID shift in mixed ratios (ped, motorcycle, speeding_type)?
(b) is CRSS weighted fatal-crash total consistent with FARS count (denominator calibration)?
(c) pooled ratio excluding 2020, and ped crude 'rate' vs FARS/CRSS-total implied rate.
Look at: per-year mixed ratio range; CRSS fatal weighted total / FARS count."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data, specs
from nhtsa_stats.analysis.survey import svy_mean
facs={"crash_type":"pedestrian","speeding_type":"exceeded_limit_or_racing","any_motorcycle":"yes"}
tri=[v for v in facs if v in specs.CRASH_TRI]
df,design=data.crss_crash(outcome=None,tri_state_cols=tri)
fars=data.fars_crash()
for v in tri: fars[v]=data.tri_state(fars[v])
print("fars cols year:",[c for c in fars.columns if c.upper()=="YEAR"])
isf=df["fatal"].to_numpy(float)==1
w=np.asarray(design.weight,float)
yr=df["YEAR"].to_numpy()
out=[]
for y in sorted(set(yr)):
    m=yr==y
    fy=fars[fars["YEAR"]==y]
    rec=dict(year=y,crss_w_total=w[m].sum(),crss_w_fatal=w[m&isf].sum(),fars_n=len(fy),n_crss_fatal=int((m&isf).sum()))
    for v,lv in facs.items():
        ind=(df[v]==lv).to_numpy(float)
        sa=(w*ind)[m].sum()/w[m].sum()
        rec[v[:6]+"_all"]=sa; rec[v[:6]+"_fars"]=(fy[v]==lv).mean(); rec[v[:6]+"_mixed"]=(fy[v]==lv).mean()/sa
        sf=(w*ind)[m&isf].sum()/w[m&isf].sum(); rec[v[:6]+"_int"]=sf/sa
    out.append(rec)
o=pd.DataFrame(out); pd.set_option("display.width",250); print(o.round(3).to_string())
o.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/F01/years.csv",index=False)
# excl 2020
for v,lv in facs.items():
    ind=(df[v]==lv).to_numpy(float); m=yr!=2020
    sa=(w*ind)[m].sum()/w[m].sum(); f=fars[fars["YEAR"]!=2020]
    print("excl2020",v,round((f[v]==lv).mean()/sa,2))
# ped CRSS weighted crashes and implied fatality rate
ind=(df["crash_type"]=="pedestrian").to_numpy(float)
print("CRSS ped weighted crashes",(w*ind).sum(),"FARS ped fatal crashes",(fars.crash_type=="pedestrian").sum(),
      "implied rate",(fars.crash_type=="pedestrian").sum()/(w*ind).sum(),"CRSS internal rate",(w*ind*isf).sum()/(w*ind).sum())
print("pop total",w.sum(),"fars total",len(fars))
