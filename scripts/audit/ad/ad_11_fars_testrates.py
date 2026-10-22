"""FARS drivers: alcohol & drug test status by severity (killed vs survived) x year; state variation; MI vs measured share."""
import polars as pl
OUT = "/tmp/nhtsa-audit/out_ad"
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_cols(30)
df = pl.read_parquet(f"{OUT}/fars_person.parquet").filter(pl.col("PER_TYP")==1)
dp = pl.read_parquet(f"{OUT}/fars_drug_person.parquet")
df = df.join(dp.select(["YEAR","ST_CASE","VEH_NO","PER_NO","drug_test_status","drug_result"]), on=["YEAR","ST_CASE","VEH_NO","PER_NO"], how="left")
df = df.with_columns(
  pl.when(pl.col("INJ_SEV")==4).then(pl.lit("killed")).when(pl.col("INJ_SEV").is_in([0,1,2,3,5])).then(pl.lit("survived"))
    .when(pl.col("INJ_SEV")==9).then(pl.lit("sev_unknown")).otherwise(pl.lit("died_prior")).alias("sev"),
  pl.when(pl.col("ALC_RES")<=940).then(pl.lit("measured")).when(pl.col("ALC_RES")==997).then(pl.lit("tested_res_unknown"))
    .when(pl.col("ALC_RES")==998).then(pl.lit("pos_no_value")).when(pl.col("ALC_RES")==996).then(pl.lit("not_tested"))
    .when(pl.col("ALC_RES")==995).then(pl.lit("not_reported")).when(pl.col("ALC_RES")==999).then(pl.lit("unk_if_tested")).alias("alc_stat"))
df.write_parquet(f"{OUT}/fars_drivers.parquet")
print("drivers:", df.height, df.group_by("sev").len().sort("sev").to_dict(as_series=False))
def rate_table(col, val, by=["YEAR"], f=None):
    x = df if f is None else df.filter(f)
    return x.group_by(by+["sev"]).agg((pl.col(col)==val).mean().mul(100).round(1).alias("pct"), pl.len().alias("n")).filter(pl.col("sev").is_in(["killed","survived"]))
for col,val,lab in [("alc_stat","measured","% with measured BAC"),("alc_stat","not_tested","% alcohol test not given"),
                    ("alc_stat","not_reported","% ALC test status not reported (995)"),("alc_stat","unk_if_tested","% unknown if tested (999)"),
                    ("alc_stat","tested_res_unknown","% tested, result unknown (997)"),
                    ("drug_test_status","tested","% drug tested"),("drug_test_status","not_tested","% drug test not given"),
                    ("drug_test_status","not_reported","% drug test not reported"),("drug_test_status","unknown_if_tested","% drug unknown if tested")]:
    t = rate_table(col,val)
    print(f"--- {lab}")
    print(t.pivot(on="sev", index="YEAR", values="pct").sort("YEAR").join(t.pivot(on="sev", index="YEAR", values="n").sort("YEAR").rename({"killed":"n_k","survived":"n_s"}), on="YEAR").with_columns(pl.col("YEAR").cast(pl.Utf8)).transpose(include_header=True, column_names="YEAR"))
# pooled
print("POOLED alc_stat by sev (%):")
print(df.group_by(["sev","alc_stat"]).len().with_columns((100*pl.col("len")/pl.col("len").sum().over("sev")).round(2).alias("pct")).pivot(on="sev", index="alc_stat", values="pct"))
print("POOLED drug_test_status by sev (%):")
print(df.group_by(["sev","drug_test_status"]).len().with_columns((100*pl.col("len")/pl.col("len").sum().over("sev")).round(2).alias("pct")).pivot(on="sev", index="drug_test_status", values="pct"))
# measured vs imputed share among all drivers by year (MI: everyone is in miper; measured => implicates = observed)
print("share of drivers whose MI value is observed (ALC_RES measured), by year:")
print(df.group_by("YEAR").agg((pl.col("alc_stat")=="measured").mean().mul(100).round(2).alias("pct_measured"), pl.len()).sort("YEAR").with_columns(pl.col("YEAR").cast(pl.Utf8)).transpose(include_header=True, column_names="YEAR"))
# state
st = df.filter(pl.col("sev").is_in(["killed","survived"])).group_by(["STATE","sev"]).agg((pl.col("alc_stat")=="measured").mean().mul(100).alias("alc"),
        (pl.col("drug_test_status")=="tested").mean().mul(100).alias("drug"), pl.len().alias("n"))
w = st.pivot(on="sev", index="STATE", values=["alc","drug","n"])
print("STATE pooled 2016-2024 (alc measured %, drug tested %):")
print(w.select(pl.all().exclude("STATE").quantile(0.0).round(1).name.suffix("_min")).hstack(w.select(pl.all().exclude("STATE").quantile(0.25).round(1).name.suffix("_p25"))).hstack(w.select(pl.all().exclude("STATE").median().round(1).name.suffix("_med"))).hstack(w.select(pl.all().exclude("STATE").quantile(0.75).round(1).name.suffix("_p75"))).hstack(w.select(pl.all().exclude("STATE").max().round(1).name.suffix("_max"))).transpose(include_header=True))
w = w.sort("alc_survived")
print(w.with_columns(pl.col(["alc_killed","alc_survived","drug_killed","drug_survived"]).round(1)))
w.write_csv(f"{OUT}/state_testrates.csv")
