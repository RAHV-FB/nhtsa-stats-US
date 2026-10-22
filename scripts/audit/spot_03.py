import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    K=key+['VEH_NO']
    d=load_table(src,'distract',columns=K+['MDRDSTRD','DRDISTRACT']).with_columns(pl.coalesce([pl.col('MDRDSTRD').cast(pl.Int64),pl.col('DRDISTRACT').cast(pl.Int64)]).alias('C'))
    ve=load_table(src,'vehicle',columns=K+(['WEIGHT'] if src=='CRSS' else ['STATE']))
    if src=='FARS': ve=ve.with_columns(pl.lit(1.0).alias('WEIGHT'))
    a=d.group_by(K).agg((pl.col('C')==96).all().alias('nr'))
    j=ve.join(a,on=K,how='left')
    print('S5',src,'distraction NR % of vehicles (w):',j.group_by('YEAR').agg(((pl.col('nr').cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(1)).sort('YEAR').rows())
    if src=='FARS':
        dp=load_table(src,'person',columns=K+['PER_TYP']).filter(pl.col('PER_TYP')==1).select(K)
        jj=j.join(dp,on=K,how='semi')
        print('S5 FARS drivers-only NR %:',jj.group_by('YEAR').agg((pl.col('nr').mean()*100).round(1)).sort('YEAR').rows())
        print('S5 Georgia(13) NR %:',jj.filter(pl.col('STATE')==13).group_by('YEAR').agg((pl.col('nr').mean()*100).round(1)).sort('YEAR').rows())
# crash hour unknown killed vs survivors
a=load_table('FARS','accident',columns=['YEAR','ST_CASE','HOUR'])
p=load_table('FARS','person',columns=['YEAR','ST_CASE','INJ_SEV']).join(a,on=['YEAR','ST_CASE'])
print('S16 FARS HOUR=99 % killed vs not:',p.group_by(pl.col('INJ_SEV')==4).agg((pl.col('HOUR')==99).mean()*100).rows())
