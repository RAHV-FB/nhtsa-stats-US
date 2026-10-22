import sys; sys.path.insert(0,'.')
from util import *
cb=codebook()
spec={'pbtype':['PEDCTYPE','PEDCGP','BIKECTYPE','BIKECGP','PEDLOC','PEDPOS','PEDDIR','MOTDIR','MOTMAN','PEDLEG','PEDSNR','PBCWALK','PBSWALK','PBSZONE','BIKELOC','BIKEPOS','BIKEDIR'],
      'nmcrash':['MTM_CRSH','NMCC'],'nmprior':['MPR_ACT','NMACTION'],'nmimpair':['NMIMPAIR'],'safetyeq':['MSAFEQMT','NMHELMET','NMLIGHT','NMOTHPRE','NMOTHPRO','NMPROPAD','NMREFCLO'],
      'damage':['MDAREAS','DAMAGE'],'vevent':['SOE','AOI1','AOI2','VNUMBER2'],'vsoe':['SOE','AOI'],'cevent':['SOE','AOI1','AOI2']}
for t,vs in spec.items():
    df=load_table('CRSS',t,columns=vs)
    for v in vs:
        if df[v].null_count()==df.height: continue
        out=[]
        def lab(s,y,var):
            return set(cb.get((s,y,t,var),{}).keys())
        crss19=set().union(*[lab('CRSS',y,v) for y in range(2019,2025)])
        # also allow renamed var
        for y in (2016,2017,2018):
            d=df.filter((pl.col('YEAR')==y)&pl.col(v).is_not_null())
            if d.height==0: out.append(f"{y}:absent"); continue
            codes=d[v].cast(pl.Utf8)
            f=lab('FARS',y,v)
            in19=codes.is_in(list(crss19)).mean() if crss19 else None
            inF=codes.is_in(list(f)).mean() if f else None
            out.append(f"{y}: n={d.height} inCRSS19+={None if in19 is None else round(in19*100,3)} inFARS{y}={None if inF is None else round(inF*100,3)}")
        print(t,v,' | '.join(out))
