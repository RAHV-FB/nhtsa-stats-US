import sys; sys.path.insert(0,'.')
from util import *
c=load_table('CRSS','accident',columns=['YEAR','WEIGHT','PSU','URBANICITY'])
print('S17 weight CV, max/min, Kish deff by year:',c.group_by('YEAR').agg((pl.col('WEIGHT').std(ddof=0)/pl.col('WEIGHT').mean()).round(3).alias('cv'),(pl.col('WEIGHT').max()/pl.col('WEIGHT').min()).round(0).alias('mm'),(pl.len()*(pl.col('WEIGHT')**2).sum()/pl.col('WEIGHT').sum()**2).round(2).alias('deff')).sort('YEAR').rows())
u=c.group_by('PSU').agg(pl.col('URBANICITY').n_unique().alias('k'),pl.col('URBANICITY').first())
print('S18 PSUs',u.height,' non-constant',(u['k']>1).sum(),' urban(1)/rural(2):',u.group_by('URBANICITY').len().sort('URBANICITY').rows())
v=load_table('FARS','vehicle',columns=['YEAR','HIT_RUN'])
print('S19 FARS HIT_RUN yes %:',v.group_by('YEAR').agg(((pl.col('HIT_RUN')==1).mean()*100).round(2)).sort('YEAR').rows())
