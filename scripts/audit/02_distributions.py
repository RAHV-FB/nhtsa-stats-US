"""Code distributions per source-year for person-domain variables.

Writes out/dist_{SOURCE}.csv (variable, year, code, n, pct_unweighted, pct_weighted[CRSS]) and prints
a compact wide table per variable (percent by year) plus year-to-year TVD.
"""
import sys

import polars as pl

from nhtsa_stats.ingestion.cache import load_table

OUT = "outputs/cache/audit/out"

VARS = {
    "FARS": ["PER_TYP", "SEX", "INJ_SEV", "SEAT_POS", "REST_USE", "REST_MIS", "HELM_USE", "HELM_MIS",
             "AIR_BAG", "EJECTION", "EJ_PATH", "EXTRICAT", "DOA", "DSTATUS", "HOSPITAL", "LOCATION",
             "WORK_INJ", "HISPANIC", "RACE", "DEVTYPE", "DEVMOTOR"],
    "CRSS": ["PER_TYP", "SEX", "SEX_IM", "INJ_SEV", "INJSEV_IM", "SEAT_POS", "SEAT_IM", "REST_USE",
             "REST_MIS", "HELM_USE", "HELM_MIS", "AIR_BAG", "EJECTION", "EJECT_IM", "DSTATUS",
             "HOSPITAL", "LOCATION", "DEVTYPE", "DEVMOTOR"],
}


def main(src):
    cols = VARS[src] + (["WEIGHT"] if src == "CRSS" else [])
    df = load_table(src, "person", columns=cols)
    rows = []
    for v in VARS[src]:
        g = df.filter(pl.col(v).is_not_null())
        if g.height == 0:
            continue
        aggs = [pl.len().alias("n")]
        if src == "CRSS":
            aggs.append(pl.col("WEIGHT").sum().alias("w"))
        t = g.group_by(["YEAR", v]).agg(aggs).rename({v: "code"})
        tot = t.group_by("YEAR").agg(pl.col("n").sum().alias("N"), *( [pl.col("w").sum().alias("W")] if src == "CRSS" else []))
        t = t.join(tot, on="YEAR").with_columns((100 * pl.col("n") / pl.col("N")).alias("pct_unw"))
        if src == "CRSS":
            t = t.with_columns((100 * pl.col("w") / pl.col("W")).alias("pct_w"))
        else:
            t = t.with_columns(pl.col("pct_unw").alias("pct_w"))
        t = t.with_columns(pl.lit(v).alias("variable"))
        rows.append(t.select(["variable", "YEAR", "code", "n", "pct_unw", "pct_w"]))
        wide = t.pivot(on="YEAR", index="code", values="pct_w", sort_columns=True).sort("code")
        wide = wide.select([pl.col("code")] + [pl.col(c).round(2) for c in wide.columns if c != "code"])
        print(f"\n=== {src} {v} (% {'weighted' if src == 'CRSS' else 'rows'}) N per year:",
              dict(zip(tot.sort('YEAR')['YEAR'].to_list(), tot.sort('YEAR')['N'].to_list())))
        with pl.Config(tbl_rows=200, tbl_cols=20, tbl_width_chars=250):
            print(wide.fill_null(0))
        # TVD year to year
        yrs = sorted(t["YEAR"].unique().to_list())
        p = {y: dict(zip(t.filter(pl.col("YEAR") == y)["code"].to_list(), t.filter(pl.col("YEAR") == y)["pct_w"].to_list())) for y in yrs}
        tv = []
        for a, b in zip(yrs, yrs[1:]):
            codes = set(p[a]) | set(p[b])
            tv.append(f"{a % 100}->{b % 100}:{sum(abs(p[a].get(c, 0) - p[b].get(c, 0)) for c in codes) / 2:.1f}")
        print("  TVD(pp):", " ".join(tv))
    pl.concat(rows).write_csv(f"{OUT}/dist_{src}.csv")


if __name__ == "__main__":
    main(sys.argv[1])
