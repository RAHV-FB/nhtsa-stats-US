"""FARS drugs table structure: exact duplicates, coverage of persons, rows/person, DRUGSPEC x DRUGRES status consistency."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_cols(30)
K = ["YEAR","ST_CASE","VEH_NO","PER_NO"]
raw = load_table("FARS","drugs",years=None,columns=["ST_CASE","VEH_NO","PER_NO","DRUGSPEC","DRUGRES","DRUGMETHOD","DRUGQTY","DRUGUOM","DRUGACTQTY"])
allcols = raw.columns
print("rows by year:", raw.group_by("YEAR").len().sort("YEAR").to_dict(as_series=False))
dup = raw.group_by("YEAR").agg(pl.len().alias("n"), pl.struct(allcols).n_unique().alias("n_unique")).with_columns((pl.col("n")-pl.col("n_unique")).alias("exact_dups")).sort("YEAR")
print(dup)
# duplicates on key+spec+res only (2023+ have extra columns)
d2 = raw.group_by("YEAR").agg(pl.struct(["ST_CASE","VEH_NO","PER_NO","DRUGSPEC","DRUGRES"]).n_unique().alias("uniq_key_spec_res"), pl.len()).sort("YEAR")
print(d2)
d = raw.unique()
p = load_table("FARS","person",years=list(range(2018,2025)),columns=["ST_CASE","VEH_NO","PER_NO","PER_TYP","INJ_SEV"])
pk = d.select(K).unique()
print("persons:", p.height, " persons with >=1 drugs row:", p.join(pk, on=K, how="semi").height, " drugs persons not in person:", pk.join(p, on=K, how="anti").height)
rpp = d.group_by(K).len()
print("rows per person distribution:", rpp["len"].value_counts().sort("len").head(15).to_dict(as_series=False))
# specimen x result status
d = d.with_columns(pl.when(pl.col("DRUGRES")==0).then(pl.lit("0 notgiven"))
    .when(pl.col("DRUGRES")==1).then(pl.lit("1 neg"))
    .when(pl.col("DRUGRES").is_in([95,9995])).then(pl.lit("95 notrep"))
    .when(pl.col("DRUGRES").is_in([996,9996])).then(pl.lit("996 other"))
    .when(pl.col("DRUGRES").is_in([997,9997])).then(pl.lit("997 resunk"))
    .when(pl.col("DRUGRES").is_in([998,9998])).then(pl.lit("998 posunk"))
    .when(pl.col("DRUGRES").is_in([999,9999])).then(pl.lit("999 unkif"))
    .when(pl.col("DRUGRES").is_between(9000,9994)).then(pl.lit("9xxx otherNP"))
    .otherwise(pl.lit("drug")).alias("rc"))
print(d.group_by(["DRUGSPEC","rc"]).len().pivot(on="rc", index="DRUGSPEC", values="len", sort_columns=True).sort("DRUGSPEC"))
# per person: is a 'not given' row mixed with tested rows?
pp = d.group_by(K).agg((pl.col("DRUGSPEC")==0).any().alias("has0"), (~pl.col("DRUGSPEC").is_in([0,96,99])).any().alias("hastested"),
                       (pl.col("DRUGSPEC")==96).any().alias("has96"), (pl.col("DRUGSPEC")==99).any().alias("has99"), pl.len().alias("n"))
print(pp.group_by(["has0","hastested","has96","has99"]).len().sort("len", descending=True))
