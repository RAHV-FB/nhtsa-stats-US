"""X2-03. Claims F07/P05/W04: within-vehicle (Evans double-pair) belt effect 65.8% lower risk; tipping
point ~21% survivor misreport. Published sensitivity only misclassifies SURVIVORS (belted<-unbelted).
Test (i) simplified DPC reproduction; (ii) the opposite error: a fraction g of KILLED occupants coded
'none' who were in truth belted (police inference from ejection/hindsight); (iii) both together;
(iv) unknown-restraint exclusion rates among killed vs survivors, and unbelted share of killed by
ejection. Look at: reduction vs g, survivor-misreport f; unknown shares by outcome."""
import numpy as np, pandas as pd
p=pd.read_parquet('data/processed/fars_person.parquet',columns=['YEAR','case_id','VEH_NO','ptype','seat','restraint','kabco','ejected','age','body'])
lpv=p.body.isin(['car','suv','pickup','van','light_truck_other','light_unknown_type'])
q=p[lpv&p.ptype.isin(['driver','passenger'])&p.kabco.between(0,4)&(p.age>=13)].copy()
q['killed']=(q.kabco==4).astype(int)
# unknown-restraint exclusion rates
fs=q[q.seat.isin(['front_left','front_other'])]
print('front-seat occupants: share restraint unknown/other by outcome')
print(fs.groupby('killed').restraint.value_counts(normalize=True).unstack().round(3).to_string())
k=fs[(fs.killed==1)&fs.restraint.isin(['belted','none'])]
print('killed front seat: share unbelted among known by ejected:'); print(k.groupby(k.ejected.fillna(-1)).restraint.apply(lambda s:(s=='none').mean()).round(3).to_dict(), k.ejected.fillna(-1).value_counts().to_dict())
fs_unk=fs[(fs.killed==1)]; print('killed unknown-restraint share by ejected',fs_unk.groupby(fs_unk.ejected.fillna(-1)).restraint.apply(lambda s:(s=='unknown').mean()).round(3).to_dict())
# build pairs
q['vid']=q.YEAR.astype(str)+'_'+q.case_id.astype(str)+'_'+q.VEH_NO.astype(str)
d=q[(q.seat=='front_left')&(q.ptype=='driver')&q.restraint.isin(['belted','none'])].drop_duplicates('vid',keep=False)
r=q[(q.seat=='front_other')&q.restraint.isin(['belted','none'])]
r=r.drop_duplicates('vid',keep=False)  # exactly one RF occupant
# require vehicle has exactly one front_other occupant overall
cnt=q[q.seat=='front_other'].groupby('vid').size(); r=r[r.vid.map(cnt)==1]
m=d.merge(r,on='vid',suffixes=('_d','_p'))
print('pairs',len(m),'with death',int(((m.killed_d+m.killed_p)>0).sum()))
def dpc(m,f=0.0,g=0.0):
    # f: share of 'belted' survivors truly unbelted; g: share of killed coded 'none' truly belted (expected counts)
    a=(m.restraint_d=='belted').astype(int).values; b=(m.restraint_p=='belted').astype(int).values
    kd=m.killed_d.values.astype(float); kp=m.killed_p.values.astype(float)
    # expected-count reclassification: weight vector over (a_true,b_true) per vehicle
    D_d=np.zeros((2,2)); D_p=np.zeros((2,2))
    for i in range(len(m)):
        pass
    # vectorised: each person has prob of true-belted
    def pb(stat,killed):
        # returns P(true belted)
        out=np.where(stat==1,np.where(killed==0,1-f,1.0),np.where(killed==1,g,0.0))
        return out
    pa=pb(a,kd); pbb=pb(b,kp)
    for ta in (0,1):
        for tb in (0,1):
            w=(pa if ta else 1-pa)*(pbb if tb else 1-pbb)
            D_d[ta,tb]=(w*kd).sum(); D_p[ta,tb]=(w*kp).sum()
    comps=[];wts=[]
    for bb in (0,1):
        R=(D_d[1,bb]/D_p[1,bb])/(D_d[0,bb]/D_p[0,bb]); comps.append(np.log(R)); wts.append(1/(1/D_d[1,bb]+1/D_p[1,bb]+1/D_d[0,bb]+1/D_p[0,bb]))
    for aa in (0,1):
        R=(D_p[aa,1]/D_d[aa,1])/(D_p[aa,0]/D_d[aa,0]); comps.append(np.log(R)); wts.append(1/(1/D_d[aa,1]+1/D_p[aa,1]+1/D_d[aa,0]+1/D_p[aa,0]))
    return 1-np.exp(np.average(comps,weights=wts))
print('\nreduction (1-R), simplified DPC; rows f=survivor misreport, cols g=killed none->truly belted')
gs=[0,0.02,0.05,0.10]
rows=[]
for f in (0,0.05,0.10,0.20):
    rows.append([f]+[round(dpc(m,f,g),3) for g in gs])
print(pd.DataFrame(rows,columns=['f']+[f'g={g}' for g in gs]).to_string(index=False))
