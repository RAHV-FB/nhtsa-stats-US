"""X2-05. (a) F06 quasi-induced exposure excludes hit-and-run crashes. If fleeing drivers differ
by age/alcohol from stayers, the culpable pool is selected. Using FARS (vehicle HIT_RUN flag +
driver age): age mix and unknown-age share of drivers of vehicles that fled vs others.
(b) W05/F04 pedestrians in CRSS: unknown speed limit and hit-and-run shares by fatal status and
the fatal share by limit under bounding of unknown limits."""
import glob, numpy as np, pandas as pd
v=pd.concat([pd.read_parquet(f,columns=['ST_CASE','VEH_NO','HIT_RUN','YEAR']) if 'YEAR' in pd.read_parquet(f).columns else pd.read_parquet(f,columns=['ST_CASE','VEH_NO','HIT_RUN']).assign(YEAR=int(f[-12:-8])) for f in sorted(glob.glob('data/interim/FARS/vehicle/*.parquet'))])
pp=pd.concat([pd.read_parquet(f,columns=['ST_CASE','VEH_NO','PER_TYP','AGE']).assign(YEAR=int(f[-12:-8])) for f in sorted(glob.glob('data/interim/FARS/person/*.parquet'))])
pp=pp[pp.PER_TYP==1]
x=v.merge(pp,on=['YEAR','ST_CASE','VEH_NO'])
print('HIT_RUN values',x.HIT_RUN.value_counts().to_dict())
x['fled']=x.HIT_RUN.isin([1,2,3,4,5]) if x.HIT_RUN.max()<=5 else x.HIT_RUN>0
x['age_unknown']=x.AGE>=998
x['teen']=x.AGE.between(15,20); x['sen']=x.AGE>=75
for lab,g in x.groupby('fled'):
    k=g[~g.age_unknown]
    print(f'fled={lab}: n={len(g)} age_unknown={g.age_unknown.mean():.3f} teen|known={k.teen.mean():.3f} 75+|known={k.sen.mean():.3f}')
# (b) CRSS pedestrians
c=pd.read_parquet('data/processed/crss_crash.parquet',columns=['YEAR','WEIGHT','any_pedestrian','speed_limit','hit_and_run','fatal'])
c=c[c.any_pedestrian==1]
print('\nCRSS pedestrian crashes: n',len(c),'weighted',round(c.WEIGHT.sum()))
c['unk']=c.speed_limit.astype(str).str.contains('unk')
for f,g in c.groupby('fatal'):
    print(f'fatal={f}: unknown limit (w) {np.average(g.unk,weights=g.WEIGHT):.3f}; hit_and_run (w) {np.average(g.hit_and_run.fillna(0)==1,weights=g.WEIGHT):.3f}')
print(c.speed_limit.value_counts(dropna=False).to_dict())
w=c.groupby('speed_limit',dropna=False).apply(lambda g: pd.Series({'w':g.WEIGHT.sum(),'fatal_share':np.average(g.fatal,weights=g.WEIGHT)}))
print(w.round(4).to_string())
