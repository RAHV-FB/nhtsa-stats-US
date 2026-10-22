import sys; sys.path.insert(0,'.')
from util import *
a=load_table('FARS','accident',columns=['YEAR','ST_CASE','HOUR','LGT_COND'])
p=load_table('FARS','person',columns=['YEAR','ST_CASE','INJ_SEV']).join(a,on=['YEAR','ST_CASE'])
print(p.group_by('INJ_SEV').agg(((pl.col('HOUR')==99).mean()*100).round(3).alias('hr'),((pl.col('LGT_COND').is_in([8,9])).mean()*100).round(3).alias('lgt'),pl.len()).sort('INJ_SEV').rows())
s=p.filter(pl.col('INJ_SEV').is_in([0,1,2,3]))
print('survivors INJ_SEV 0-3:',round((s['HOUR']==99).mean()*100,3), round(s['LGT_COND'].is_in([8,9]).mean()*100,3))
s=p.filter(pl.col('INJ_SEV').is_in([0,1,2,3,5]))
print('survivors INJ_SEV 0-3,5:',round((s['HOUR']==99).mean()*100,3), round(s['LGT_COND'].is_in([8,9]).mean()*100,3))
