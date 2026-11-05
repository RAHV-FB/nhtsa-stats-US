"""X2-06. W05 (and F04 pedestrian RR 6.6): CRSS share of struck pedestrians who died, by posted limit
(2.2% at <=25 mph to 33.1% at 50-55). Unknown limit is 30% of non-fatal vs 11% of fatal pedestrian
crashes, so complete-case inflates the absolute fatal shares (outcome-dependent missingness) while
leaving odds ratios intact. Correct by weighting known records by 1/P(known | fatal status),
assuming limit is MAR within fatal status (a bounding assumption). Output: raw vs corrected shares,
by year too (unknown share trend)."""
import numpy as np, pandas as pd
c=pd.read_parquet('data/processed/crss_crash.parquet',columns=['YEAR','WEIGHT','any_pedestrian','speed_limit','fatal'])
c=c[(c.any_pedestrian==1)&c.fatal.notna()].copy()
c['known']=~c.speed_limit.isin(['unknown'])
pk=c.groupby('fatal').apply(lambda g:np.average(g.known,weights=g.WEIGHT)); print('P(limit known | fatal):',pk.round(3).to_dict())
k=c[c.known&(c.speed_limit!='none_nontrafficway')].copy()
k['w2']=k.WEIGHT/k.fatal.map(pk)
def tab(w):
    g=k.groupby('speed_limit').apply(lambda x:pd.Series({'raw_or_corrected':np.average(x.fatal,weights=x[w])}))
    return g
t=pd.DataFrame({'raw_fatal_share':tab('WEIGHT').raw_or_corrected,'corrected_fatal_share':tab('w2').raw_or_corrected}).round(4)
t['n']=k.groupby('speed_limit').size()
print(t.loc[['<=25','30-35','40-45','50-55','60-65','70+']].to_string())
r=lambda col:t.loc['50-55',col]/t.loc['<=25',col]
print('crude RR 50-55 vs <=25: raw %.1f corrected %.1f'%(r('raw_fatal_share'),r('corrected_fatal_share')))
print(c.groupby('YEAR').apply(lambda g:pd.Series({'unk_nonfatal':1-np.average(g[g.fatal==0].known,weights=g[g.fatal==0].WEIGHT),'unk_fatal':1-np.average(g[g.fatal==1].known,weights=g[g.fatal==1].WEIGHT)})).round(3).to_string())
