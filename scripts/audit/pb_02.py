import sys; sys.path.insert(0,'.')
from util import *
cols=['PBPTYPE','PEDCTYPE','PEDCGP','BIKECTYPE','BIKECGP','PEDLOC','PEDPOS','BIKELOC','BIKEPOS','PBCWALK','PBSWALK','PBSZONE','PEDLEG','PEDSNR','MOTDIR','MOTMAN','PEDDIR','BIKEDIR']
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    pb=load_table(src,'pbtype',columns=key+['VEH_NO','PER_NO']+cols)
    pe=load_table(src,'person',columns=key+['VEH_NO','PER_NO','INJ_SEV']+(['WEIGHT'] if src=='CRSS' else []))
    j=pb.join(pe,on=key+['VEH_NO','PER_NO'],how='left')
    if src=='FARS': j=j.with_columns(pl.lit(1.0).alias('WEIGHT'))
    ped=j.filter(pl.col('PBPTYPE')==5); bik=j.filter(pl.col('PBPTYPE')==6)
    print('=====',src)
    # does ped get PEDCGP!=0 always; bike gets BIKECGP!=0?
    print('peds with PEDCGP==0:',(ped['PEDCGP']==0).sum(),'peds with BIKECGP!=0:',(ped['BIKECGP']!=0).sum(),' bikes PEDCGP!=0:',(bik['PEDCGP']!=0).sum(),' bikes BIKECGP==0:',(bik['BIKECGP']==0).sum())
    oth=j.filter(~pl.col('PBPTYPE').is_in([5,6]))
    print('other PBPTYPE (7,8,11-13): PEDCGP!=0 share',(oth['PEDCGP']!=0).mean(),' BIKECGP!=0 share',(oth['BIKECGP']!=0).mean())
    print(oth.group_by('PBPTYPE').agg((pl.col('PEDCGP')!=0).mean().alias('ped_typed'),(pl.col('BIKECGP')!=0).mean().alias('bike_typed')).sort('PBPTYPE'))
    w='WEIGHT' if src=='CRSS' else None
    print('PEDCGP among PBPTYPE 5 (%, weighted if CRSS)'); show(ped,'PEDCGP',src,'pbtype',w=w)
    print('BIKECGP among PBPTYPE 6'); show(bik,'BIKECGP',src,'pbtype',w=w)
    print('PEDLOC among peds'); show(ped,'PEDLOC',src,'pbtype',w=w)
    # severity dependence of unknown crash group 990, and PEDLOC 9
    for nm,df,var,unk in [('ped',ped,'PEDCGP',[990]),('ped',ped,'PEDLOC',[9]),('bike',bik,'BIKECGP',[990]),('bike',bik,'BIKELOC',[9]),('ped',ped,'PBCWALK',[9])]:
        g=df.with_columns(pl.col(var).is_in(unk).alias('u')).group_by('INJ_SEV').agg((pl.col('u')*pl.col('WEIGHT')).sum()/pl.col('WEIGHT').sum()*100, pl.len()).sort('INJ_SEV')
        print(nm,var,'unknown % by INJ_SEV', [(r[0],round(r[1],2),r[2]) for r in g.iter_rows()])
