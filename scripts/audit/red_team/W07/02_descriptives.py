"""W07 attacks on selection/ageing: (a) CRSS weighted share of LPV occupants (all outcomes) in
18+ vehicles by year = exposure proxy for fleet ageing, vs FARS share (published 18.0%->30.5%);
(b) injury-severity mix by vehicle age (is a crash in an old car less likely to be reported when
minor?): weighted share killed / K-or-A / injured / uninjured; killed given K-or-A; (c) unknown
model year by outcome; (d) belt use and age mix by vehicle age band."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import person as P
df, design = P.load_occupants("killed")
pops = P.build_populations(df, design); L = pops["lpv"].df.copy(); del df
L["YEAR"]=L.YEAR.astype(int); w=L.WEIGHT
def sh(g,col,val): 
    return (g.WEIGHT*(g[col]==val)).sum()/g.WEIGHT.sum()
print("== (a) weighted share of ALL CRSS LPV occupants (8+) in 18+ vehicles, known age, by year")
for y,g in L.groupby("YEAR"):
    k=g[g.veh_age_band!="unknown"]
    k1=k[k.killed==1]
    print(y, "crss_all %.3f"%sh(k,"veh_age_band","18+"), " crss_killed %.3f (n=%d)"%(sh(k1,"veh_age_band","18+"),len(k1)), " crss_0-3 all %.3f killed %.3f"%(sh(k,"veh_age_band","0-3"),sh(k1,"veh_age_band","0-3")))
print("== (b) weighted severity by veh_age_band")
L["ka"]=L.killed_or_serious
rows=[]
for b,g in L.groupby("veh_age_band",observed=True):
    W=g.WEIGHT.sum(); ka=(g.WEIGHT*(g.ka==1)).sum(); k=(g.WEIGHT*(g.killed==1)).sum()
    inj=(g.WEIGHT*(g.get("injured",pd.Series(0,index=g.index))==1)).sum() if "injured" in g else np.nan
    rows.append(dict(band=b,n=len(g),w_ka_rate=ka/W,w_k_rate=k/W,killed_given_ka=k/ka,inj_rate=inj/W,
                     belted=sh(g,"restraint","belted"),unbelted=sh(g,"restraint","none"),unk_belt=sh(g,"restraint","unknown"),
                     rural=sh(g,"urbanicity","rural"),mean_age=(g.WEIGHT*g.age).sum()/W,age75p=(g.WEIGHT*(g.age>=75)).sum()/W,age_u25=(g.WEIGHT*(g.age<25)).sum()/W,
                     spd=sh(g,"speeding","yes"),alc=sh(g,"alcohol_im","yes"),mc_or_ht=0))
print(pd.DataFrame(rows).round(4).to_string())
print("== (c) unknown MOD_YEAR share of killed vs not (weighted)")
for o in [0,1]:
    g=L[L.killed==o]; print("killed",o,"unknown veh age share %.4f"%sh(g,"veh_age_band","unknown"))
print("== injured col present:", "injured" in L.columns, L["injured"].value_counts(dropna=False).to_dict() if "injured" in L else "")
