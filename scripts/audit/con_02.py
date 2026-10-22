import sys; sys.path.insert(0,'.')
from util import *
K=['YEAR','ST_CASE','VEH_NO','PER_NO']
pe=load_table('FARS','person',columns=K+['PER_TYP','INJ_SEV','ALC_RES','HISPANIC','STATE'])
pa=load_table('FARS','per_aux',columns=K+['A_ALCTES','A_HISP','A_RCAT'])
d=pe.join(pa,on=K,how='left')
dr=d.filter(pl.col('PER_TYP')==1).with_columns((pl.col('INJ_SEV')==4).alias('killed'),pl.col('ALC_RES').is_between(0,940).alias('meas'),pl.col('A_ALCTES').is_in([1,2]).alias('aux12'),pl.col('A_ALCTES').is_in([3,4,5]).alias('aux345'))
print('drivers by killed: measured(0-940), A_ALCTES1/2, A_ALCTES3/4/5, n')
print(dr.group_by('killed').agg((pl.col('meas').mean()*100).round(2),(pl.col('aux12').mean()*100).round(2),(pl.col('aux345').mean()*100).round(2),pl.len(),pl.col('meas').sum().alias('n_meas')).rows())
print('INJ_SEV 6 (died prior) drivers:',dr.filter(pl.col('INJ_SEV')==6).height,' INJ_SEV 9 drivers:',dr.filter(pl.col('INJ_SEV')==9).height)
# survivors excluding INJ_SEV 9?
print('survivors INJ_SEV 0-3,5 only:',dr.filter(pl.col('INJ_SEV').is_in([0,1,2,3,5])).select((pl.col('meas').mean()*100).round(2),(pl.col('aux12').mean()*100).round(2),pl.len()).rows())
print('rows ALC_RES 998:',(dr['ALC_RES']==998).sum(), ' ALC_RES 941-994:',dr.filter(pl.col('ALC_RES').is_between(941,994)).height)
k24=dr.filter((pl.col('YEAR')==2024)&pl.col('killed'))
print('2024 killed drivers: 995 %',round((k24['ALC_RES']==995).mean()*100,2),' 995|999 %',round(k24['ALC_RES'].is_in([995,999]).mean()*100,2),' A_ALCTES=5 %',round((k24['A_ALCTES']==5).mean()*100,2))
f24=d.filter((pl.col('YEAR')==2024)&(pl.col('INJ_SEV')==4))
print('2024 fatalities: HISPANIC 99 %',round((f24['HISPANIC']==99).mean()*100,2),' 97 %',round((f24['HISPANIC']==97).mean()*100,2),' A_HISP=3 %',round((f24['A_HISP']==3).mean()*100,2),' A_RCAT=8 %',round((f24['A_RCAT']==8).mean()*100,2), ' n',f24.height)
