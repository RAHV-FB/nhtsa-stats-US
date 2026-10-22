import sys; sys.path.insert(0,'.')
from util import *
p=load_table('FARS','person',columns=['YEAR','ST_CASE','PER_TYP','ALC_RES']).filter(pl.col('PER_TYP')==1)
c=p.group_by(['YEAR','ST_CASE']).agg((pl.col('ALC_RES').is_between(10,940)|(pl.col('ALC_RES')==998)).any().alias('pos10'),(pl.col('ALC_RES').is_between(1,940)|(pl.col('ALC_RES')==998)).any().alias('pos1'))
a=load_table('FARS','acc_aux',columns=['YEAR','ST_CASE','A_POSBAC']).join(c,on=['YEAR','ST_CASE'],how='left')
a=a.with_columns(pl.col('pos10').fill_null(False),pl.col('pos1').fill_null(False))
r=a.group_by(pl.col('YEAR')>=2020).agg((((pl.col('A_POSBAC')==1)==pl.col('pos10')).mean()).alias('agree_ge10'),(((pl.col('A_POSBAC')==1)==pl.col('pos1')).mean()).alias('agree_ge1'),(pl.col('pos1')&~pl.col('pos10')).sum().alias('n_low_only'),((pl.col('pos1')&~pl.col('pos10'))&(pl.col('A_POSBAC')==1)).sum().alias('low_only_coded1'))
print(r.rows())
