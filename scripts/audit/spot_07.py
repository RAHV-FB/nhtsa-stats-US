import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    p=load_table(src,'person',columns=key+['VEH_NO','INJ_SEV']+(['WEIGHT'] if src=='CRSS' else []))
    if src=='FARS': p=p.with_columns(pl.lit(1.0).alias('WEIGHT'))
    v=load_table(src,'vehicle',columns=key+['VEH_NO','HIT_RUN'])
    print(src,'INJ_SEV 9 % (w):',p.group_by('YEAR').agg((((pl.col('INJ_SEV')==9)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2)).sort('YEAR').rows())
    j=p.filter(pl.col('INJ_SEV')==9).join(v,on=key+['VEH_NO'],how='left')
    print(src,'share of INJ_SEV 9 in HIT_RUN=1 vehicles (unw, w):',round((j['HIT_RUN']==1).mean()*100,1), round(((j['HIT_RUN']==1)*j['WEIGHT']).sum()/j['WEIGHT'].sum()*100,1))
