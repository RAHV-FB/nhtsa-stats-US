"""X5-01: Equivalence (TOST at 90% CI) and minimum detectable effect for every published
"no effect / not detected / unchanged" claim.  Inputs: committed tables only (95% CIs).
For each claim: SE(log) = (ln hi - ln lo)/(2 t_.975,42); 90% CI -> smallest symmetric margin
delta such that the 90% CI lies in [1/delta, delta] (TOST equivalence margin, i.e. the claim
'no effect larger than delta-fold' is supported at alpha=.05); MDE80 = exp((t.975+t.80)*SE).
Look at the 'margin' and 'MDE80' columns: a margin of 1.3 means effects up to 30% are NOT excluded.
"""
import numpy as np, pandas as pd
from scipy import stats
T = stats.t.ppf(.975, 42); T90 = stats.t.ppf(.95, 42); T80 = stats.t.ppf(.80, 42)
O = 'outputs/tables/'
rows = []
def add(name, est, lo, hi, tdf=True):
    se = (np.log(hi) - np.log(lo)) / (2 * T)
    l90, h90 = np.log(est) - T90 * se, np.log(est) + T90 * se
    margin = np.exp(max(abs(l90), abs(h90)))
    rows.append(dict(claim=name, est=est, lo95=lo, hi95=hi, se_log=se, ci90=f"{np.exp(l90):.2f}-{np.exp(h90):.2f}",
                     margin=margin, MDE80=np.exp((T + T80) * se), p_vs_1=2 * stats.t.sf(abs(np.log(est) / se), 42)))
sp = pd.read_csv(O + 'severity/fatal_speeding_type.csv').set_index('level')
ka = pd.read_csv(O + 'severity/ka_speeding_type.csv').set_index('level')
r = sp.loc['too_fast_for_conditions']; add('too-fast fatal (F03)', r.adj_rr, r.adj_rr_low, r.adj_rr_high)
r = ka.loc['too_fast_for_conditions']; add('too-fast KA (F03; published as "small excess")', r.adj_rr, r.adj_rr_low, r.adj_rr_high)
w = pd.read_csv(O + 'severity/fatal_crude_vs_adjusted.csv')
r = w[(w.factor == 'weather') & (w.level == 'rain')].iloc[0]; add('rain vs clear, model A (F02)', r.A_adj_rr, r.A_adj_rr_low, r.A_adj_rr_high)
add('rain vs clear, model B (config added)', r.B_adj_rr, r.B_adj_rr_low, r.B_adj_rr_high)
p = pd.read_csv(O + 'interactions/pairs_fatal.csv').set_index('pair')
for k, n in [('speeding x dark_unlit', 'RRR speeding x unlit (F05)'), ('young_driver x late_night', 'RRR young x night (F05)'),
             ('motorcycle x speeding', 'RRR motorcycle x speeding'), ('alcohol x dark_unlit', 'RRR alcohol x unlit'), ('older_driver x angle', 'RRR older x angle')]:
    r = p.loc[k]; add(n, r.ratio_of_rr, r.ratio_of_rr_low, r.ratio_of_rr_high)
m = pd.read_csv(O + 'multifactor/interactions.csv'); r = m[m.analysis == 'sv_driver_exceeded_x_alcohol'].iloc[0]
add('RRR single-vehicle exceed x alcohol (P03)', r.multiplicative_ratio, r.multiplicative_ratio_low, r.multiplicative_ratio_high)
t = pd.read_csv(O + 'trends/within_by_subgroup.csv'); t = t[(t.analysis == 'model_B') & (t.outcome == 'fatal')].set_index('subgroup')
for s in ['alcohol involved (imputed)', 'pedestrian crash', 'driver aged 65+ involved', 'rural PSU']:
    r = t.loc[s]; add(f'within-circ. rise: {s} (F08)', r.within_rr, r.within_rr_low, r.within_rr_high)
print(pd.DataFrame(rows).round(3).to_string())
# belt RR equality (bootstrap SEs, independent strata assumed)
d = pd.read_csv(O + 'restraint_behaviour/dpc_by_driver_behaviour.csv').set_index(['split', 'stratum'])
print('\nBelt within-vehicle RR, ratio of stratum RRs (z-test, bootstrap SE of log RR)')
for sp_, a, b in [('driver speeding (any)', 'driver not speeding', 'driver speeding'), ('driver exceeded limit', 'driver not speeding', 'driver exceeded limit / racing'),
                  ('driver BAC >= .08 (MI)', 'driver BAC < .08', 'driver BAC >= .08'), ('driver speeding and alcohol', 'neither', 'both')]:
    A, B = d.loc[(sp_, a)], d.loc[(sp_, b)]
    lr = np.log(B.rr_belted_vs_unbelted / A.rr_belted_vs_unbelted); se = np.hypot(A.se_log_bootstrap, B.se_log_bootstrap)
    print(f"{sp_:30s} {b:32s} ratio={np.exp(lr):.3f} 90%CI={np.exp(lr-1.645*se):.3f}-{np.exp(lr+1.645*se):.3f} margin={np.exp(abs(lr)+1.645*se):.3f} p={2*stats.norm.sf(abs(lr/se)):.3f} (table p={B.heterogeneity_p})")
