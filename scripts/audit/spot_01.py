import sys; sys.path.insert(0,'.')
from util import *
# 1 FATALS
acc=load_table('FARS','accident',columns=['YEAR','ST_CASE','FATALS','WEATHER','STATE'])
pk=load_table('FARS','person',columns=['YEAR','ST_CASE','INJ_SEV']).filter(pl.col('INJ_SEV')==4).group_by(['YEAR','ST_CASE']).len()
j=acc.join(pk,on=['YEAR','ST_CASE'],how='left').with_columns(pl.col('len').fill_null(0))
#print('S1 crashes',acc.height,' sum FATALS',acc['FATALS'].sum(),' mismatches',(j['FATALS']!=j['len']).sum())
# 7 weather NR
w=acc.with_columns(pl.col('WEATHER').is_in([98,99]).alias('nr'),(pl.col('WEATHER')==98).alias('nr98'))
#print('S7 WEATHER 98/99 % by year:',w.group_by('YEAR').agg((pl.col('nr').mean()*100).round(2),(pl.col('nr98').mean()*100).round(2)).sort('YEAR').rows())
#print('S7 Virginia(51) WEATHER 98/99 %:',w.filter(pl.col('STATE')==51).group_by('YEAR').agg((pl.col('nr').mean()*100).round(1)).sort('YEAR').rows())
# 2 calibration
c=load_table('CRSS','accident',columns=['YEAR','MAXSEV_IM','MAX_SEV','WEIGHT','ALCOHOL','RELJCT1','TYP_INT'])
cal=c.filter(pl.col('MAXSEV_IM')==4).group_by('YEAR').agg(pl.col('WEIGHT').sum().round(0)).sort('YEAR').join(acc.group_by('YEAR').len(),on='YEAR')
#print('S2 CRSS weighted MAXSEV_IM=4 vs FARS crashes:',cal.rows())
# 6 ALCOHOL 9
print('S6 CRSS ALCOHOL=9 % (weighted, unweighted):',c.group_by('YEAR').agg((((pl.col('ALCOHOL')==9)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).alias('w'),((pl.col('ALCOHOL')==9).mean()*100).alias('u')).sort('YEAR').with_columns(pl.all().exclude('YEAR').round(2)).rows())
# 8 RELJCT1
print('S8 CRSS RELJCT1 {8,9} % (weighted, unweighted):',c.group_by('YEAR').agg((((pl.col('RELJCT1').is_in([8,9]))*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).alias('w'),(pl.col('RELJCT1').is_in([8,9]).mean()*100).alias('u')).sort('YEAR').with_columns(pl.all().exclude('YEAR').round(2)).rows())
# 12 cases without person rows
cp=load_table('CRSS','person',columns=['YEAR','CASENUM']).unique()
ca=load_table('CRSS','accident',columns=['YEAR','CASENUM','MAX_SEV'])
nop=ca.join(cp,on=['YEAR','CASENUM'],how='anti')
#print('S12 CRSS crashes w/o person rows:',nop.height,' MAX_SEV values:',nop.group_by('MAX_SEV').len().rows(),' total MAX_SEV=8:',(ca['MAX_SEV']==8).sum())
