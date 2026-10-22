import sys; sys.path.insert(0,'.')
from util import *
p=load_table('FARS','person',years=[2020,2021,2022,2023,2024],columns=['YEAR','STATE','INJ_SEV','HISPANIC','WORK_INJ'])
ia=p.filter((pl.col('STATE')==19)&(pl.col('INJ_SEV')==4))
print('S20 Iowa fatalities 2020-24:',ia.height,' HISPANIC==97 share:',(ia['HISPANIC']==97).mean(),' WORK_INJ==7:',(ia['WORK_INJ']==7).mean(), ' 97 outside Iowa:',p.filter((pl.col('HISPANIC')==97)&(pl.col('STATE')!=19)).height)
print('S20 per year:',ia.group_by('YEAR').len().sort('YEAR').rows())
