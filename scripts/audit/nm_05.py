import sys; sys.path.insert(0,'.')
from util import *
for src,key in [('FARS',['YEAR','ST_CASE']),('CRSS',['YEAR','CASENUM'])]:
    K=key+['VEH_NO','PER_NO']
    for t,vars_,spec in [('nmcrash',['MTM_CRSH','NMCC'],[0,99,92]),('nmprior',['MPR_ACT','NMACTION'],[98,99]),('nmdistract',['MNMDSTRD','NMDISTRACT'],[0,96,99]),('nmimpair',['NMIMPAIR'],[0,98,99])]:
        d=load_table(src,t,columns=K+vars_).with_columns(pl.coalesce([pl.col(v).cast(pl.Int64) for v in vars_]).alias('C'))
        g=d.group_by(K).agg(pl.len().alias('n'),*[(pl.col('C')==s).any().alias(f's{s}') for s in spec])
        mixed={s:int(g.filter(pl.col(f's{s}')&(pl.col('n')>1)).height) for s in spec}
        print(src,t,'persons',g.height,'multi-row',int((g['n']>1).sum()),'special code co-occurring with other rows:',mixed)
