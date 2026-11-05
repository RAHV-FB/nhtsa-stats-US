"""X2-07. W08 (2019-21 rise: drunk driving +33.4%, invalid-licence crashes +44.0%, all deaths +18.9%).
Test whether ascertainment changes manufacture the differential: (a) deaths in crashes with a driver
at BAC>=.08 per year under MI (published basis), measured-only, and positivity among killed drivers
who were measured; test rate of killed drivers; (b) invalid-licence crash deaths vs share of drivers
with unknown licence status by year; invalid among known (stable?)."""
import numpy as np, pandas as pd
cols=['YEAR','case_id','drv_killed','drv_bac08_measured','L_STATUS']+[f'drv_bac08_mi_{k}' for k in range(1,11)]
d=pd.read_parquet('data/processed/fars_driver.parquet',columns=cols)
c=pd.read_parquet('data/processed/fars_crash.parquet',columns=['YEAR','case_id','n_killed'])
d=d.merge(c,on=['YEAR','case_id'],how='left'); d['cid']=d.YEAR.astype(str)+'_'+d.case_id.astype(str)
def deaths_any(flag):
    g=d.assign(f=flag.fillna(0).values).groupby('cid').agg(y=('YEAR','first'),a=('f','max'),nk=('n_killed','first'))
    return g[g.a>0].groupby('y').nk.sum()
mi=pd.concat([deaths_any(d[f'drv_bac08_mi_{k}']) for k in range(1,11)],axis=1).mean(axis=1)
meas=deaths_any((d.drv_bac08_measured==1).astype(float))
allk=d.groupby('YEAR').apply(lambda g:g.drop_duplicates('cid').n_killed.sum())
kd=d[d.drv_killed==1]
test=kd.groupby('YEAR').drv_bac08_measured.apply(lambda s:s.notna().mean())
pos=kd.groupby('YEAR').drv_bac08_measured.apply(lambda s:(s.dropna()==1).mean())
t=pd.DataFrame({'deaths_MI_drunk':mi,'deaths_measured_only':meas,'all_deaths':allk,'killed_drv_test_rate':test,'positivity_among_tested_killed':pos}).round(3)
print(t.to_string())
for y in (2021,2024):
    print(f'2019->{y}: MI {mi[y]/mi[2019]-1:+.3f} measured-only {meas[y]/meas[2019]-1:+.3f} all deaths {allk[y]/allk[2019]-1:+.3f}')
# licence
d['inv']=d.L_STATUS.isin([0,1,2,3,4]); d['unk']=~d.L_STATUS.isin([0,1,2,3,4,6])
g=d.groupby('cid').agg(y=('YEAR','first'),inv=('inv','max'),nk=('n_killed','first'),unk=('unk','max'))
dk=g[g.inv].groupby('y').nk.sum()
print('\ninvalid-licence crash deaths',dk.to_dict(),'\n 2019->2021 %+.3f'%(dk[2021]/dk[2019]-1))
print('driver licence unknown share by year',d.groupby('YEAR').unk.mean().round(3).to_dict())
print('driver invalid share (of known) by year',d[~d.unk].groupby('YEAR').inv.mean().round(3).to_dict())
print('drivers per death-year',d.groupby('YEAR').size().to_dict())
