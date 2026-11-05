"""P06 attack 7: is 'alcohol first on deaths involved' (105,821 vs speeding 98,693) robust?
(a) between-implicate spread of the BAC>=.08 death count over the 10 MI implicates (FARS);
(b) break-even drug-positive rate among the 222,767 deaths with undetermined drug status at which
drugs would out-rank alcohol (committed fars_overlap_summary numbers)."""
import numpy as np, polars as pl
from nhtsa_stats import config
cols=[f"drv_bac08_mi_{i}" for i in range(1,11)]
d=pl.read_parquet(config.PROCESSED_DIR/"fars_driver.parquet",columns=["YEAR","case_id",*cols])
c=d.group_by(["YEAR","case_id"]).agg(*[pl.col(x).max().fill_null(0).alias(f"a{i+1}") for i,x in enumerate(cols)])
p=pl.read_parquet(config.PROCESSED_DIR/"fars_person.parquet",columns=["YEAR","case_id","killed","speeding"]).filter(pl.col("killed")==1)
j=p.join(c,on=["YEAR","case_id"],how="left").to_pandas()
tot=[float(j[f"a{i}"].fillna(0).sum()) for i in range(1,11)]
print("BAC>=.08 deaths per implicate:",np.round(tot,0)); print("mean %.0f sd %.0f min %.0f max %.0f"%(np.mean(tot),np.std(tot,ddof=1),min(tot),max(tot)))
print("speeding-related deaths:",int((j.speeding==1).sum()))
det=353706-222767; pos=84207
print("determinate deaths",det,"drug-positive share among determinate %.3f"%(pos/det))
need=105821-pos; print("extra positives among undetermined needed for drugs>alcohol:",need," = %.1f%% of undetermined"%(100*need/222767))
for r in [0.05,0.10,0.20,0.30]: print(f" if undetermined positive rate {r:.0%}: drug-involved deaths ~{pos+r*222767:,.0f}")
