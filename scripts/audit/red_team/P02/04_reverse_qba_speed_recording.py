"""P02 attack 4: 'The reverse hypothesis fails too' (speeding type moves alcohol RR 6.41 -> 5.62, Shapley share 4%).
Exceedance is a police judgement, under-recorded in CRSS relative to FARS (fars_crss_recording: CRSS/FARS = 0.67
for exceedance among fatal crashes).  Covariate-free QBA: true exceedance recorded with sensitivity Se_F (fatal)
and Se_N (non-fatal); missed cases are assumed to look like recorded ones within (alcohol, outcome) cells.
Compute the crude alcohol RR and the RR standardised over exceedance, and the share of alcohol's crude log-RR
removed by exceedance, as Se falls.  Also the forward share (alcohol removing exceedance log-RR).
Look at: whether the reverse share can climb well above 4% under plausible under-recording."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import speeding as sp
df, design = sp.load_frame(); w = design.weight
st = df['speeding_type'].astype(str); a = df['alcohol_im'].astype(str).to_numpy(); y = df['fatal'].to_numpy(float)
X = np.where(st=='exceeded_limit_or_racing',1,np.where(st=='no',0,np.nan)); A = (a=='yes').astype(float)
ok = ~np.isnan(X)
def build(Se_F, Se_N):
    n={}
    for aa in (0,1):
        for yy in (0,1):
            m = ok&(A==aa)&(y==yy); o1=w[m&(X==1)].sum(); o0=w[m&(X==0)].sum()
            se = Se_F if yy else Se_N; t1=o1/se; n[(1,aa,yy)]=t1; n[(0,aa,yy)]=o0-(t1-o1)
    return n   # key (X,A,Y)
def rr_std(n, expo, cond):
    # exposure index 0=X,1=A ; stratify on the other ; standardise to marginal of the other
    tot=sum(n.values()); res={}
    def get(e,c,yy): return n[(e,c,yy)] if expo==0 else n[(c,e,yy)]
    pc={c:sum(get(e,c,yy) for e in (0,1) for yy in (0,1)) for c in (0,1)}
    r=lambda e,c: get(e,c,1)/(get(e,c,0)+get(e,c,1))
    crude=(sum(get(1,c,1) for c in (0,1))/sum(get(1,c,yy) for c in (0,1) for yy in (0,1)))/(sum(get(0,c,1) for c in (0,1))/sum(get(0,c,yy) for c in (0,1) for yy in (0,1)))
    adj=sum(pc[c]*r(1,c) for c in (0,1))/sum(pc[c]*r(0,c) for c in (0,1))
    return crude, adj
rows=[]
for Se_F,Se_N in [(1,1),(0.8,0.8),(0.67,0.67),(0.67,0.5),(0.67,0.4),(0.5,0.5),(0.5,0.3)]:
    n=build(Se_F,Se_N)
    cA,aA=rr_std(n,1,0)   # alcohol exposure, standardised over exceedance
    cX,aX=rr_std(n,0,1)   # exceedance exposure, standardised over alcohol
    rows.append(dict(Se_F=Se_F,Se_N=Se_N,alc_crude=cA,alc_adj_for_X=aA,reverse_share=1-np.log(aA)/np.log(cA),exc_crude=cX,exc_adj_for_alc=aX,forward_share=1-np.log(aX)/np.log(cX)))
print(pd.DataFrame(rows).round(3).to_string(index=False))
