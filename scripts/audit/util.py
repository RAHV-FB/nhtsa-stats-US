"""Helpers for the completeness-critic spot checks (scratch, not part of the repo)."""
import csv
import collections
import re
import polars as pl
from nhtsa_stats.ingestion.cache import load_table

CB = '/home/user/nhtsa-stats-US/outputs/audit/codebook.csv'
_cb = None


def codebook():
    global _cb
    if _cb is None:
        d = collections.defaultdict(dict)
        for r in csv.DictReader(open(CB)):
            d[(r['source'], int(r['year']), r['table'], r['variable'])][r['code']] = r['label']
        _cb = d
    return _cb


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def labels(source, table, var):
    """code -> {year: label}"""
    cb = codebook()
    out = collections.defaultdict(dict)
    for (s, y, t, v), m in cb.items():
        if s == source and t == table and v == var:
            for c, l in m.items():
                out[c][y] = l
    return out


def label_changes(source, table, var):
    lab = labels(source, table, var)
    res = []
    for c in sorted(lab, key=lambda x: (len(x), x)):
        ys = lab[c]
        ns = {}
        for y in sorted(ys):
            ns.setdefault(norm(ys[y]), []).append(y)
        if len(ns) > 1:
            res.append((c, {k: (v[0], v[-1]) for k, v in ns.items()}))
    return res


def dist(df, var, by='YEAR', w=None):
    """percent distribution of var per by-group; returns wide polars df"""
    if w:
        g = df.group_by([by, var]).agg(pl.col(w).sum().alias('n'))
    else:
        g = df.group_by([by, var]).agg(pl.len().alias('n'))
    g = g.with_columns((100 * pl.col('n') / pl.col('n').sum().over(by)).round(2).alias('pct'))
    return g.pivot(on=by, index=var, values='pct', sort_columns=True).sort(var)


def show(df, var, source, table, by='YEAR', w=None, maxrows=80):
    d = dist(df, var, by, w)
    lab = labels(source, table, var)
    lab2 = {k: v[max(v)] for k, v in lab.items()}
    with pl.Config(tbl_rows=maxrows, tbl_cols=20, tbl_width_chars=250, fmt_str_lengths=45):
        d = d.with_columns(pl.col(var).cast(pl.Utf8).replace_strict(lab2, default='?').str.slice(0, 45).alias('label'))
        print(d)
