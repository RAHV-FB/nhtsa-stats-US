"""X5-03 (committed tables only): (a) scale of the reporting - tables, rows, 95% intervals, p-values;
(b) Holm family sensitivity: registered 13 pairs vs all 18 rows, and fatal+KA pooled; which 'headline'
interaction claims change; (c) 2023-24 excess imputed vs complete case: bounds on the untested difference;
(d) cc/imputed share ratio table row for 2023-24.
"""
import glob, numpy as np, pandas as pd
from scipy import stats
tabs = sorted(glob.glob('outputs/tables/*/*.csv'))
nrows = nint = np_ = 0
for f in tabs:
    d = pd.read_csv(f)
    nrows += len(d)
    for c in d.columns:
        if c.endswith('_low') or c.endswith('_ci_low') or c == 'ci_low':
            nint += int(d[c].notna().sum())
        if c == 'p' or c.endswith('_p') or c.endswith('_p_holm') or c.endswith('_p_bh'):
            np_ += int(d[c].notna().sum())
print(f"(a) {len(tabs)} tables, {nrows} rows, ~{nint} reported lower-limit cells (= 95% intervals), ~{np_} p-value cells")
p = pd.read_csv('outputs/tables/interactions/pairs_fatal.csv')
ka = pd.read_csv('outputs/tables/interactions/pairs_ka.csv')
per = pd.read_csv('outputs/tables/interactions/pairs_fatal_by_period.csv')
print('rows pairs_fatal', len(p), 'pairs_ka', len(ka), 'by_period', len(per), '-> pair-level interval sets across files')
def holm(ps):
    ps = np.asarray(ps, float); o = np.argsort(ps); m = len(ps); adj = np.empty(m); run = 0
    for r, i in enumerate(o): run = max(run, (m - r) * ps[i]); adj[i] = min(run, 1)
    return adj
print('\n(b) Holm sensitivity on ratio_of_rr_p (fatal)')
reg = p[p.prespecified]
for label, sel in [('13 registered (published)', reg), ('all 18 rows', p)]:
    a = holm(sel.ratio_of_rr_p); b = holm(sel.ic_p)
    print(label)
    for n, x, y in zip(sel.pair, a, b):
        if n in ('speeding x alcohol', 'heavy_truck x high_speed_road', 'motorcycle x alcohol', 'young_driver x late_night', 'speeding x dark_unlit'):
            print(f"   {n:32s} RRR Holm p={x:.4f}  IC Holm p={y:.4f}")
# KA + fatal pooled family for the 13 registered
kr = ka[ka.prespecified]
allp = np.r_[reg.ratio_of_rr_p.values, kr.ratio_of_rr_p.values]; names = list(reg.pair) + [n + ' [KA]' for n in kr.pair]
a = holm(allp); print('Pooled fatal+KA (26 tests) RRR Holm for chosen rows:')
for n, x in zip(names, a):
    if n in ('speeding x alcohol', 'heavy_truck x high_speed_road', 'motorcycle x alcohol', 'speeding x dark_unlit [KA]', 'young_driver x late_night [KA]', 'speeding x alcohol [KA]'):
        print(f"   {n:32s} {x:.4f}")
print('KA table own Holm columns for speeding x dark_unlit:', ka.loc[ka.pair == 'speeding x dark_unlit', [c for c in ka.columns if 'holm' in c]].round(4).to_dict('records'))
print('\nproduct_p_holm vs ratio_of_rr_p_holm (two tests of "multiplicativity"):')
print(reg[['pair', 'ratio_of_rr_p_holm', 'product_p_holm']].round(4).to_string(index=False))
print('\n(c) 2023-24 obs/expected: imputed vs complete case -- published values (findings.md table)')
for yr, (a1, a2, b1, b2) in {2023: (1.08, .0, 1.15, .0), 2024: (1.05, .0, 1.12, .0)}.items(): pass
for yr, im, im_l, im_h, cc, cc_l, cc_h in [(2023, 1.08, .97, 1.20, 1.15, 1.04, 1.26), (2024, 1.05, .96, 1.14, 1.12, 1.04, 1.21)]:
    s1 = (np.log(im_h) - np.log(im_l)) / (2 * 2.018); s2 = (np.log(cc_h) - np.log(cc_l)) / (2 * 2.018); d = np.log(cc) - np.log(im)
    for rho in (0, .5, .9, .99):
        se = np.sqrt(s1**2 + s2**2 - 2 * rho * s1 * s2)
        print(f"   {yr} rho={rho}: log diff {d:.3f}, SE {se:.3f}, z={d/se:.2f}, p={2*stats.norm.sf(abs(d/se)):.3f}")
o = pd.read_csv('outputs/tables/trends/outcome_definitions_by_year.csv').set_index('YEAR')
print('\n(d) share_ratio_cc_over_imputed by year:'); print(o[['share_ratio_cc_over_imputed', 'share_ratio_cc_over_imputed_low', 'share_ratio_cc_over_imputed_high']].round(3).to_string())
