import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    print('=====',src)
    ce=load_table(src,'cevent',columns=key+['EVENTNUM','VNUMBER1','AOI1','SOE','VNUMBER2','AOI2'])
    acc=load_table(src,'accident',columns=key+['HARM_EV','VE_TOTAL'])
    # every crash has cevent rows?
    nce=ce.group_by(key).agg(pl.len().alias('nev'),pl.col('EVENTNUM').min().alias('mn'),pl.col('EVENTNUM').max().alias('mx'))
    j=acc.join(nce,on=key,how='left')
    print('crashes without cevent rows:',j['nev'].null_count(),' EVENTNUM contiguous 1..n:',((j['mn']==1)&(j['mx']==j['nev'])).mean())
    print('events per crash dist (share):',j.group_by(pl.col('nev').clip(1,6)).len().sort('nev').with_columns((pl.col('len')/pl.col('len').sum()).round(4)).rows())
    first=ce.filter(pl.col('EVENTNUM')==1).select(key+['SOE'])
    j=acc.join(first,on=key,how='left')
    print('HARM_EV == SOE of EVENTNUM 1:',(j['HARM_EV']==j['SOE']).mean())
    # codes that are never HARM_EV but appear as SOE -> candidate non-harmful
    hv=set(acc['HARM_EV'].unique().to_list())
    soe=ce.group_by('SOE').len()
    nh=sorted(set(soe['SOE'].to_list())-hv)
    lab=labels(src if src=='FARS' else 'FARS','cevent','SOE'); lab={k:v[max(v)] for k,v in lab.items()}
    print('SOE codes never used as HARM_EV:',[(c,lab.get(str(c),'?')[:35]) for c in nh])
    ce2=ce.filter(~pl.col('SOE').is_in(nh)).group_by(key).agg(pl.col('SOE').sort_by('EVENTNUM').first().alias('fh'))
    j=acc.join(ce2,on=key,how='left')
    agree=(j['HARM_EV']==j['fh'])
    print('HARM_EV == first harmful SOE in cevent:',agree.mean(),' mism n:',(~agree).sum(),' null fh:',j['fh'].null_count())
    print(j.filter(pl.col('HARM_EV')!=pl.col('fh')).group_by(['HARM_EV','fh']).len().sort('len',descending=True).head(8).rows())
    # vevent vs vsoe identical?
    ve=load_table(src,'vevent',columns=key+['VEH_NO','EVENTNUM','VEVENTNUM','SOE','AOI1','AOI2','VNUMBER1','VNUMBER2'])
    vs=load_table(src,'vsoe',columns=key+['VEH_NO','VEVENTNUM','SOE','AOI'])
    m=ve.join(vs,on=key+['VEH_NO','VEVENTNUM'],how='full',coalesce=True,suffix='_s')
    print('vevent-vsoe full join rows',m.height,'ve rows',ve.height,'SOE equal',(m['SOE']==m['SOE_s']).mean())
    # AOI in vsoe = AOI1 if VNUMBER1==VEH_NO else AOI2
    m=m.with_columns(pl.when(pl.col('VNUMBER1')==pl.col('VEH_NO')).then(pl.col('AOI1')).otherwise(pl.col('AOI2')).alias('aoi_d'))
    print('vsoe.AOI == own-vehicle AOI from vevent:',(m['aoi_d']==m['AOI']).mean())
    # cevent rows all present in vevent?
    vce=ve.select(key+['EVENTNUM']).unique()
    print('cevent events that appear in vevent:', ce.join(vce,on=key+['EVENTNUM'],how='semi').height/ce.height)
    # M_HARM in vsoe for that vehicle
    veh=load_table(src,'vehicle',columns=key+['VEH_NO','M_HARM'])
    has=vs.join(veh,on=key+['VEH_NO']).filter(pl.col('SOE')==pl.col('M_HARM')).select(key+['VEH_NO']).unique()
    print('vehicles whose M_HARM appears in own vsoe:',has.height/veh.height,' vehicles with no vsoe rows:',veh.join(vs.select(key+['VEH_NO']).unique(),on=key+['VEH_NO'],how='anti').height)
