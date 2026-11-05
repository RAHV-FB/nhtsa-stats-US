"""Inspect keys/values: processed fars_person vs per_aux A_RESTUSE (scratch)."""
import polars as pl
p=pl.read_parquet("data/processed/fars_person.parquet")
for c in ["case_id","body","restraint","seat","ptype","killed","ejected","REST_USE","SEAT_POS","EJECTION","INJ_SEV","role"]:
    print(c, p[c].head(3).to_list(), p[c].n_unique())
print(p["body"].value_counts().sort("body"))
print(p["restraint"].value_counts())
print(p["seat"].value_counts())
print(p["REST_USE"].value_counts().sort("REST_USE"))
print(p["ejected"].value_counts())
print(p.group_by("INJ_SEV").len().sort("INJ_SEV"))
a=pl.concat([pl.read_parquet(f"data/interim/FARS/per_aux/{y}.parquet") for y in range(2016,2025)],how="diagonal")
print(a.shape, a.columns[:8])
