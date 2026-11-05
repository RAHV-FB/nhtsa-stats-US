"""Re-derive the DPC belt effectiveness (1 - RR) with the project's own estimator functions on the
eligible driver/RF pairs, then test TRANSPORT of the 65.8% to the other populations it is applied to
(rear seat, by period, body type, non-ejected, night/day) with 300-rep crash-cluster bootstraps.
Also implied survivor unbelted prevalence under the misreport scenarios.
Look at: 'ALL' row should be 0.6585; subgroup rows vs 0.66; rear-seat row is the key transport test."""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats.analysis import matched as m

cols=list(m.FARS_COLUMNS)+["ejected","night"]
df=pl.read_parquet("data/processed/fars_person.parquet",columns=cols).to_pandas()
df=m.add_ids(df)
elig,_=m.lpv_flow_and_eligible(df)
elig["belted"]=1-elig["unbelted"]
rng=np.random.default_rng(1)
def est(pairs,nb=300):
    if len(pairs)==0: return (np.nan,)*5
    c=m.cell_counts(pairs); lg=m.dpc_combined(c)
    if not np.isfinite(lg): return (np.nan,len(pairs),np.nan,np.nan,np.nan)
    b=m.dpc_combined(m.bootstrap_counts(pairs,nb,rng,cluster="crash_id"))
    b=b[np.isfinite(b)]
    dd,dp=m.death_counts(c)
    return (1-np.exp(lg), int(((pairs.k_d+pairs.k_p)>0).sum()), 1-np.exp(np.percentile(b,97.5)),1-np.exp(np.percentile(b,2.5)), min(dd.min(),dp.min()))
rows=[]
def add(name,pairs):
    e=est(pairs); rows.append(dict(sub=name,eff=e[0],n_death_pairs=e[1],lo=e[2],hi=e[3],min_deaths=e[4]))
drv=(elig.ptype=="driver")&(elig.SEAT_POS==11)
rf=(elig.ptype=="passenger")&(elig.SEAT_POS==13)
rear=(elig.seat=="second_row")
P=m.pair_frame(elig,"belted",drv,rf,carry=("YEAR","body","ejected","night","age"))
add("ALL driver/RF",P)
c=m.cell_counts(P); print("cells sum",c.sum(),"deaths drv/other",[x.tolist() for x in m.death_counts(c)])
add("2016-2019",P[P.YEAR_d<=2019]); add("2020-2024",P[P.YEAR_d>=2020])
for b in ["car","suv","pickup","van"]: add("body="+b,P[P.body_d==b])
add("neither ejected",P[(P.ejected_d==0)&(P.ejected_p==0)])
add("any ejected",P[(P.ejected_d==1)|(P.ejected_p==1)])
add("night",P[P.night_d==1]); add("day",P[P.night_d==0])
add("both aged 13-24",P[(P.age_d<25)&(P.age_p<25)]); add("both aged 25-64",P[(P.age_d.between(25,64))&(P.age_p.between(25,64))]); add("both aged 65+",P[(P.age_d>=65)&(P.age_p>=65)])
# rear seat: other = single second-row occupant
PR=m.pair_frame(elig,"belted",drv,rear,carry=("YEAR","body","ejected","age"))
add("REAR seat (driver + single rear 13+)",PR)
c=m.cell_counts(PR); print("rear cells deaths",[x.tolist() for x in m.death_counts(c)])
# rear subgroups: rear occupant age 13-24 / 25+
add("REAR, rear occ aged 13-24",PR[PR.age_p<25]); add("REAR, rear occ 25+",PR[PR.age_p>=25])
out=pd.DataFrame(rows); pd.set_option("display.width",200); print(out.round(3))
out.to_csv("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/W04/02_dpc_transport.csv",index=False)
# implied prevalence of unbelted among survivors in driver/RF pairs
cP=m.cell_counts(P)
surv_drv=cP[:,0,:,:].sum(); surv_unb=cP[0,0,:,:].sum()
print("driver survivors",surv_drv,"coded unbelted",surv_unb,"share",surv_unb/surv_drv)
for f in (0,.05,.1,.2):
    print("f",f,"implied true unbelted share of belted-coded+unbelted survivors",surv_unb/surv_drv+f*(1-surv_unb/surv_drv))
dd=P.loc[P.k_d==1,"x_d"]; print("share of driver deaths coded unbelted",1-dd.mean(), len(dd))
print("tipping f",m.dpc_tipping_point(cP))
