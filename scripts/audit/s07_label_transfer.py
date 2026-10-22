"""CRSS 2016-18 (unlabelled): code-set overlap with CRSS 2019+ and same-year FARS labels; year-to-year TVD."""
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import polars as pl
from common import OUT

pl.Config.set_tbl_rows(200)
pl.Config.set_tbl_width_chars(250)
pl.Config.set_tbl_hide_dataframe_shape(True)
pl.Config.set_tbl_hide_column_data_types(True)
cs = pl.read_csv(f"{OUT}/codesets.csv", schema_overrides={"code": pl.Utf8, "label": pl.Utf8, "nlabel": pl.Utf8})
cs = cs.with_columns(share=pl.col("n") / pl.col("n").sum().over("source", "YEAR", "table", "variable"))
HIGH = {"TRAV_SP", "VSPD_LIM", "DR_HGT", "DR_WGT", "FIRST_YR", "LAST_YR"}
rows = []
crss_vars = cs.filter(pl.col("source") == "CRSS").select("table", "variable").unique().sort("table", "variable")
for table, var in crss_vars.iter_rows():
    g = cs.filter((pl.col("source") == "CRSS") & (pl.col("table") == table) & (pl.col("variable") == var))
    yrs = sorted(g["YEAR"].unique().to_list())
    lab = g.filter(pl.col("label").is_not_null())
    lab_codes = set(lab["code"].to_list())
    fars = cs.filter((pl.col("source") == "FARS") & (pl.col("table") == table) & (pl.col("variable") == var))

    def tvd(y1, y2):
        a = g.filter(pl.col("YEAR") == y1).select("code", pl.col("share").alias("a"))
        b = g.filter(pl.col("YEAR") == y2).select("code", pl.col("share").alias("b"))
        m = a.join(b, on="code", how="full", coalesce=True).fill_null(0)
        return round(0.5 * (m["a"] - m["b"]).abs().sum() * 100, 1)

    for y in [2016, 2017, 2018]:
        if y not in yrs:
            continue
        gy = g.filter(pl.col("YEAR") == y)
        codes = set(gy["code"].to_list())
        notlab = codes - lab_codes
        fy = fars.filter(pl.col("YEAR") == y)
        fcodes = set(fy["code"].to_list())
        n_notlab = int(gy.filter(pl.col("code").is_in(list(notlab)))["n"].sum())
        notlab_inf = sorted(notlab & fcodes, key=lambda x: float(x))
        notlab_none = sorted(notlab - fcodes, key=lambda x: float(x))
        rows.append(dict(table=table, var=var, year=y, n_codes=len(codes), codes_not_in_crss19plus=len(notlab),
                         rows_not_in_crss19plus=n_notlab,
                         unl_codes_labelled_by_fars=",".join(notlab_inf) if var not in HIGH else f"{len(notlab_inf)}",
                         unl_codes_no_label_anywhere=",".join(notlab_none) if var not in HIGH else f"{len(notlab_none)}",
                         tvd_vs_next=tvd(y, y + 1) if (y + 1) in yrs else None))
    if 2019 in yrs and 2020 in yrs:
        rows.append(dict(table=table, var=var, year=2019, n_codes=None, codes_not_in_crss19plus=None,
                         rows_not_in_crss19plus=None, unl_codes_labelled_by_fars="", unl_codes_no_label_anywhere="",
                         tvd_vs_next=tvd(2019, 2020)))
out = pl.DataFrame(rows)
print(out)
# also TVD FARS consecutive years for comparison
rows = []
for (table, var), g in cs.filter(pl.col("source") == "FARS").group_by(["table", "variable"]):
    yrs = sorted(g["YEAR"].unique().to_list())
    r = {"table": table, "var": var}
    for y in yrs[:-1]:
        a = g.filter(pl.col("YEAR") == y).select("code", pl.col("share").alias("a"))
        b = g.filter(pl.col("YEAR") == y + 1).select("code", pl.col("share").alias("b"))
        m = a.join(b, on="code", how="full", coalesce=True).fill_null(0)
        r[f"{y}-{y+1}"] = round(0.5 * (m["a"] - m["b"]).abs().sum() * 100, 1)
    rows.append(r)
print("FARS year-to-year TVD (%):")
print(pl.DataFrame(rows).sort("table", "var"))
rows = []
for (table, var), g in cs.filter(pl.col("source") == "CRSS").group_by(["table", "variable"]):
    yrs = sorted(g["YEAR"].unique().to_list())
    r = {"table": table, "var": var}
    for y in yrs[:-1]:
        a = g.filter(pl.col("YEAR") == y).select("code", pl.col("share").alias("a"))
        b = g.filter(pl.col("YEAR") == y + 1).select("code", pl.col("share").alias("b"))
        m = a.join(b, on="code", how="full", coalesce=True).fill_null(0)
        r[f"{y}-{y+1}"] = round(0.5 * (m["a"] - m["b"]).abs().sum() * 100, 1)
    rows.append(r)
print("CRSS year-to-year TVD (%), unweighted:")
print(pl.DataFrame(rows).sort("table", "var"))
