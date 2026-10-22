import sys; sys.path.insert(0,'.')
from util import *
a=load_table('FARS','accident',columns=['YEAR','LATITUDE','LATITUDENAME','LONGITUD','LONGITUDNAME'])
s=a.filter(pl.col('LATITUDE')>=77).group_by(['YEAR','LATITUDE','LATITUDENAME']).len().sort(['YEAR','LATITUDE'])
print(s.rows())
s2=a.filter(pl.col('LONGITUD').abs()>=700).group_by(['YEAR','LONGITUD','LONGITUDNAME']).len().sort(['YEAR','LONGITUD'])
print(s2.rows())
print('share special lat by year:',a.group_by('YEAR').agg(((pl.col('LATITUDE')>=77).mean()*100).round(2)).sort('YEAR').rows())
