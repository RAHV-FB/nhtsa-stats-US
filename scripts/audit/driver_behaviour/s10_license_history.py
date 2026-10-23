"""FARS driver licence and driving-record variables: unknown rates by year/severity, PREV_SUS split, joint missingness."""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT

pl.Config.set_tbl_rows(200)
pl.Config.set_tbl_cols(40)
pl.Config.set_tbl_width_chars(300)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_tbl_hide_column_data_types(True)
f = pl.read_parquet(f"{OUT}/frame_FARS.parquet")
d = f.filter(pl.col("DR_PRES") == 1).with_columns(
    sev=pl.when(pl.col("DRV_INJ_SEV") == 4).then(pl.lit("killed")).when(pl.col("DRV_INJ_SEV").is_in([0, 1, 2, 3, 5]))
    .then(pl.lit("survived")).otherwise(pl.lit("unk")),
    hr=pl.col("HIT_RUN") == 1,
    rec_unk=pl.col("PREV_DWI") == 99,
    lic_invalid=pl.col("L_STATUS").is_in([0, 1, 2, 3, 4]),
    lic_unk=pl.col("L_STATUS") == 9,
    hgt_unk=pl.col("DR_HGT") == 999, wgt_unk=pl.col("DR_WGT") == 999,
    dwi_any=pl.col("PREV_DWI").is_between(1, 98), spd_any=pl.col("PREV_SPD").is_between(1, 98),
    acc98=pl.col("PREV_ACC") == 98,
    sus_any_old=pl.col("PREV_SUS").is_between(1, 97),
    sus_any_new=(pl.col("PREV_SUS1").is_between(1, 97) | pl.col("PREV_SUS2").is_between(1, 97)
                 | pl.col("PREV_SUS3").is_between(1, 97)),
)


def pct(e):
    return (e.cast(pl.Float64).mean() * 100).round(2)


print("== FARS driver-present: unknown/invalid rates by year")
print(d.group_by("YEAR").agg(pl.len().alias("n"), pct(pl.col("lic_unk")).alias("L_STATUS9"),
                             pct(pl.col("lic_invalid")).alias("lic_invalid"),
                             pct(pl.col("L_COMPL") == 9).alias("L_COMPL9"),
                             pct(pl.col("CDL_STAT") == 99).alias("CDL99"),
                             pct(pl.col("rec_unk")).alias("record99"), pct(pl.col("acc98")).alias("PREV_ACC98"),
                             pct(pl.col("dwi_any")).alias("prevDWI>=1"), pct(pl.col("spd_any")).alias("prevSPD>=1"),
                             pct(pl.col("hgt_unk")).alias("HGT999"), pct(pl.col("wgt_unk")).alias("WGT999"),
                             pct(pl.col("L_RESTRI") == 3).alias("RESTRI3"),
                             pct(pl.col("DR_ZIP") == 99999).alias("ZIP99999"),
                             pct(pl.col("DR_ZIP") == 99998).alias("ZIP99998")).sort("YEAR"))
print("== by severity (pooled) and hit-and-run")
for g in ["sev", "hr"]:
    print(d.group_by(g).agg(pl.len().alias("n"), pct(pl.col("lic_unk")).alias("L_STATUS9"),
                            pct(pl.col("lic_invalid")).alias("lic_invalid"),
                            pct(pl.col("rec_unk")).alias("record99"), pct(pl.col("dwi_any")).alias("prevDWI>=1"),
                            pct(pl.col("spd_any")).alias("prevSPD>=1"), pct(pl.col("hgt_unk")).alias("HGT999"),
                            pct(pl.col("wgt_unk")).alias("WGT999"), pct(pl.col("DR_ZIP") == 99999).alias("ZIP99999")).sort(g))
print("== by severity x hit-run")
print(d.group_by("sev", "hr").agg(pl.len().alias("n"), pct(pl.col("lic_unk")).alias("L_STATUS9"),
                                  pct(pl.col("rec_unk")).alias("record99"), pct(pl.col("lic_invalid")).alias("lic_invalid")).sort("sev", "hr"))
print("== per-year L_STATUS9 and record99 by severity")
print(d.group_by("YEAR", "sev").agg(pct(pl.col("lic_unk")).alias("x")).pivot(on="sev", index="YEAR", values="x").sort("YEAR"))
print(d.group_by("YEAR", "sev").agg(pct(pl.col("rec_unk")).alias("x")).pivot(on="sev", index="YEAR", values="x").sort("YEAR"))
print(d.group_by("YEAR", "sev").agg(pct(pl.col("hgt_unk")).alias("x")).pivot(on="sev", index="YEAR", values="x").sort("YEAR"))
print("== joint missingness of driving record: PREV_ACC/SUS/DWI/SPD/OTH/FIRST_MO==99 coincide?")
j = f.with_columns(
    a=pl.col("PREV_ACC") == 99, b=pl.col("PREV_DWI") == 99, c=pl.col("PREV_SPD") == 99, e=pl.col("PREV_OTH") == 99,
    s=pl.coalesce(pl.col("PREV_SUS"), pl.col("PREV_SUS1")) == 99, fm=pl.col("FIRST_YR") == 9999,
    l=pl.col("L_STATUS") == 9)
print(j.group_by("YEAR").agg(pl.col("a").sum(), pl.col("b").sum(), pl.col("c").sum(), pl.col("e").sum(), pl.col("s").sum(),
                             pl.col("fm").sum(), (pl.col("a") & pl.col("b") & pl.col("c") & pl.col("e") & pl.col("s")).sum().alias("all5"),
                             (pl.col("b") & pl.col("l")).sum().alias("rec99&L9"), pl.col("l").sum().alias("L9")).sort("YEAR"))
print("== PREV_SUS1/2/3 meaning test: P(prior DWI>=1 | SUSk>=1), P(prior SPD>=1 | SUSk>=1)")
n = d.filter(pl.col("YEAR") >= 2018)
for kk in ["PREV_SUS1", "PREV_SUS2", "PREV_SUS3"]:
    x = n.filter(pl.col(kk).is_between(1, 97))
    y = n.filter(pl.col(kk) == 0)
    print(kk, "n>=1:", x.height, "P(DWI>=1)=", round(x["dwi_any"].mean() * 100, 1), "vs", round(y["dwi_any"].mean() * 100, 1),
          "| P(SPD>=1)=", round(x["spd_any"].mean() * 100, 1), "vs", round(y["spd_any"].mean() * 100, 1),
          "| P(L_STATUS in 1,2)=", round(x["L_STATUS"].is_in([1, 2]).mean() * 100, 1), "vs", round(y["L_STATUS"].is_in([1, 2]).mean() * 100, 1))
print("== PREV_SUS (2016-17) vs sum(SUS1..3) (2018-19) distribution (% of record-known drivers)")
o = d.filter(pl.col("YEAR") <= 2017, pl.col("PREV_SUS") < 98).with_columns(k=pl.col("PREV_SUS").clip(0, 5))
nn = d.filter(pl.col("YEAR").is_between(2018, 2019), pl.col("PREV_SUS1") < 98).with_columns(
    k=(pl.col("PREV_SUS1") + pl.col("PREV_SUS2") + pl.col("PREV_SUS3")).clip(0, 5))
print(o.group_by("k").len().with_columns((pl.col("len") / pl.col("len").sum() * 100).round(2).alias("pct_1617")).sort("k").join(
    nn.group_by("k").len().with_columns((pl.col("len") / pl.col("len").sum() * 100).round(2).alias("pct_1819")).sort("k"), on="k"))
print("any-suspension share: 2016-17", round(o["sus_any_old"].mean() * 100, 2), "2018-19", round(nn["sus_any_new"].mean() * 100, 2))
print("== PREV_ACC=98 by state (2019 vs 2020): number of states with >50% code 98")
s = d.filter(pl.col("YEAR").is_in([2019, 2020])).group_by("STATE", "YEAR").agg(pct(pl.col("acc98")).alias("p")).pivot(
    on="YEAR", index="STATE", values="p")
print(s.filter((pl.col("2019") > 20) | (pl.col("2020") > 20)).sort("STATE"))
print("== L_STATUS x L_COMPL (driver-present, pooled)")
print(d.group_by("L_STATUS", "L_COMPL").len().pivot(on="L_COMPL", index="L_STATUS", values="len", sort_columns=True).sort("L_STATUS"))
print("== L_TYPE x L_STATUS")
print(d.group_by("L_TYPE", "L_STATUS").len().pivot(on="L_STATUS", index="L_TYPE", values="len", sort_columns=True).sort("L_TYPE"))
print("== DR_HGT / DR_WGT plausible ranges (driver-present, known)")
print(d.filter(pl.col("DR_HGT") < 998).select(pl.col("DR_HGT").quantile(0.001).alias("h_p0.1"), pl.col("DR_HGT").median().alias("h_med"),
                                             pl.col("DR_HGT").quantile(0.999).alias("h_p99.9"), pl.col("DR_HGT").min().alias("hmin"), pl.col("DR_HGT").max().alias("hmax")))
print(d.filter(pl.col("DR_WGT") < 997).select(pl.col("DR_WGT").quantile(0.001), pl.col("DR_WGT").median(), pl.col("DR_WGT").quantile(0.999),
                                             pl.col("DR_WGT").min().alias("wmin"), pl.col("DR_WGT").max().alias("wmax")))
