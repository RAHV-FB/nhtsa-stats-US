"""P02 attack 2: measured vs true alcohol -> residual confounding.
Claim attacked: 'alcohol accounts for ~9% (16% when added first) of the crude log-RR of exceedance'.
Alcohol in CRSS is police-reported/imputed involvement of ANY driver, and police may miss alcohol far more
often in non-fatal crashes (no BAC test) than in fatal ones.  (i) prints alcohol prevalence by outcome
(CRSS weighted) and the FARS counterpart; (ii) crude (covariate-free) QBA: let police sensitivity for true alcohol
be Se_F (fatal) and Se_N (non-fatal), specificity 1; reconstruct true-alcohol 2x2xY counts assuming missed
alcohol crashes look like detected ones within (exposure, outcome) cells; recompute the alcohol-standardised
exceedance RR and the share of the crude log-RR that alcohol removes (published first-step: 10.03 -> 6.97 = 16%).
Look at: how the share and the stratum RRs (no-alcohol vs alcohol) move as Se_N falls."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import speeding as sp, data
df, design = sp.load_frame()
w = design.weight
st = df['speeding_type'].astype(str); a = df['alcohol_im'].astype(str)
y = df['fatal'].to_numpy(float)
print('--- (i) CRSS weighted alcohol_im==yes share')
for lab, m in [('all', np.ones(len(df),bool)), ('fatal', y==1), ('nonfatal', y==0)]:
    print(f'{lab:9s} {w[m&(a=="yes").to_numpy()].sum()/w[m&a.isin(["yes","no"]).to_numpy()].sum():.4f}  (n_unknown_alc={int((m&~a.isin(["yes","no"]).to_numpy()).sum())})')
print('police alcohol categories (unweighted counts):', df['alcohol'].astype(str).value_counts().to_dict())
fc = data.fars_crash()
print('FARS cols', [c for c in fc.columns if 'alc' in c.lower() or 'bac' in c.lower()])
for c in ['alcohol_driver','driver_bac08_prob']:
    if c in fc.columns:
        s=fc[c]; print(c, s.dtype, (s.astype(str).value_counts().head(5).to_dict() if s.dtype==object or str(s.dtype)=='category' else (s.mean(),)))
# --- (ii) QBA, covariate-free
x = np.where(st=='exceeded_limit_or_racing',1,np.where(st=='no',0,np.nan))
ok = ~np.isnan(x) & a.isin(['yes','no']).to_numpy()
A = (a=='yes').to_numpy()
def cnt(mask): return w[mask]
def cells(Se_F, Se_N):
    """weighted true counts n[A,x,y]"""
    n = {}
    for xx in (0,1):
        for yy in (0,1):
            m = ok & (x==xx) & (y==yy)
            obs1 = w[m & A].sum(); obs0 = w[m & ~A].sum()
            se = Se_F if yy==1 else Se_N
            t1 = obs1/se; t0 = obs0 - (t1-obs1)
            n[(1,xx,yy)] = t1; n[(0,xx,yy)] = max(t0,1e-9)
    return n
def summarise(n):
    tot = sum(n.values())
    pA = {k: sum(v for (aa,_,_),v in n.items() if aa==k)/tot for k in (0,1)}
    def r(aa,xx):
        d = n[(aa,xx,0)]+n[(aa,xx,1)]; return n[(aa,xx,1)]/d
    crude = (sum(n[(aa,1,1)] for aa in (0,1))/sum(n[(aa,1,yy)] for aa in (0,1) for yy in (0,1))) / (sum(n[(aa,0,1)] for aa in (0,1))/sum(n[(aa,0,yy)] for aa in (0,1) for yy in (0,1)))
    adj = sum(pA[k]*r(k,1) for k in (0,1))/sum(pA[k]*r(k,0) for k in (0,1))
    return crude, adj, r(0,1)/r(0,0), r(1,1)/r(1,0), pA[1]
print('\n--- (ii) QBA: Se_F, Se_N -> crude RR, alcohol-standardised RR, share removed by alcohol, stratum RR (no alc, alc), true alc prevalence')
rows=[]
for Se_F in (1.0,0.9):
    for Se_N in (1.0,0.8,0.6,0.5,0.4,0.3):
        if Se_N>Se_F: continue
        c,ad,r0,r1,pa = summarise(cells(Se_F,Se_N))
        rows.append(dict(Se_F=Se_F,Se_N=Se_N,crude=c,adj=ad,share_removed=1-np.log(ad)/np.log(c),rr_noalc=r0,rr_alc=r1,prev_true=pa))
out=pd.DataFrame(rows); print(out.round(3).to_string(index=False))
out.to_csv('/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/P02/02_qba.csv',index=False)
