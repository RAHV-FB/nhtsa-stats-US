import sys; sys.path.insert(0,'.')
from util import *
cb=codebook()
for t,v in [('person','REST_USE'),('person','AIR_BAG'),('person','REST_MIS'),('vehicle','BODY_TYP'),('person','PER_TYP')]:
    df=load_table('CRSS',t,years=[2016,2017,2018],columns=[v])
    c19=set(cb.get(('CRSS',2019,t,v),{}).keys())
    out=[]
    for y in (2016,2017,2018):
        s=df.filter(pl.col('YEAR')==y)[v].cast(pl.Utf8)
        f=set(cb.get(('FARS',y,t,v),{}).keys())
        notin=s.filter(~s.is_in(list(c19))).value_counts().sort('count',descending=True).head(6).rows()
        out.append(f"{y}: in CRSS2019 {s.is_in(list(c19)).mean()*100:.2f}% in FARS{y} {s.is_in(list(f)).mean()*100:.2f}% missing-from-2019 codes {notin}")
    print(t,v); [print('   ',o) for o in out]
    # also label meaning differences for shared codes between FARS2016 and CRSS2019
    f16=cb.get(('FARS',2016,t,v),{}); 
    diff=[(k,f16[k][:30],cb[('CRSS',2019,t,v)][k][:30]) for k in f16 if k in c19 and norm(f16[k])!=norm(cb[('CRSS',2019,t,v)][k])]
    print('    same code, different label FARS2016 vs CRSS2019:',diff[:8])
