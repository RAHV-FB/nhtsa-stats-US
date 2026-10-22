import sys; sys.path.insert(0,'.')
from util import *
NM=['NMHELMET','NMLIGHT','NMREFCLO','NMOTHPRE','NMPROPAD','NMOTHPRO']
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    K=key+['VEH_NO','PER_NO']
    pe=load_table(src,'person',years=[2016,2017,2018],columns=K+['PER_TYP']+(['WEIGHT'] if src=='CRSS' else []))
    if src=='FARS': pe=pe.with_columns(pl.lit(1.0).alias('WEIGHT'))
    se=load_table(src,'safetyeq',years=[2016,2017,2018],columns=K+['MSAFEQMT']+NM)
    a16=se.filter(pl.col('YEAR')==2016).group_by(K).agg(pl.col('MSAFEQMT').is_in([8,9]).all().alias('allunk'),(pl.col('MSAFEQMT')==2).any().alias('helmet'))
    a17=se.filter(pl.col('YEAR')>=2017).with_columns(pl.all_horizontal([pl.col(c).is_in([8,9]) for c in NM]).alias('allunk'),(pl.col('NMHELMET')==2).alias('helmet')).select(K+['allunk','helmet'])
    a=pl.concat([a16,a17]).join(pe,on=K)
    for pt,nm in [(5,'ped'),(6,'cyc')]:
        r=a.filter(pl.col('PER_TYP')==pt).group_by('YEAR').agg(((pl.col('allunk').cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(1).alias('allunk_w'),(pl.col('allunk').mean()*100).round(1).alias('allunk_u'),((pl.col('helmet').cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(1).alias('helmet_w'),pl.len()).sort('YEAR')
        print(src,nm,r.rows())
