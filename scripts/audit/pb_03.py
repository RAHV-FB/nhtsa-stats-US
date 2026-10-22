import sys; sys.path.insert(0,'.')
from util import *
pb=load_table('CRSS','pbtype',columns=['YEAR','CASENUM','VEH_NO','PER_NO','PBPTYPE','BIKECGP','BIKECTYPE']).filter(pl.col('PBPTYPE')==6)
print('unweighted BIKECGP 110 share and count:',pb.group_by('YEAR').agg(((pl.col('BIKECGP')==110).mean()*100).round(2),(pl.col('BIKECGP')==110).sum().alias('n110'),pl.len()).sort('YEAR').rows())
print(pb.filter(pl.col('BIKECGP')==110).group_by(['YEAR','BIKECTYPE']).len().pivot(on='YEAR',index='BIKECTYPE',values='len',sort_columns=True).sort('BIKECTYPE'))
lab=labels('FARS','pbtype','BIKECTYPE')
for c in ['111','112','113','114','119','121','122','129']:
    if c in lab: print(c,{k:v for k,v in list(lab[c].items())[:1]})
f=load_table('FARS','pbtype',columns=['YEAR','PBPTYPE','BIKECGP','BIKECTYPE']).filter(pl.col('PBPTYPE')==6)
print(f.filter(pl.col('BIKECGP')==110).group_by(['YEAR','BIKECTYPE']).len().pivot(on='YEAR',index='BIKECTYPE',values='len',sort_columns=True).sort('BIKECTYPE'))
