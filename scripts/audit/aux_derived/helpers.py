"""Shared helpers for the aux-table audit (read-only use of the interim cache)."""
import polars as pl
from nhtsa_stats.ingestion.cache import load_table

pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(30); pl.Config.set_fmt_str_lengths(60); pl.Config.set_tbl_width_chars(260)
CB = pl.read_csv("/home/user/nhtsa-stats-US/outputs/audit/codebook.csv", infer_schema_length=0)
YEARS = list(range(2016, 2025))

def ck(src):
    return ["ST_CASE"] if src == "FARS" else ["CASENUM"]

def labels(src, table, var):
    """code -> label (most recent year that has the code)."""
    d = CB.filter((pl.col("source") == src) & (pl.col("table") == table) & (pl.col("variable") == var))
    d = d.sort("year").group_by("code").agg(pl.col("label").last())
    return {int(c) if c.lstrip('-').isdigit() else c: l for c, l in d.iter_rows()}

def aux_main(src, level, aux_cols, main_cols, years=None):
    """1:1 join of aux table to its main table."""
    aux = {"crash": "acc_aux", "veh": "veh_aux", "per": "per_aux"}[level]
    main = {"crash": "accident", "veh": "vehicle", "per": "person"}[level]
    k = ["YEAR"] + ck(src) + {"crash": [], "veh": ["VEH_NO"], "per": ["VEH_NO", "PER_NO"]}[level]
    a = load_table(src, aux, years=years, columns=k + aux_cols)
    m = load_table(src, main, years=years, columns=k + [c for c in main_cols if c not in k])
    return a.join(m, on=k, how="inner")

def xtab(df, a, b, src=None, table=None, by_year=False, top=60, w=None):
    """Counts of (a, b) pooled over years (or by YEAR); label b if src/table given."""
    g = [a, b] + (["YEAR"] if by_year else [])
    agg = pl.len().alias("n") if w is None else pl.col(w).sum().round(0).alias("n")
    t = df.group_by(g).agg(agg)
    tot = t.group_by([b] + (["YEAR"] if by_year else [])).agg(pl.col("n").sum().alias("nb"))
    t = t.join(tot, on=[b] + (["YEAR"] if by_year else []))
    t = t.with_columns((100 * pl.col("n") / pl.col("nb")).round(2).alias("pct_of_b"))
    if src and table:
        lab = labels(src, table, b)
        t = t.with_columns(pl.col(b).map_elements(lambda x: (lab.get(x) or "")[:45], return_dtype=pl.String).alias("b_label"))
    t = t.sort(g[::-1] if by_year else [b, a])
    return t

def wide(df, a, b, src=None, table=None):
    """Wide crosstab: rows=b (with label), columns=a codes, cells=count."""
    t = df.group_by([a, b]).agg(pl.len().alias("n"))
    p = t.pivot(on=a, index=b, values="n", sort_columns=True)
    p = p.with_columns([pl.col(c).fill_null(0) for c in p.columns if c != b]).sort(b, nulls_last=True)
    if src and table:
        lab = labels(src, table, b)
        p = p.with_columns(pl.col(b).map_elements(lambda x: (lab.get(x) or "")[:50], return_dtype=pl.String).alias("label"))
    return p

def agree(df, pred, actual, name, by="YEAR"):
    """Per-year agreement of expression pred with column actual (both non-null)."""
    d = df.with_columns(pred.alias("_pred"))
    r = d.group_by(by).agg(pl.len().alias("n"), (pl.col("_pred") == pl.col(actual)).sum().alias("agree"),
                           pl.col("_pred").is_null().sum().alias("pred_null")).sort(by)
    r = r.with_columns((100 * pl.col("agree") / pl.col("n")).round(3).alias("pct"))
    tot = r.select(pl.col("n").sum(), pl.col("agree").sum())
    print(f"--- agreement {name}: overall {tot['agree'][0]}/{tot['n'][0]} = {100*tot['agree'][0]/tot['n'][0]:.3f}%")
    print(r.select(by, "n", "agree", "pct").transpose(include_header=True).to_pandas().to_string(index=False, header=False))
    return d

def mismatch(d, actual, cols, n=30):
    m = d.filter(pl.col("_pred") != pl.col(actual))
    print(m.group_by(["_pred", actual] + cols).agg(pl.len().alias("n")).sort("n", descending=True).head(n))
