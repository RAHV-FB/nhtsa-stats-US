import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    K=key+['VEH_NO']
    ve=load_table(src,'vehicle',columns=K+['VEH_SC1','VEH_SC2']+(['WEIGHT'] if src=='CRSS' else []))
    if src=='FARS': ve=ve.with_columns(pl.lit(1.0).alias('WEIGHT'))
    sf=load_table(src,'vehiclesf',columns=K+['VEHICLESF'])
    a=sf.group_by(K).agg((pl.col('VEHICLESF')==0).all().alias('none'),(pl.col('VEHICLESF').is_in([999])).any().alias('unk'),(pl.col('VEHICLESF')==32).any().alias('hc'),pl.len().alias('n'))
    j=ve.join(a,on=K,how='left')
    old=ve.filter(pl.col('YEAR')<=2019).with_columns(((pl.col('VEH_SC1')==0)&(pl.col('VEH_SC2')==0)).alias('none'),(pl.col('VEH_SC1').is_in([99])|pl.col('VEH_SC2').is_in([99])).alias('unk'),((pl.col('VEH_SC1')==32)|(pl.col('VEH_SC2')==32)).alias('hc'))
    new=j.filter(pl.col('YEAR')>=2020)
    f=lambda df: df.group_by('YEAR').agg([((pl.col(c).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias(c) for c in ['none','unk','hc']]).sort('YEAR').rows()
    print(src,'VEH_SC1/2 2016-19 (none, unk99, code32):',f(old))
    print(src,'vehiclesf 2020-24 (none, unk999, code32):',f(new),' vehicles w/o vehiclesf rows:',new['n'].null_count(),' max rows/veh',new['n'].max())
    print(src,'VEH_SC1 codes 2016-19 top:',ve.filter(pl.col('YEAR')<=2019).group_by('VEH_SC1').len().sort('len',descending=True).head(8).rows())
