"""P02 attack 3 (adjustment set / apples-to-oranges): 
(a) the README/summary pairs 'with all seven blocks RR 4.9' with 'no-alcohol stratum 6.5 vs alcohol 3.3', but the
    strata models omit crash configuration (strata.csv 'blocks' column).  Refit the alcohol strata WITH configuration.
(b) 'after all recorded circumstances': drugs and distracted-driving (police-reported, both in crss_crash) are not in
    any block.  Refit the all-block model and the strata with an extra block (drugs, distracted).
Look at: all-block RR (expect 4.88 = published), then RR with extra block; stratum RRs with config; ratio of strata RRs."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import speeding as sp, confounding as cf, data, specs
from nhtsa_stats.analysis.survey import MarginSet
cf.BLOCKS['extra'] = ('drugs', 'distracted')
df, design = data.crss_crash(outcome='fatal', tri_state_cols=specs.CRASH_TRI)
df[cf.NIGHT_COLUMN] = df['night'].map({1:'night',0:'day'}).fillna('unknown').astype(object)
df['YEAR'] = df['YEAR'].astype(int)
cols = sorted(set(cf.analysis_columns()) | {'drugs','distracted'})
df = df[list(dict.fromkeys([*cols, cf.NIGHT_COLUMN, 'fatal','ka']))].copy()
df['fatal']=df['fatal'].astype(float)
for c in [*cols]: df[c]=pd.Categorical(df[c], categories=cf.declared_levels(c))
print('drugs levels (unweighted):', df['drugs'].value_counts().to_dict(), ' distracted:', df['distracted'].value_counts().to_dict())
base = sp.EXPOSURES['exceeded']
ex = cf.Exposure(base.name, base.column, base.reference, base.exposed, (*base.blocks,'extra'), base.label)
cd = cf.cluster_design(design)
def rr(f): return np.exp(f.log_rr)
env5 = [b for b in sp.ENV_BLOCKS]
F = lambda d, s, blocks: cf.fit_subset(d, s, ex, blocks, 'fatal')
allb = [*sp.ENV_BLOCKS,'alcohol','configuration']
f = F(df, design, allb); print('all 7 blocks RR', round(rr(f),3), '(published 4.88)')
f2 = F(df, design, allb+['extra']); print('7 blocks + drugs/distracted RR', round(rr(f2),3))
f3 = F(df, design, [*sp.ENV_BLOCKS,'alcohol','extra']); print('6 blocks (no config) + extra RR', round(rr(f3),3))
f4 = F(df, design, [*sp.ENV_BLOCKS,'alcohol']); print('6 blocks (no config) RR', round(rr(f4),3))
a = df['alcohol_im'].astype(str)
res = {}
for lab, blocks in [('env5 (published strata)', env5), ('env5 + configuration', env5+['configuration']),
                    ('env5 + config + extra', env5+['configuration','extra'])]:
    fits={}
    for sname, mask in [('no alcohol', (a=='no').to_numpy()), ('alcohol', (a=='yes').to_numpy())]:
        sub=df.loc[mask].reset_index(drop=True); sd=design.subset(mask)
        for c in sub.columns:
            if isinstance(sub[c].dtype, pd.CategoricalDtype): sub[c]=sub[c].cat.remove_unused_categories()
        fits[sname]=F(sub, sd, blocks)
    ms = MarginSet({'a':fits['no alcohol'].log_rr,'b':fits['alcohol'].log_rr},{'a':fits['no alcohol'].t_log_rr,'b':fits['alcohol'].t_log_rr}, cd)
    d,se = cf.linear_contrast(ms, {'b':1.0,'a':-1.0}); t=cd.tcrit()
    print(f'{lab:28s} RR no-alc {rr(fits["no alcohol"]):.2f}  RR alc {rr(fits["alcohol"]):.2f}  ratio {np.exp(d):.2f} ({np.exp(d-t*se):.2f}-{np.exp(d+t*se):.2f})  RD no-alc {fits["no alcohol"].m_exposed-fits["no alcohol"].m_reference:.4f} RD alc {fits["alcohol"].m_exposed-fits["alcohol"].m_reference:.4f}')
