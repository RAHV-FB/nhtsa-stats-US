import sys; sys.path.insert(0,'.')
from util import *
K=['YEAR','CASENUM','VEH_NO','PER_NO']
pe=load_table('CRSS','person',columns=K+['PER_TYP','INJ_SEV','INJSEV_IM','REST_USE','HELM_USE','WEIGHT'])
ve=load_table('CRSS','vehicle',columns=['YEAR','CASENUM','VEH_NO','BODY_TYP'])
pa=load_table('CRSS','per_aux',columns=K+['A_RESTUSE','A_HELMUSE','A_PERINJ'])
d=pe.join(ve,on=['YEAR','CASENUM','VEH_NO'],how='left').join(pa,on=K,how='left')
sevmap={0:'O',1:'C',2:'B',3:'A',4:'K',5:'U',6:'D',9:'9'}
d=d.with_columns(pl.col('INJ_SEV').replace_strict(sevmap,default='?').alias('obs'),pl.col('INJSEV_IM').replace_strict(sevmap,default='?').alias('imp'))
def rate(df,flag,by):
    return df.group_by(by).agg(((pl.col(flag).cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2).alias('pct'),pl.len().alias('n')).sort(by)
lpv=d.filter(pl.col('PER_TYP').is_in([1,2,9])&pl.col('BODY_TYP').is_between(1,49)).with_columns(pl.col('REST_USE').is_in([98,99]).alias('u'))
auxu=d.filter(pl.col('PER_TYP').is_in([1,2,9])&~pl.col('BODY_TYP').is_between(80,84)&~pl.col('BODY_TYP').is_between(87,89)).with_columns((pl.col('A_RESTUSE')==3).alias('u'))
print('A) person-domain def (LPV, REST_USE 98/99) by observed INJ_SEV:',rate(lpv,'u','obs').rows())
print('B) same universe by imputed INJSEV_IM:',rate(lpv,'u','imp').rows())
print('C) aux-domain def (A_RESTUSE=3, non-MC occupants) by observed INJ_SEV:',rate(auxu,'u','obs').rows())
print('D) aux-domain def by INJSEV_IM:',rate(auxu,'u','imp').rows())
print('E) aux-domain def by A_PERINJ:',rate(auxu,'u','A_PERINJ').rows())
# body type composition of aux universe not in LPV
x=auxu.with_columns(pl.col('BODY_TYP').is_between(1,49).alias('lpv'))
print('aux universe: share LPV (w) and unknown rate LPV vs non-LPV:',x.group_by('lpv').agg((pl.col('WEIGHT').sum()).alias('w'),((pl.col('u').cast(pl.Float64)*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100).round(2)).rows())
# check if A_RESTUSE=3 equals REST_USE in {98,99} for LPV 2020+
y=lpv.filter(pl.col('YEAR')>=2020)
print('LPV 2020+: A_RESTUSE==3 vs REST_USE 98/99 agreement:',((y['A_RESTUSE']==3)==y['u']).mean())
mc=d.filter(pl.col('PER_TYP').is_in([1,2,9])&pl.col('BODY_TYP').is_between(80,89))
mc=mc.with_columns(pl.when(pl.col('YEAR')<=2018).then(pl.col('REST_USE').is_in([29,97,98,99])).otherwise(pl.col('HELM_USE').is_in([97,98,99])).alias('u'))
print('helmet unknown (person def) by obs:',rate(mc,'u','obs').rows())
print('helmet unknown (person def) by imp:',rate(mc,'u','imp').rows())
mc2=mc.with_columns((pl.col('A_HELMUSE')==3).alias('ua'))
print('A_HELMUSE=3 by obs:',rate(mc2,'ua','obs').rows())
print('A_HELMUSE=3 by imp:',rate(mc2,'ua','imp').rows())
