import sys; sys.path.insert(0,'.')
from util import *
cp=load_table('CRSS','person',columns=['YEAR','CASENUM']).unique()
ca=load_table('CRSS','accident',columns=['YEAR','CASENUM','MAX_SEV'])
nop=ca.join(cp,on=['YEAR','CASENUM'],how='anti')
print('S12 CRSS crashes w/o person rows:',nop.height,' MAX_SEV values:',nop.group_by('MAX_SEV').len().rows(),' total MAX_SEV=8:',int((ca['MAX_SEV']==8).sum()))
# S3 VTRAFCON
v=load_table('FARS','vehicle',columns=['YEAR','VTRAFCON','SPEEDREL','DR_PRES'])
print('S3 FARS VTRAFCON 97 / 0 % by year:',v.group_by('YEAR').agg(((pl.col('VTRAFCON')==97).mean()*100).round(2).alias('97'),((pl.col('VTRAFCON')==0).mean()*100).round(2).alias('0')).sort('YEAR').rows())
print('S14 FARS SPEEDREL=8 rows:',int((v['SPEEDREL']==8).sum()),' of which DR_PRES in (0,9):',int(v.filter(pl.col('SPEEDREL')==8)['DR_PRES'].is_in([0,9]).sum()),' DR_PRES in(0,9) total:',int(v['DR_PRES'].is_in([0,9]).sum()))
cv=load_table('CRSS','vehicle',columns=['YEAR','SPEEDREL','DR_PRES'])
print('S14 CRSS SPEEDREL=8 rows:',int((cv['SPEEDREL']==8).sum()),' DR_PRES in(0,9) total:',int(cv['DR_PRES'].is_in([0,9]).sum()),' agree:',((cv['SPEEDREL']==8)==cv['DR_PRES'].is_in([0,9])).mean())
# S4 REST_USE
p=load_table('FARS','person',columns=['YEAR','REST_USE'])
print('S4 FARS REST_USE 20 and 7 % by year:',p.group_by('YEAR').agg(((pl.col('REST_USE')==20).mean()*100).round(2).alias('20'),((pl.col('REST_USE')==7).mean()*100).round(2).alias('7')).sort('YEAR').rows())
# S15 vpicdecode coverage CRSS
for src,key in [('CRSS',['YEAR','CASENUM']),('FARS',['YEAR','ST_CASE'])]:
    ve=load_table(src,'vehicle',columns=key+['VEH_NO'])
    vp=load_table(src,'vpicdecode',columns=key+['VEH_NO']).with_columns(pl.lit(1).alias('h'))
    print('S15',src,'vpicdecode coverage of vehicles:',ve.join(vp,on=key+['VEH_NO'],how='left').group_by('YEAR').agg((pl.col('h').is_not_null().mean()*100).round(1)).sort('YEAR').rows())
