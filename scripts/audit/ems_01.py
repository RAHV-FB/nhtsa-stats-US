import sys; sys.path.insert(0,'.')
from util import *
cols=['YEAR','ST_CASE','STATE','HOUR','MINUTE','NOT_HOUR','NOT_MIN','ARR_HOUR','ARR_MIN','HOSP_HR','HOSP_MN','RUR_URB','LATITUDE','LONGITUD','FATALS','LATITUDENAME','LONGITUDNAME']
a=load_table('FARS','accident',columns=cols)
print(a.select(['LATITUDE','LONGITUD']).dtypes)
# lat/long special values
for c in ['LATITUDE','LONGITUD']:
    v=a.with_columns(pl.col(c).cast(pl.Float64).abs().alias('v'))
    thr=77 if c=='LATITUDE' else 700
    sp=v.filter(pl.col('v')>=thr).group_by(['YEAR',pl.col('v').round(4)]).len().sort(['YEAR','v'])
    print(c,'special values by year:',sp.pivot(on='v',index='YEAR',values='len',sort_columns=True).sort('YEAR').rows())
print('LATITUDENAME labels for specials:',a.filter(pl.col('LATITUDE').cast(pl.Float64)>=77).group_by(['LATITUDE','LATITUDENAME']).len().sort('len',descending=True).head(6).rows())
def known_t(h,m): return (pl.col(h)<=23)&(pl.col(m)<=59)
a=a.with_columns(known_t('NOT_HOUR','NOT_MIN').alias('notk'),known_t('ARR_HOUR','ARR_MIN').alias('arrk'),known_t('HOSP_HR','HOSP_MN').alias('hospk'),
  (pl.col('NOT_HOUR')==88).alias('not88'),(pl.col('ARR_HOUR')==88).alias('arr88'),(pl.col('HOSP_HR')==88).alias('hosp88'),
  ((pl.col('NOT_HOUR')==99)|(pl.col('NOT_MIN').is_in([98,99]))).alias('notU'),((pl.col('ARR_HOUR')==99)|(pl.col('ARR_MIN').is_in([98,99]))).alias('arrU'),((pl.col('HOSP_HR')==99)|(pl.col('HOSP_MN').is_in([98,99]))).alias('hospU'))
print(a.group_by('YEAR').agg([(pl.col(c).mean()*100).round(1) for c in ['notk','notU','not88','arrk','arrU','arr88','hospk','hospU','hosp88']]).sort('YEAR'))
print('min codes ARR_MIN 97:',a.group_by('YEAR').agg((pl.col('ARR_MIN')==97).sum()).sort('YEAR').rows())
# response time
ab=a.filter(pl.col('notk')&pl.col('arrk')&(pl.col('HOUR')<=23)&(pl.col('MINUTE')<=59))
ab=ab.with_columns(((pl.col('ARR_HOUR')*60+pl.col('ARR_MIN'))-(pl.col('NOT_HOUR')*60+pl.col('NOT_MIN'))).alias('d'),((pl.col('NOT_HOUR')*60+pl.col('NOT_MIN'))-(pl.col('HOUR')*60+pl.col('MINUTE'))).alias('dn'))
ab=ab.with_columns(pl.when(pl.col('d')<0).then(pl.col('d')+1440).otherwise(pl.col('d')).alias('resp'),pl.when(pl.col('dn')<-720).then(pl.col('dn')+1440).otherwise(pl.col('dn')).alias('notdelay'))
print('response min (arr-not), crossing midnight added; quantiles by RUR_URB:')
print(ab.group_by('RUR_URB').agg(pl.len(),pl.col('resp').median().alias('med'),pl.col('resp').quantile(0.9).alias('p90'),(pl.col('resp')>120).mean().round(4).alias('gt120'),(pl.col('d')<0).mean().round(4).alias('wrap')).sort('RUR_URB').rows())
print('notification before crash (dn in -720..-1):',(ab['notdelay']<0).mean(),' notification delay median',ab['notdelay'].median())
# unknown by rur_urb and state concentration
print('arr unknown by RUR_URB:',a.group_by('RUR_URB').agg((pl.col('arrU').mean()*100).round(2),pl.len()).sort('RUR_URB').rows())
st=a.group_by('STATE').agg((pl.col('arrU').mean()*100).round(1).alias('arrU'),(pl.col('notU').mean()*100).round(1).alias('notU'),(pl.col('hospU').mean()*100).round(1).alias('hospU'),pl.len()).sort('arrU',descending=True)
print(st.head(8).rows())
print('states with arrival unknown>50% in any year:',a.group_by(['STATE','YEAR']).agg(pl.col('arrU').mean()).filter(pl.col('arrU')>0.5).sort(['STATE','YEAR']).rows())
