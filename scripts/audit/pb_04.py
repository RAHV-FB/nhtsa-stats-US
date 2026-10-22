import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    pb=load_table(src,'pbtype',columns=key+['VEH_NO','PER_NO','PBPTYPE','BIKECTYPE','PEDCTYPE'])
    b=pb.filter(pl.col('PBPTYPE')==6); p=pb.filter(pl.col('PBPTYPE')==5)
    print(src,'BIKECTYPE 231 % of cyclists:',b.group_by('YEAR').agg(((pl.col('BIKECTYPE')==231).mean()*100).round(2)).sort('YEAR').rows())
    print(src,'BIKECTYPE 23x (230 group) % :',b.group_by('YEAR').agg(((pl.col('BIKECTYPE')//10==23).mean()*100).round(2)).sort('YEAR').rows())
    print(src,'PEDCTYPE 341 count:',p.group_by('YEAR').agg((pl.col('PEDCTYPE')==341).sum()).sort('YEAR').rows())
