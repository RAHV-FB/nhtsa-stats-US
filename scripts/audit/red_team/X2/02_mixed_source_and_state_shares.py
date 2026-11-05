"""X2-02. (a) F01: the headline over-representation ratios divide a FARS numerator share by a CRSS
denominator share. Recompute the ratio with a CRSS-only numerator (share among CRSS fatal crashes)
and show the inflation factor FARS/CRSS per factor. (b) W09: state unbelted / unhelmeted share
ranges: unknown-belt bounds, rank correlation of the share with the unknown share, and which
extreme states rest on few known motorcyclists. Reads committed tables only."""
import pandas as pd, numpy as np
f=pd.read_csv('outputs/tables/descriptive/frequency_vs_severity.csv')
f=f[f.overrep_ratio.notna()].copy()
f['crss_only_ratio']=f.share_fatal_crss/f.share_all_crashes
f['inflation']=f.overrep_ratio/f.crss_only_ratio
print(f[f.factor.isin(['speeding_type','speeding'])|f.level.isin(['motorcycle','yes'])][['factor','level','share_all_crashes','share_fatal_crss','share_fatal_fars','overrep_ratio','crss_only_ratio','inflation']].round(3).to_string())
print('\nlargest inflations:'); print(f.sort_values('inflation',ascending=False).head(8)[['factor','level','overrep_ratio','crss_only_ratio','inflation']].round(2).to_string())
s=pd.read_csv('outputs/tables/deaths/states.csv')
s=s[s.state!='US'] if 'US' in set(s.state) else s
print('\nN states',len(s))
for share,unk,n in [('unbelted_share_known','restraint_unknown_share','pv_known'),('unhelmeted_share_known','helmet_unknown_share','mc_known')]:
    x=s.dropna(subset=[share]).copy()
    # bounds: unknown counted as belted (lower) or unbelted (upper)  -> share*(1-u) ; share*(1-u)+u
    x['lo']=x[share]*(1-x[unk]); x['hi']=x[share]*(1-x[unk])+x[unk]
    print(f'\n{share}: range {x[share].min():.3f}-{x[share].max():.3f}; bounds-range lo {x.lo.min():.3f}..{x.lo.max():.3f} hi {x.hi.min():.3f}..{x.hi.max():.3f}')
    print(' spearman(share, unknown share)=%.2f'%x[share].corr(x[unk],method='spearman'))
    print(' min 3:',x.nsmallest(3,share)[['state',share,unk,n]].round(3).values.tolist())
    print(' max 3:',x.nlargest(3,share)[['state',share,unk,n]].round(3).values.tolist())
    print(' states with <100 known:',int((x[n]<100).sum()), 'median known',x[n].median())
