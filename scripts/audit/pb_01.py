import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    pb=load_table(src,'pbtype',columns=key+['VEH_NO','PER_NO','PBPTYPE','PBAGE','PBSEX','PEDCTYPE','PEDCGP','BIKECTYPE','BIKECGP'])
    pcols=key+['VEH_NO','PER_NO','PER_TYP','AGE','SEX','INJ_SEV']+(['WEIGHT'] if src=='CRSS' else [])
    pe=load_table(src,'person',columns=pcols)
    j=pb.join(pe,on=key+['VEH_NO','PER_NO'],how='left')
    print('=====',src,'pbtype rows',pb.height,'unmatched to person',j['PER_TYP'].null_count())
    print('PER_TYP of pbtype rows x year'); print(j.group_by(['YEAR','PER_TYP']).len().pivot(on='YEAR',index='PER_TYP',values='len',sort_columns=True).sort('PER_TYP'))
    # coverage: persons of nonmotorist types that have pbtype row
    nm=pe.filter(pl.col('PER_TYP').is_in([4,5,6,7,8,10,11,12,13,19]))
    nm=nm.join(pb.select(key+['VEH_NO','PER_NO']).with_columns(pl.lit(1).alias('has')),on=key+['VEH_NO','PER_NO'],how='left')
    print('coverage of non-motorists by pbtype (share with row) by PER_TYP')
    print(nm.group_by('PER_TYP').agg(pl.len(),pl.col('has').is_not_null().mean().round(4)).sort('PER_TYP'))
    print('VEH_NO of pbtype rows:',j.group_by(pl.col('VEH_NO')==0).len())
    # PBPTYPE vs PER_TYP
    print('PBPTYPE==PER_TYP:',(j['PBPTYPE']==j['PER_TYP']).mean(), ' PBAGE==AGE:',(j['PBAGE']==j['AGE']).mean(),' PBSEX==SEX:',(j['PBSEX']==j['SEX']).mean())
    print(j.filter(pl.col('PBPTYPE')!=pl.col('PER_TYP')).group_by(['PBPTYPE','PER_TYP','YEAR']).len().sort('len',descending=True).head(15))
    print(j.filter(pl.col('PBAGE')!=pl.col('AGE')).group_by(['YEAR']).len().sort('YEAR'))
