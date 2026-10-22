import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    K=key+['VEH_NO','PER_NO']
    pe=load_table(src,'person',columns=K+['PER_TYP','INJ_SEV']+(['WEIGHT'] if src=='CRSS' else ['STATE']))
    if src=='FARS': pe=pe.with_columns(pl.lit(1.0).alias('WEIGHT'))
    nmp=pe.filter(pl.col('PER_TYP').is_in([5,6,7,8,11,12,13]))  # ped/cyclist/other conveyance
    print('=====',src)
    for t,vars_ in [('nmcrash',['MTM_CRSH','NMCC']),('nmprior',['MPR_ACT','NMACTION']),('nmdistract',['MNMDSTRD','NMDISTRACT']),('nmimpair',['NMIMPAIR'])]:
        d=load_table(src,t,columns=K+vars_)
        d=d.with_columns(pl.coalesce([pl.col(v).cast(pl.Int64) for v in vars_]).alias('C')).drop(vars_)
        allnm=pe.filter(pl.col('VEH_NO')==0)
        cov=allnm.join(d.unique(subset=K).select(K).with_columns(pl.lit(1).alias('h')),on=K,how='left').group_by('YEAR').agg(pl.col('h').is_not_null().mean().round(4)).sort('YEAR')
        print(t,'coverage of VEH_NO=0 persons:',[r[1] for r in cov.rows()], ' rows/person max:', d.group_by(K).len()['len'].max())
        if t=='nmcrash':
            agg=d.group_by(K).agg((pl.col('C')==0).all().alias('none'),(pl.col('C')==99).all().alias('unk'),(pl.col('C')==2).any().alias('fty'),(pl.col('C')==9).any().alias('ww'),(pl.col('C')==12).any().alias('jay'),(pl.col('C')==19).any().alias('notvis'),(pl.col('C')==6).any().alias('inatt'))
            flags=['none','unk','fty','ww','jay','notvis','inatt']
        elif t=='nmprior':
            agg=d.group_by(K).agg((pl.col('C')==98).all().alias('NR'),(pl.col('C')==99).all().alias('unk'),(pl.col('C')==3).any().alias('crossing'))
            flags=['NR','unk','crossing']
        elif t=='nmdistract':
            agg=d.group_by(K).agg((pl.col('C')==96).all().alias('NR'),(pl.col('C')==99).all().alias('unk'),(pl.col('C')==0).all().alias('notdist'),(~pl.col('C').is_in([0,96,99])).any().alias('dist'))
            flags=['NR','unk','notdist','dist']
        else:
            agg=d.group_by(K).agg((pl.col('C')==98).all().alias('NR'),(pl.col('C')==99).all().alias('unk'),(pl.col('C')==0).all().alias('none'),(pl.col('C')==9).any().alias('alcdrug'))
            flags=['NR','unk','none','alcdrug']
        j=nmp.join(agg,on=K,how='inner')
        res=j.group_by('YEAR').agg([((pl.col(f).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias(f) for f in flags]+[pl.len().alias('n')]).sort('YEAR')
        with pl.Config(tbl_rows=20,tbl_cols=20,tbl_width_chars=200): print(res)
        # severity
        if src=='FARS':
            j=j.with_columns(pl.when(pl.col('INJ_SEV')==4).then(pl.lit('K')).otherwise(pl.lit('notK')).alias('sev'))
        else:
            j=j.with_columns(pl.col('INJ_SEV').replace_strict({0:'O',1:'C',2:'B',3:'A',4:'K',5:'U',6:'D',9:'9'},default='?').alias('sev'))
        res=j.filter(pl.col('YEAR')>=2020).group_by('sev').agg([((pl.col(f).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias(f) for f in flags]+[pl.len().alias('n')]).sort('sev')
        print('  by severity 2020-24:'); 
        with pl.Config(tbl_rows=20,tbl_cols=20,tbl_width_chars=200): print(res)
