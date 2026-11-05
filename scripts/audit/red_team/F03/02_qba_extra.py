"""F03: bias analyses the published QBA omits.
(a) DIFFERENTIAL SPECIFICITY for exceedance: false 'exceeded' codes only in fatal crashes
    (police infer speeding post hoc from severity). Published grid varies sensitivity only; its
    sp=0.99 rows are all NaN (published qba_grid).
(b) Same sensitivity grid for 'too fast for conditions' vs no (published QBA covers exceedance only).
(c) Type-shift misclassification: fraction g of recorded TF crashes are really exceeders.
(d) FARS recalibration of the fatal counts: scale CRSS fatal TF/exceeded counts to FARS shares.
Output: corrected crude RRs. Compare with published crude 10.03 / 1.34."""
import numpy as np, pandas as pd
from nhtsa_stats.analysis import data
from nhtsa_stats.analysis.measurement import corrected_rr
df, design = data.crss_crash(outcome="fatal"); w = design.weight
st = df["speeding_type"].astype(str); y = df["fatal"].to_numpy(float)
def cells(code):
    x = np.where(st == code, 1.0, np.where(st == "no", 0.0, np.nan)); k = ~np.isnan(x)
    f = lambda e, o: w[k & (x == e) & (y == o)].sum()
    return f(1,1), f(1,0), f(0,1), f(0,0)
for code in ("exceeded_limit_or_racing", "too_fast_for_conditions"):
    a,b,c,d = cells(code); print(code, "crude RR", (a/(a+b))/(c/(c+d)), "weighted shares exposed fatal/nonfatal", a/(a+c), b/(b+d))
# (a) differential specificity, exceed
a,b,c,d = cells("exceeded_limit_or_racing"); fat, non = a+c, b+d
print("\n(a) exceed: false-positive share P in FATAL crashes only (sens=1, sp_nonfatal=1)")
for fp in (0, .005, .01, .02, .03, .04, .05):
    at = a - fp*fat; ct = c + fp*fat   # misclassified unexposed recorded as exposed
    print(f"  fp_fatal={fp:.3f}  corrected RR={(at/(at+b))/(ct/(ct+d)):.2f}")
print("(a2) joint: sens_nonfatal 0.5 AND fp_fatal")
for fp in (0, .01, .02, .03):
    at = a - fp*fat; ct = c + fp*fat; bt = b/0.5; 
    print(f"  fp_fatal={fp:.3f} se_nf=0.5  RR={(at/(at+bt))/(ct/(ct+d)):.2f}")
# (b) TF sensitivity grid
a,b,c,d = cells("too_fast_for_conditions")
print("\n(b) TF corrected crude RR, se_fatal=0.8 (published crude 1.34)")
for sn in (0.3,0.5,0.8,1.0,1.2,1.5):
    print(f"  se_nonfatal={sn}: {corrected_rr(a,b,c,d,0.8,sn) if sn<=1 else (lambda : ((a/0.8)/((a/0.8)+b/sn))/((c/0.8)/((c/0.8)+d/sn)))():.2f}")
print("   (se_nonfatal>1 => nonfatal recorded MORE completely than fatal -> equivalent to se_fatal<1)")
for sf in (0.5,0.6,0.7):
    print(f"  se_fatal={sf}, se_nonfatal=1.0: {corrected_rr(a,b,c,d,sf,1.0):.2f}")
# (c) type shift
ex = cells("exceeded_limit_or_racing"); tf = cells("too_fast_for_conditions"); no = cells("no")
rate = lambda c_: c_[0]/(c_[0]+c_[1])
r_tf, r_ex, r_no = rate(tf), rate(ex), c / (c+d) if False else no[2]/(no[2]+no[3])
print("\n(c) rates (weighted, per crash) no/TF/EX:", r_no, r_tf, r_ex)
print("   share g of TF group that would be hidden exceeders to explain whole crude excess:", (r_tf-r_no)/(r_ex-r_no))
# (d) FARS recalibration: published FARS share of fatal crashes vs CRSS (descriptive/frequency_vs_severity)
fars = {"exceeded": 0.108956, "tf": 0.116730, "no": 0.655362}; crss = {"exceeded": 0.073225, "tf": 0.091033, "no": 0.735414}
print("\n(d) FARS/CRSS fatal-share ratio:", {k: round(fars[k]/crss[k],3) for k in fars})
for code, key in (("exceeded_limit_or_racing","exceeded"),("too_fast_for_conditions","tf")):
    a,b,c,d = cells(code); _,_,_,_=0,0,0,0
    s = fars[key]/crss[key]; sn = fars["no"]/crss["no"]
    a2, c2 = a*s, c*sn
    print(f"  {code}: crude RR {(a/(a+b))/(c/(c+d)):.2f} -> {(a2/(a2+b))/(c2/(c2+d)):.2f} with CRSS fatal counts scaled to FARS shares")
