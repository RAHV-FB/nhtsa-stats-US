import sys; sys.path.insert(0,'.')
from util import *
sevmap={0:'O',1:'C',2:'B',3:'A',4:'K',5:'U',6:'D',8:'NoP',9:'9'}
for src,key in [('CRSS',['YEAR','CASENUM']),('FARS',['YEAR','ST_CASE'])]:
    vcols=key+['VEH_NO','TRAV_SP','HIT_RUN']+(['WEIGHT','MAX_VSEV'] if src=='CRSS' else ['DEATHS'])
    ve=load_table(src,'vehicle',columns=vcols)
    if src=='FARS': ve=ve.with_columns(pl.lit(1.0).alias('WEIGHT'))
    dr=load_table(src,'person',columns=key+['VEH_NO','PER_TYP','INJ_SEV']).filter(pl.col('PER_TYP')==1).select(key+['VEH_NO','INJ_SEV'])
    v=ve.join(dr,on=key+['VEH_NO'],how='left').with_columns(
        pl.col('TRAV_SP').is_in([998,999]).alias('miss'),
        (pl.col('TRAV_SP').is_between(1,151)|(pl.col('TRAV_SP')==997)).alias('known_excl0'),
        (pl.col('TRAV_SP')==0).alias('zero'))
    def r(df,by,flag):
        return df.group_by(by).agg(((pl.col(flag).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(1).alias(flag),pl.len().alias('n')).sort(by)
    print('=====',src)
    print('overall by year: miss%, known(1-151,997)%, zero%')
    print(v.group_by('YEAR').agg([((pl.col(f).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(1).alias(f) for f in ['miss','known_excl0','zero']]).sort('YEAR').rows())
    vv=v.filter(pl.col('INJ_SEV').is_not_null())
    vv=vv.with_columns(pl.col('INJ_SEV').replace_strict(sevmap,default='?').alias('dsev'))
    for f in ['miss','known_excl0','zero']:
        print(f,'by driver INJ_SEV (drivers only):',[(a,b) for a,b,c in r(vv,'dsev',f).rows()])
    if src=='CRSS':
        v2=v.with_columns(pl.col('MAX_VSEV').replace_strict(sevmap,default='?').alias('vsev'))
        for f in ['miss','zero']:
            print(f,'by vehicle MAX_VSEV (all vehicles):',[(a,b) for a,b,c in r(v2,'vsev',f).rows()])
    else:
        for f in ['miss','zero','known_excl0']:
            print(f,'by DEATHS>0 (all vehicles):',r(v.with_columns((pl.col('DEATHS')>0).alias('d')),'d',f).rows())
        for f in ['miss','known_excl0']:
            print(f,'drivers killed vs not:',r(vv.with_columns((pl.col('INJ_SEV')==4).alias('k')),'k',f).rows())
