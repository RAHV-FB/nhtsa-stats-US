"""Miscellaneous person checks: race table structure, DSTATUS meaning, PER_TYP personal-conveyance split
vs DEVTYPE/DEVMOTOR, SEAT_POS vs PER_TYP, AGE details, killed-vs-survivor restraint unknown summary.
"""
import polars as pl

from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(80)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(250)
OUT = "/tmp/nhtsa-audit/out"

# ---- race table
r = load_table("FARS", "race", years=range(2019, 2025), columns=["ST_CASE", "VEH_NO", "PER_NO", "RACE", "ORDER", "MULTRACE"])
p = load_table("FARS", "person", years=range(2019, 2025), columns=["ST_CASE", "VEH_NO", "PER_NO", "INJ_SEV"])
K = ["YEAR", "ST_CASE", "VEH_NO", "PER_NO"]
rp = r.group_by(K).agg(pl.len().alias("n_rows"), pl.col("RACE").min().alias("rmin"), pl.col("RACE").max().alias("rmax"),
                       pl.col("MULTRACE").max().alias("multi"), pl.col("ORDER").max().alias("omax"))
j = p.join(rp, on=K, how="left")
print("### race table: persons covered, rows per person, multi-race, by year")
print(j.group_by("YEAR").agg(pl.len().alias("persons"), pl.col("n_rows").is_null().sum().alias("no_race_row"),
                             (pl.col("n_rows") > 1).sum().alias("multi_rows"), (pl.col("multi") == 1).sum().alias("MULTRACE1"),
                             ((pl.col("INJ_SEV") != 4) & (pl.col("rmax") != 0)).sum().alias("nonfatal_with_race"),
                             ((pl.col("INJ_SEV") == 4) & (pl.col("rmin") == 0)).sum().alias("fatal_with_race0"),
                             (pl.col("multi") == 7).sum().alias("MULTRACE7_redacted")).sort("YEAR"))
print("race rows anti-join to person:", r.join(p, on=K, how="anti").height)
print("2019 ORDER/MULTRACE values:", r.filter(pl.col("YEAR") == 2019).group_by(["ORDER", "MULTRACE"]).len().to_dicts())
fr = r.join(p.filter(pl.col("INJ_SEV") == 4).select(K), on=K)
print("fatalities: RACE distribution (%) per year, first-listed (ORDER==1 or 2019 all) rows")
first = fr.filter((pl.col("ORDER") == 1) | (pl.col("YEAR") == 2019) | pl.col("ORDER").is_null())
t = first.group_by(["YEAR", "RACE"]).len().with_columns((100 * pl.col("len") / pl.col("len").sum().over("YEAR")).round(2).alias("pct"))
print(t.pivot(on="YEAR", index="RACE", values="pct", sort_columns=True).sort("RACE").fill_null(0))
print("ORDER values among MULTRACE==1:", r.filter(pl.col("MULTRACE") == 1).group_by("ORDER").len().sort("ORDER").to_dicts())
print("persons with >1 race rows but MULTRACE==0:", j.filter((pl.col("n_rows") > 1) & (pl.col("multi") == 0)).height)

# ---- DSTATUS meaning (2016-2017 cross-tab vs DRUGTST1) and by severity
d = load_table("FARS", "person", years=[2016, 2017], columns=["DSTATUS", "DRUGTST1", "INJ_SEV"])
print("### FARS 2016-17 DSTATUS x DRUGTST1 (counts)")
print(d.group_by(["DSTATUS", "DRUGTST1"]).len().sort("len", descending=True).head(15))
cb = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/codebook.csv", infer_schema_length=0)
print(cb.filter((pl.col("variable") == "DRUGTST1") & (pl.col("year") == "2016") & (pl.col("source") == "FARS")).select(["code", "label", "n"]).head(12))
ds = load_table("FARS", "person", columns=["DSTATUS", "INJ_SEV"])
print("### FARS DSTATUS by year x killed (% of rows)")
print(ds.with_columns((pl.col("INJ_SEV") == 4).alias("K")).group_by(["YEAR", "K", "DSTATUS"]).len().with_columns(
    (100 * pl.col("len") / pl.col("len").sum().over(["YEAR", "K"])).round(1).alias("pct")).pivot(on="DSTATUS", index=["YEAR", "K"], values="pct", sort_columns=True).sort(["K", "YEAR"]))

# ---- PER_TYP personal conveyance vs DEVTYPE/DEVMOTOR
for src in ("FARS", "CRSS"):
    q = load_table(src, "person", years=range(2020, 2025), columns=["PER_TYP", "DEVTYPE", "DEVMOTOR", "VEH_NO"])
    print(f"### {src} PER_TYP 8/11/12/13/19 by year")
    print(q.filter(pl.col("PER_TYP").is_in([8, 11, 12, 13, 19])).group_by(["YEAR", "PER_TYP"]).len().pivot(on="PER_TYP", index="YEAR", values="len", sort_columns=True).sort("YEAR"))
    print(f"### {src} 2022+ PER_TYP x DEVMOTOR (non-motorists)")
    print(q.filter((pl.col("YEAR") >= 2022) & (pl.col("VEH_NO") == 0)).group_by(["PER_TYP", "DEVMOTOR"]).len().pivot(on="DEVMOTOR", index="PER_TYP", values="len", sort_columns=True).sort("PER_TYP"))
print(cb.filter(pl.col("variable").is_in(["DEVMOTOR", "DEVTYPE"]) & (pl.col("year") == "2024") & (pl.col("source") == "FARS")).select(["variable", "code", "label", "n"]))

# ---- SEAT_POS vs PER_TYP
for src in ("FARS", "CRSS"):
    q = load_table(src, "person", columns=["PER_TYP", "SEAT_POS", "BODY_TYP"])
    print(f"### {src} drivers (PER_TYP 1): SEAT_POS distribution (pooled)")
    print(q.filter(pl.col("PER_TYP") == 1).group_by("SEAT_POS").len().sort("len", descending=True).head(6).to_dicts())
    print(f"### {src} passengers in seat 11 by body class:", q.filter((pl.col("PER_TYP") == 2) & (pl.col("SEAT_POS") == 11)).with_columns(
        (pl.col("BODY_TYP").is_between(80, 89)).alias("moto")).group_by("moto").len().to_dicts())

# ---- AGE details
for src in ("FARS", "CRSS"):
    q = load_table(src, "person", columns=["PER_TYP", "AGE", "INJ_SEV"])
    print(f"### {src} AGE: 998/999 counts and drivers aged < 14 by year")
    print(q.group_by("YEAR").agg((pl.col("AGE") == 998).sum().alias("n998"), (pl.col("AGE") == 999).sum().alias("n999"),
                                 ((pl.col("PER_TYP") == 1) & (pl.col("AGE") < 14)).sum().alias("drivers_lt14"),
                                 (pl.col("AGE").is_between(121, 997)).sum().alias("n_121_997"),
                                 pl.col("AGE").filter(pl.col("AGE") < 998).median().alias("median")).sort("YEAR"))
