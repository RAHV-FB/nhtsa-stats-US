"""P05 attack 4: survivors' belt status is police/self-reported. If the share f of coded-belted
survivors who are truly unbelted DIFFERS between speeding and non-speeding drivers' vehicles,
the 'equal RR' (1.006) moves. Point estimates only (no bootstrap): ratio of speeding/not RR over a
grid (f_not, f_speeding), using matched.reclassify + dpc_combined. Also the same for BAC."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from nhtsa_stats.analysis import matched, restraint_behaviour as rb
elig=rb.fars_pairs_frame()
st=elig["own_speeding_type"].astype(str)
spd=st.isin(["exceeded_limit_or_racing","too_fast_for_conditions","speeding_unspecified"]); nos=st=="no"
bhi=elig["drv_p_p08"]>0.5
def counts(mask):
    sub=elig.loc[mask]
    d=(sub["ptype"]=="driver")&(sub["SEAT_POS"]==matched.SEAT_POS_DRIVER)
    r=(sub["ptype"]=="passenger")&(sub["SEAT_POS"]==matched.SEAT_POS_RIGHT_FRONT)
    return matched.cell_counts(matched.pair_frame(sub,"belted",d,r))
def rr(c,f): return float(np.exp(matched.dpc_combined(matched.reclassify(c,f))))
for name,a,b in [("speeding vs not",nos,spd),("BAC>=.08 vs <",~bhi,bhi)]:
    ca,cb=counts(a),counts(b)
    print(f"\n{name}: rows f_ref (not-exposed) / cols f_exposed; entries = RR_exposed / RR_ref (and RR_ref)")
    fs=[0,.05,.1,.2]
    print("f_ref\\f_exp "+"  ".join(f"{f:>6}" for f in fs))
    for fr in fs:
        print(f"{fr:>10} "+"  ".join(f"{rr(cb,fe)/rr(ca,fr):6.3f}" for fe in fs), f"  [RR_ref={rr(ca,fr):.3f}]")
