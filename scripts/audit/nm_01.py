import sys; sys.path.insert(0,'.')
from util import *
NM=['NMHELMET','NMLIGHT','NMREFCLO','NMOTHPRE','NMPROPAD','NMOTHPRO']
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    K=key+['VEH_NO','PER_NO']
    pe=load_table(src,'person',columns=K+['PER_TYP','INJ_SEV']+(['WEIGHT'] if src=='CRSS' else []))
    if src=='FARS': pe=pe.with_columns(pl.lit(1.0).alias('WEIGHT'))
    nmp=pe.filter(pl.col('VEH_NO')==0)
    se=load_table(src,'safetyeq',columns=K+['MSAFEQMT']+NM)
    print('=====',src)
    # rows per person per year
    rp=se.group_by(['YEAR']+K[1:]).len().group_by('YEAR').agg(pl.len().alias('persons'),(pl.col('len')>1).sum().alias('multi')).sort('YEAR')
    print('safetyeq persons per year, persons with >1 row:',rp.rows())
    jj=se.unique(subset=K).join(nmp,on=K,how='left')
    print('safetyeq PER_TYP:',jj.group_by('PER_TYP').len().sort('PER_TYP').rows(),' unmatched:',jj['PER_TYP'].null_count())
    cov=nmp.join(se.unique(subset=K).select(K).with_columns(pl.lit(1).alias('h')),on=K,how='left').group_by('PER_TYP').agg(pl.col('h').is_not_null().mean().round(4),pl.len()).sort('PER_TYP')
    print('coverage of VEH_NO=0 persons by safetyeq:',cov.rows())
    # 2017+: NMHELMET among bicyclists
    s=se.filter(pl.col('YEAR')>=2017).join(nmp,on=K,how='inner')
    cyc=s.filter(pl.col('PER_TYP')==6)
    print('NMHELMET among cyclists (weighted % by year)'); show(cyc,'NMHELMET',src,'safetyeq',w='WEIGHT')
    ped=s.filter(pl.col('PER_TYP')==5)
    print('NMREFCLO among pedestrians'); show(ped,'NMREFCLO',src,'safetyeq',w='WEIGHT')
    # all six NR simultaneously?
    allnr=s.with_columns(pl.all_horizontal([pl.col(c)==8 for c in NM]).alias('allNR'),pl.any_horizontal([pl.col(c)==8 for c in NM]).alias('anyNR'))
    print('all six fields NR when any NR:', (allnr.filter('anyNR')['allNR'].mean()))
    g=cyc.with_columns(pl.col('NMHELMET').is_in([8,9]).alias('u')).group_by('INJ_SEV').agg(((pl.col('u')*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2),pl.len()).sort('INJ_SEV')
    print('cyclist helmet NR/unknown % by INJ_SEV:',g.rows())
    kn=cyc.filter(pl.col('NMHELMET').is_in([1,2])).with_columns((pl.col('NMHELMET')==2).alias('y')).group_by('INJ_SEV').agg(((pl.col('y')*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2),pl.len()).sort('INJ_SEV')
    print('cyclist helmet YES among known by INJ_SEV:',kn.rows())
    # 2016 MSAFEQMT among cyclists
    s16=se.filter(pl.col('YEAR')==2016).join(nmp,on=K,how='inner').filter(pl.col('PER_TYP')==6)
    print('2016 MSAFEQMT among cyclists rows:',s16.group_by('MSAFEQMT').agg(pl.col('WEIGHT').sum()).with_columns((pl.col('WEIGHT')/pl.col('WEIGHT').sum()*100).round(2)).sort('MSAFEQMT').rows())
    print('2016 cyclists with helmet code 2 (person share):', s16.group_by(K).agg((pl.col('MSAFEQMT')==2).any().alias('h'),pl.col('MSAFEQMT').is_in([8,9]).all().alias('u'),pl.col('WEIGHT').first()).select((pl.col('h')*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum(), (pl.col('u')*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()).rows())
