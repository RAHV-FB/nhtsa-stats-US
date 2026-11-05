"""P04 claim: tox OR(BAC>=.08, drug)=1.23 vs police OR=5.0 (killed); 13.8 vs 1.84 (survivors);
testing 62% vs 19%.  Reproduces them, then tests whether the contrast is an artefact of
DIFFERENT POPULATIONS: recompute police-report OR on the identical drivers (tested for both,
determinate tox, police alcohol+drugs both known), and tox OR with the drug definition
restricted (no THC) and within-state.  Look at 'same-driver' rows."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import drugs as D

def orci(x, z):
    a=int((x&z).sum());b=int((x&~z).sum());c=int((~x&z).sum());d=int((~x&~z).sum())
    o,lo,hi=D._or2x2(a,b,c,d);return round(o,2),round(lo,2),round(hi,2),a+b+c+d

df=D.load_fars_drivers(); d=df[df.survival!="unknown"]
print("drug tested share:",d.groupby("survival").drug_tested.mean().round(3).to_dict())
for s in ("killed","survived"):
    g=d[(d.survival==s)&(d.drug_tested==1)&d.drv_drug_any.notna()&d.drv_bac08_measured.notna()]
    print(s,"TOX all tested:",orci(g.drv_bac08_measured==1,g.drv_drug_any==1))
    p=d[(d.survival==s)&d.drv_pr_drugs.notna()&d.drv_pr_alcohol.notna()]
    print(s,"POLICE published pop:",orci(p.drv_pr_alcohol==1,p.drv_pr_drugs==1))
    h=g[g.drv_pr_drugs.notna()&g.drv_pr_alcohol.notna()]
    print(s,"POLICE same drivers as tox:",orci(h.drv_pr_alcohol==1,h.drv_pr_drugs==1))
    print(s,"TOX same drivers (police known):",orci(h.drv_bac08_measured==1,h.drv_drug_any==1))
    # police alcohol vs tox drug / tox BAC vs police drugs (cross)
    print(s,"cross: police alc x tox drug:",orci(h.drv_pr_alcohol==1,h.drv_drug_any==1))
    print(s,"cross: tox BAC x police drugs:",orci(h.drv_bac08_measured==1,h.drv_pr_drugs==1))
    # drug def excluding cannabinoid
    nt=g[g.drv_drug_cannabinoid.notna()]
    z=(nt[[f"drv_drug_{c}" for c in D.DRUG_CLASSES if c!="cannabinoid"]].fillna(0).max(axis=1)==1)
    print(s,"TOX drug excluding cannabinoid:",orci(nt.drv_bac08_measured==1,z))
    # police-like: drug only when police-positive subset: tox OR among police-suspected
    for lab,m in (("police drugs yes",h.drv_pr_drugs==1),("police drugs no",h.drv_pr_drugs==0)):
        print(s,"TOX OR within",lab,":",orci(h[m].drv_bac08_measured==1,h[m].drv_drug_any==1))
    # within-state stratified (Mantel-Haenszel)
    num=den=0
    for st,gg in g.groupby("STATE"):
        x=gg.drv_bac08_measured==1;z=gg.drv_drug_any==1;n=len(gg)
        a=(x&z).sum();b=(x&~z).sum();c=(~x&z).sum();dd=(~x&~z).sum()
        num+=a*dd/n;den+=b*c/n
    print(s,"TOX MH OR across states:",round(num/den,3))
