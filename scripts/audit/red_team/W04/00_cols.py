"""Inspect columns of processed FARS person + interim per_aux/person (scratch)."""
import polars as pl
p=pl.read_parquet("data/processed/fars_person.parquet")
print(p.columns)
a=pl.read_parquet("data/interim/FARS/per_aux/2020.parquet");print(a.columns)
print(a.select("A_RESTUSE").to_series().value_counts().sort("A_RESTUSE"))
q=pl.read_parquet("data/interim/FARS/person/2020.parquet");print(q.columns)
