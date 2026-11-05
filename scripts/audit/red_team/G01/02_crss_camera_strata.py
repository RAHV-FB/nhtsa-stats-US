"""G01 claim: 'Any projection of a camera programme should therefore target limit-exceeding crashes' (RR 5.2 vs 1.06).
Tests whether the exceeded-vs-too-fast contrast holds in the settings cameras operate (urban, low speed limit) using
weighted CRSS crude P(fatal | crash) by speeding_type x speed-limit band x urban. Also CRSS unknown/unspecified share by year."""
import polars as pl
c = pl.read_parquet("data/processed/crss_crash.parquet")
print([x for x in c.columns if x in ("WEIGHT","fatal","ka","speeding_type","speed_limit","rural","FATALS","MAX_SEV","max_sev","YEAR","severity")])
print(c.columns)
