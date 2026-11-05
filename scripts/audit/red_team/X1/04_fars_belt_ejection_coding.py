"""X1-04  FARS within-vehicle belt design (F07, P05, W04): is REST_USE coded using outcome-linked info?

Concern: police infer 'unbelted' from ejection / severe injury (ejection is a consequence of the crash
and of non-use); belted survivors are self-reported. Test: (1) ejection share by restraint x killed;
(2) recompute the double-pair-comparison belted/unbelted fatality RR (project functions, closed form,
no bootstrap) on all pairs vs pairs where neither occupant was ejected.
Look at: RR all (published 0.3415) vs RR without ejected pairs.
"""
import numpy as np, pandas as pd, polars as pl
from nhtsa_stats.analysis import matched as M
df = M.load_fars_occupants()
ej = pl.read_parquet("data/processed/fars_person.parquet", columns=["YEAR","case_id","VEH_NO","PER_NO","ejected"]).to_pandas()
df = df.merge(ej, on=["YEAR","case_id","VEH_NO","PER_NO"], how="left") if "PER_NO" in df.columns else df
elig, _ = M.lpv_flow_and_eligible(df)
elig["belted"] = 1 - elig["unbelted"]
print(pd.crosstab([elig.killed, elig.restraint], elig.ejected.astype(str), normalize="index").round(3).to_string())
print("ejected share killed unbelted %.3f belted %.3f ; survivors unbelted %.3f belted %.3f" % tuple(
  elig[(elig.killed==k)&(elig.belted==b)].ejected.astype(str).isin(["True","yes","1","1.0"]).mean() for k,b in [(1,0),(1,1),(0,0),(0,1)]))
drv=(elig.ptype=="driver")&(elig.SEAT_POS==M.SEAT_POS_DRIVER); rf=(elig.ptype=="passenger")&(elig.SEAT_POS==M.SEAT_POS_RIGHT_FRONT)
def rr(sub_mask=None):
    e=elig if sub_mask is None else elig[sub_mask]
    p=M.pair_frame(e,"belted",(e.ptype=="driver")&(e.SEAT_POS==M.SEAT_POS_DRIVER),(e.ptype=="passenger")&(e.SEAT_POS==M.SEAT_POS_RIGHT_FRONT))
    c=M.cell_counts(p); return float(np.exp(M.dpc_combined(c))), len(p), M.death_counts(c)
base=rr(); print("DPC RR all pairs: %.4f n=%d"%base[:2])
ejv=set(elig.loc[elig.ejected.astype(str).isin(["True","yes","1","1.0"]),"vehicle_id"])
noej=~elig.vehicle_id.isin(ejv)
r2=rr(noej); print("DPC RR vehicles with no ejected eligible occupant: %.4f n=%d (%.1f%% of pairs)"%(r2[0],r2[1],100*r2[1]/base[1]))
