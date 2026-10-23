import sys; sys.path.insert(0,'.')
from util import *
K=['YEAR','ST_CASE','VEH_NO','PER_NO']
pe=load_table('FARS','person',columns=K+['PER_TYP','STATE'])
d=load_table('FARS','nmcrash',years=[2016,2017,2018,2019,2020,2024],columns=K+['MTM_CRSH','NMCC'])
d=d.with_columns(pl.coalesce([pl.col('MTM_CRSH').cast(pl.Int64),pl.col('NMCC').cast(pl.Int64)]).alias('C'))
a=d.group_by(K).agg((pl.col('C')==2).any().alias('fty'),(pl.col('C')==9).any().alias('ww'),(pl.col('C')==0).all().alias('none')).join(pe,on=K)
a=a.filter(pl.col('PER_TYP').is_in([5,6]))
s=a.group_by(['STATE','YEAR']).agg(pl.col('fty').mean().round(3),pl.col('ww').mean().round(3),pl.len()).sort(['STATE','YEAR'])
w=s.pivot(on='YEAR',index='STATE',values='fty',sort_columns=True)
n=a.group_by('STATE').len()
w=w.join(n,on='STATE').with_columns((pl.col('2018')-pl.col('2017')).alias('d1718'),(pl.col('2019')-pl.col('2018')).alias('d1819'))
with pl.Config(tbl_rows=60): print(w.sort('d1718',descending=True).head(12)); 
# contribution to national jump: count increase
c=a.group_by(['STATE','YEAR']).agg(pl.col('fty').sum()).pivot(on='YEAR',index='STATE',values='fty',sort_columns=True).with_columns((pl.col('2018')-pl.col('2017')).alias('inc'))
print('national fty count 2017,2018:',c['2017'].sum(),c['2018'].sum()); print(c.sort('inc',descending=True).head(8))
ww=s.pivot(on='YEAR',index='STATE',values='ww',sort_columns=True).with_columns((pl.col('2019')-pl.col('2018')).alias('d')).sort('d',descending=True)
print(ww.head(8))
c2=a.group_by(['STATE','YEAR']).agg(pl.col('ww').sum()).pivot(on='YEAR',index='STATE',values='ww',sort_columns=True).with_columns((pl.col('2019')-pl.col('2018')).alias('inc'))
print('national ww count 2018,2019:',c2['2018'].sum(),c2['2019'].sum()); print(c2.sort('inc',descending=True).head(6))
