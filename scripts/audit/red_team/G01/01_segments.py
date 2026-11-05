"""G01 claim: policy_analysis §3-4 required shares (410/segment deaths) and 'target limit-exceeding crashes'.
Recomputes per-year segment deaths from fars_crash, window sensitivity (2016-18 .. 2022-24), speeding_type composition
by year, unknown-bound scenarios for the required share, drug-unknown share, union of segments."""
import polars as pl
c = pl.read_parquet("data/processed/fars_crash.parquet")
print(c.columns[:80])
print(c.select(["speeding","speeding_type","drugs"]).head(3))
print(c["speeding_type"].value_counts().sort("count",descending=True))
print(c["drugs"].value_counts())
g = c.group_by("YEAR").agg(
  deaths=pl.col("FATALS").sum(),
  sp=pl.col("FATALS").filter(pl.col("speeding")==1).sum(),
  ex=pl.col("FATALS").filter(pl.col("speeding_type")=="exceeded_limit_or_racing").sum(),
  tf=pl.col("FATALS").filter(pl.col("speeding_type")=="too_fast_for_conditions").sum(),
  unspec=pl.col("FATALS").filter(pl.col("speeding_type")=="speeding_unspecified").sum(),
  unk=pl.col("FATALS").filter(pl.col("speeding_type")=="unknown").sum(),
  dr=pl.col("FATALS").filter(pl.col("drugs")==1).sum(),
  drunk=pl.col("FATALS").filter(pl.col("drugs").is_null()).sum(),
).sort("YEAR")
print(g)
d=g.to_pandas().set_index("YEAR")
for a,b in [(2016,2018),(2019,2021),(2022,2024),(2016,2024)]:
    s=d.loc[a:b].mean()
    print(a,b,"all",round(s.deaths),"ex",round(s.ex),"req1%% ex=%.3f"%(0.01*s.deaths/s.ex),"req1%% sp=%.3f"%(0.01*s.deaths/s.sp),
      "req1%% dr=%.3f"%(0.01*s.deaths/s.dr),"ex share of speeding %.2f"%(s.ex/s.sp), "drug null share %.3f"%(s.drunk/s.deaths))
s=d.loc[2022:2024].mean()
print("ex upper bound incl unspecified+unknown:", s.ex+s.unspec, s.ex+s.unspec+s.unk, "req1%:",0.01*s.deaths/(s.ex+s.unspec), 0.01*s.deaths/(s.ex+s.unspec+s.unk))
print("drug if positives scale by 1/known share:", s.dr/(1-s.drunk/s.deaths), "req1%:",0.01*s.deaths/(s.dr/(1-s.drunk/s.deaths)))
