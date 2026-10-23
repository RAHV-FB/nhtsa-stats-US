"""Can CRSS 2019+ labels / same-year FARS labels be applied to CRSS 2016-2018 (unlabelled)?

For each categorical person variable: codes observed in CRSS 2016/2017/2018 (from dist_CRSS.csv),
codes not in the CRSS 2019-2024 label union, codes not in the same-year FARS label set, the weighted
share of rows with such codes, and TVD of CRSS y vs CRSS 2019 and vs CRSS 2018->2019.
"""
import polars as pl

OUT = "outputs/cache/audit/out"
cb = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/codebook.csv", infer_schema_length=0)
cb = cb.filter(pl.col("table") == "person").with_columns(pl.col("year").cast(pl.Int64))
d = pl.read_csv(f"{OUT}/dist_CRSS.csv").with_columns(pl.col("code").cast(pl.Utf8))

VARS = ["PER_TYP", "SEX", "SEX_IM", "INJ_SEV", "INJSEV_IM", "SEAT_POS", "SEAT_IM", "REST_USE",
        "REST_MIS", "AIR_BAG", "EJECTION", "EJECT_IM", "HOSPITAL", "LOCATION", "DSTATUS"]


def labset(src, var, years):
    return set(cb.filter((pl.col("source") == src) & (pl.col("variable") == var) & pl.col("year").is_in(years))["code"].to_list())


def dist(var, y):
    g = d.filter((pl.col("variable") == var) & (pl.col("YEAR") == y))
    return dict(zip(g["code"].to_list(), g["pct_w"].to_list()))


rows = []
for v in VARS:
    crss19 = labset("CRSS", v, range(2019, 2025))
    p19 = dist(v, 2019)
    for y in (2016, 2017, 2018):
        p = dist(v, y)
        if not p:
            continue
        fars = labset("FARS", v, [y])
        not19 = sorted(set(p) - crss19, key=float)
        notf = sorted(set(p) - fars, key=float) if fars else ["(no FARS var)"]
        m19 = sum(p[c] for c in not19)
        mf = sum(p[c] for c in notf if c in p)
        codes = set(p) | set(p19)
        tvd = sum(abs(p.get(c, 0) - p19.get(c, 0)) for c in codes) / 2
        rows.append(dict(var=v, year=y, n_codes=len(p), not_in_crss19_labels=",".join(not19), pct_w_not19=round(m19, 3),
                         not_in_fars_same_year=",".join(notf), pct_w_notfars=round(mf, 3), tvd_vs_2019=round(tvd, 2)))
out = pl.DataFrame(rows)
with pl.Config(tbl_rows=100, tbl_width_chars=250, fmt_str_lengths=60):
    print(out)
out.write_csv(f"{OUT}/crss_unlabelled_check.csv")
