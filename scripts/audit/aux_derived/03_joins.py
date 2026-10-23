"""Verify 1:1 joins of aux tables to main tables and equality of shared non-key columns."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table
pairs = {"acc_aux": "accident", "veh_aux": "vehicle", "per_aux": "person"}
keys = {"acc_aux": [], "veh_aux": ["VEH_NO"], "per_aux": ["VEH_NO", "PER_NO"]}
res = []
for src in ["FARS", "CRSS"]:
    ck = ["ST_CASE"] if src == "FARS" else ["CASENUM"]
    for aux, main in pairs.items():
        k = ["YEAR"] + ck + keys[aux]
        share = {"FARS": {"acc_aux": ["STATE", "FATALS", "COUNTY"], "veh_aux": ["STATE"], "per_aux": ["STATE"]},
                 "CRSS": {"acc_aux": ["WEIGHT"], "veh_aux": ["WEIGHT"], "per_aux": ["WEIGHT"]}}[src][aux]
        for y in range(2016, 2025):
            a = load_table(src, aux, years=[y], columns=k + share)
            m = load_table(src, main, years=[y], columns=k + share)
            j = a.join(m, on=k, how="full", suffix="_m", coalesce=True, nulls_equal=True)
            only_a = j.filter(pl.col(share[0]+"_m").is_null() & pl.col(share[0]).is_not_null()).height if False else a.join(m, on=k, how="anti").height
            only_m = m.join(a, on=k, how="anti").height
            dup_a = a.height - a.select(k).unique().height
            inner = a.join(m, on=k, how="inner", suffix="_m")
            diffs = {}
            for c in share:
                if c in a.columns and a[c].null_count() < a.height and m[c].null_count() < m.height:
                    if a[c].dtype == pl.String or inner[c+"_m"].dtype == pl.String:
                        d = (inner[c].cast(pl.String) != inner[c+"_m"].cast(pl.String)).sum()
                    else:
                        d = (inner[c].cast(pl.Float64) - inner[c+"_m"].cast(pl.Float64)).abs().gt(1e-9).sum()
                    diffs[c] = int(d)
                else:
                    diffs[c] = "absent"
            res.append(dict(source=src, aux=aux, year=y, n_aux=a.height, n_main=m.height, dup_keys_aux=dup_a,
                            aux_not_in_main=only_a, main_not_in_aux=only_m, matched=inner.height, shared_col_mismatch=str(diffs)))
df = pl.DataFrame(res)
pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(20); pl.Config.set_fmt_str_lengths(80); pl.Config.set_tbl_width_chars(250)
print(df)
df.write_csv("outputs/cache/audit/out_aux/joins.csv")
