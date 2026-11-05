"""X2-04. (a) Coding break: F01/F02 'Intersection x0.58' mixes a CRSS denominator with a FARS numerator;
CRSS junction coding breaks 2017-2021 (unknown 45% of fatal CRSS crashes in 2019 per
measurement/fars_crss_fatal_composition). Recompute the CRSS-all intersection share by year
(incl. unknown level) and the ratio using only unaffected years (2016, 2022-24) and using
known-only shares. (b) W01/P01: how much of FARS 'speeding-related' deaths sit in 'too fast for
conditions' / unspecified (the type with no detectable excess in F03)? Output: shares by year and
death splits."""
import numpy as np, pandas as pd
cc=pd.read_parquet('data/processed/crss_crash.parquet',columns=['YEAR','WEIGHT','junction','fatal','speeding_type'])
fc=pd.read_parquet('data/processed/fars_crash.parquet',columns=['YEAR','junction','speeding_type','n_killed'])
print('junction levels crss',cc.junction.value_counts(dropna=False).to_dict()); print('fars',fc.junction.value_counts(dropna=False).to_dict())
def sh(df,w=None,col='junction'):
    w=df[w] if w else pd.Series(1.0,index=df.index)
    return (w.groupby(df[col]).sum()/w.sum())
rows=[]
for y in sorted(cc.YEAR.unique()):
    a=cc[cc.YEAR==y]; f=fc[fc.YEAR==y]
    sa=sh(a,'WEIGHT'); sf=sh(f)
    inter=[l for l in sa.index if 'inter' in str(l).lower()]
    unk=[l for l in sa.index if 'unk' in str(l).lower()]
    ia=sa[inter].sum(); iu=sa[unk].sum(); fi=sf[[l for l in sf.index if 'inter' in str(l).lower()]].sum(); fu=sf[[l for l in sf.index if 'unk' in str(l).lower()]].sum()
    rows.append((y,ia,iu,fi,fu,fi/ia,(fi/(1-fu))/(ia/(1-iu))))
t=pd.DataFrame(rows,columns=['YEAR','crss_all_inter','crss_all_unknown','fars_fatal_inter','fars_unknown','ratio_raw','ratio_known_only']).round(3)
print(t.to_string(index=False))
ok=cc.YEAR.isin([2016,2022,2023,2024]); okf=fc.YEAR.isin([2016,2022,2023,2024])
for lab,a,f in [('all years',cc,fc),('unaffected years 2016+2022-24',cc[ok],fc[okf])]:
    sa=sh(a,'WEIGHT'); sf=sh(f)
    ia=sa[[l for l in sa.index if 'inter' in str(l).lower()]].sum(); fi=sf[[l for l in sf.index if 'inter' in str(l).lower()]].sum()
    print(lab,'CRSS-all intersection share %.3f FARS fatal %.3f ratio %.3f'%(ia,fi,fi/ia))
# speeding types among FARS deaths
fc['d']=fc.n_killed
print('\nFARS deaths by speeding_type:'); s=fc.groupby('speeding_type',dropna=False).d.sum(); print((s/s.sum()).round(3).to_dict(), s.sum())
