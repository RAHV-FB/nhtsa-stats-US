import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    print('=====',src)
    K=key+['VEH_NO']
    dm=load_table(src,'damage',columns=K+['MDAREAS','DAMAGE']).with_columns(pl.coalesce([pl.col('MDAREAS').cast(pl.Int64),pl.col('DAMAGE').cast(pl.Int64)]).alias('D'))
    veh=load_table(src,'vehicle',columns=K+['DEFORMED','HIT_RUN']+(['WEIGHT','MAX_VSEV'] if src=='CRSS' else ['DEATHS']))
    pw=load_table(src,'parkwork',columns=K)
    agg=dm.group_by(K).agg(pl.len().alias('n'),(pl.col('D')==99).all().alias('unk'),(pl.col('D')==15).all().alias('nodmg'),(pl.col('D')==15).any().alias('any15'))
    print('damage vehicles in vehicle table:',agg.join(veh,on=K,how='semi').height,' in parkwork:',agg.join(pw,on=K,how='semi').height,' total:',agg.height)
    print('15 mixed with other codes:',agg.filter(pl.col('any15')&(pl.col('n')>1)).height,' 99 mixed:',dm.group_by(K).agg((pl.col('D')==99).any().alias('a'),pl.len()).filter(pl.col('a')&(pl.col('len')>1)).height)
    j=veh.join(agg,on=K,how='left')
    print('vehicles without damage rows:',j['n'].null_count(), 'share', round(j['n'].null_count()/j.height,4))
    if src=='FARS': j=j.with_columns(pl.lit(1.0).alias('WEIGHT'))
    r=j.group_by('YEAR').agg(((pl.col('unk').fill_null(False)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias('unk%'),((pl.col('nodmg').fill_null(False)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias('nodmg%'),(pl.col('n').is_null()*pl.col('WEIGHT')).sum().alias('w_noRows'),pl.col('n').mean().round(2).alias('mean_rows')).sort('YEAR')
    print(r.rows())
    # DEFORMED vs damage
    x=j.group_by(['DEFORMED']).agg(pl.len(),pl.col('nodmg').mean().round(3).alias('nodmg'),pl.col('unk').mean().round(3).alias('unk')).sort('DEFORMED')
    print('DEFORMED x damage:',x.rows())
    # unk by hit-run
    print('damage unknown by HIT_RUN:',j.group_by('HIT_RUN').agg(pl.col('unk').mean().round(3),pl.len()).sort('HIT_RUN').rows())
    if src=='CRSS':
        print('damage unknown by MAX_VSEV (w):',j.group_by('MAX_VSEV').agg(((pl.col('unk').fill_null(False)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2),pl.len()).sort('MAX_VSEV').rows())
    else:
        print('damage unknown by DEATHS>0:',j.group_by(pl.col('DEATHS')>0).agg(pl.col('unk').mean().round(4),pl.len()).rows())
