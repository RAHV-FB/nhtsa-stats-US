"""X2-01. Claims: W02 ("39.4% of those killed in drunk-driving crashes were not the drunk driver"),
W01 (29.9% of deaths with a driver at BAC>=.08), W03 (prior-DWI 7.4% vs 1.8%).
Test: recompute victim-role share under alternative drunk-driver definitions and by testing
completeness: (a) NHTSA multiple imputation (10 implicates, as published); (b) measured BAC only;
(c) crashes where every driver has a measured BAC (no ascertainment gap). Also prior-DWI by
driver survival and record availability. Look at: share not drunk driver, % of drunk-driver crashes
where drunk driver died, and how it moves with testing completeness."""
import numpy as np, pandas as pd
cols=['YEAR','case_id','VEH_NO','drv_killed','drv_bac08_measured','PREV_DWI','L_STATUS','has_driver_record']+[f'drv_bac08_mi_{k}' for k in range(1,11)]
d=pd.read_parquet('data/processed/fars_driver.parquet',columns=cols)
c=pd.read_parquet('data/processed/fars_crash.parquet',columns=['YEAR','case_id','n_killed'])
d=d.merge(c,on=['YEAR','case_id'],how='left')
d['kd']=d.drv_killed.fillna(0)
d['cid']=d.YEAR.astype(str)+'_'+d.case_id.astype(str)
def role(flagcol):
    f=d[flagcol].fillna(0)
    g=pd.DataFrame({'cid':d.cid,'any':f,'killeddrunk':f*d.kd,'n_killed':d.n_killed})
    s=g.groupby('cid').agg(any=('any','max'),kd=('killeddrunk','sum'),nk=('n_killed','first'))
    s=s[s['any']>0]
    return s
res=[]
mi=[]
for k in range(1,11):
    s=role(f'drv_bac08_mi_{k}'); mi.append((s.nk.sum(),s.kd.sum(),len(s),(s.kd>0).mean()))
mi=np.mean(mi,axis=0)
res.append(('MI (10 implicates)',mi[2],mi[0],1-mi[1]/mi[0],mi[3]))
d['meas1']=(d.drv_bac08_measured==1).astype(float)
s=role('meas1'); res.append(('measured BAC>=.08 only',len(s),s.nk.sum(),1-s.kd.sum()/s.nk.sum(),(s.kd>0).mean()))
# all drivers measured
tested=d.groupby('cid').drv_bac08_measured.apply(lambda x:x.notna().all())
full=set(tested[tested].index)
d2=d[d.cid.isin(full)]
g=d2.groupby('cid').agg(any=('meas1','max'),kd=('kd',lambda x:0),nk=('n_killed','first'))
d2=d2.assign(kdd=d2.kd*d2.meas1)
g=d2.groupby('cid').agg(any=('meas1','max'),kd=('kdd','sum'),nk=('n_killed','first'))
g=g[g['any']>0]
res.append(('measured, all drivers tested',len(g),g.nk.sum(),1-g.kd.sum()/g.nk.sum(),(g.kd>0).mean()))
# multi-vehicle only, all tested
mv=d.groupby('cid').VEH_NO.transform('count')>1
d3=d[mv&d.cid.isin(full)].assign(kdd=lambda x:x.kd*x.meas1)
g=d3.groupby('cid').agg(any=('meas1','max'),kd=('kdd','sum'),nk=('n_killed','first')); g=g[g['any']>0]
res.append(('measured, multi-vehicle, all tested',len(g),g.nk.sum(),1-g.kd.sum()/g.nk.sum(),(g.kd>0).mean()))
# share of crashes with >=1 driver untested
print('share of crashes with every driver measured:',len(full)/d.cid.nunique())
print(pd.DataFrame(res,columns=['definition','crashes','deaths','share_killed_not_drunk_driver','pct_crashes_drunk_driver_died']).to_string())
# W03 prior DWI
d['dwi_known']=~d.PREV_DWI.isin([99,998])
d['dwi']=(d.PREV_DWI.between(1,5)).astype(float)
yr=d[d.YEAR>=2016]
for lab,m in [('BAC>=.08 measured',yr.drv_bac08_measured==1),('BAC 0 measured',yr.drv_bac08_measured==0)]:
    for kl,km in [('killed',yr.drv_killed==1),('survived',yr.drv_killed==0)]:
        x=yr[m&km]
        print(f'{lab:20s} {kl:9s} n={len(x):6d} dwi_unknown={1-x.dwi_known.mean():.3f} priorDWI|known={x[x.dwi_known].dwi.mean():.4f} nolicence={(x.L_STATUS.isin([0,1,2,3,4,7])).mean():.3f}')

# imputed-vs-measured drunk drivers: prior DWI among known record
yr=d[d.dwi_known]
meas=yr[yr.drv_bac08_measured==1]
print('measured BAC>=.08 n',len(meas),'priorDWI',meas.dwi.mean())
for k in (1,2,3):
    x=yr[(yr[f'drv_bac08_mi_{k}']==1)]
    xi=x[x.drv_bac08_measured.isna()]
    print(f'MI{k}: all drunk n={len(x)} priorDWI={x.dwi.mean():.4f}; imputed-only (untested) n={len(xi)} priorDWI={xi.dwi.mean():.4f}')
    z=yr[(yr[f'drv_bac08_mi_{k}']==0)]
    print(f'   MI{k} not-drunk priorDWI={z.dwi.mean():.4f}; measured-zero {yr[yr.drv_bac08_measured==0].dwi.mean():.4f}; imputed-zero(untested) {z[z.drv_bac08_measured.isna()].dwi.mean():.4f}')
