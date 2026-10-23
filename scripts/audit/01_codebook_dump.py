"""Dump code->label mapping per source/year for person-domain variables from codebook.csv.

For each (source, table, variable): one line per code, listing years present, the label
variants (raw) with the years they apply to, and a flag when normalised label text differs.
Usage: python 01_codebook_dump.py VAR [VAR ...]
"""
import re
import sys
from collections import defaultdict

import polars as pl

CB = "/home/user/nhtsa-stats-US/outputs/audit/codebook.csv"
TABLES = ("person", "race")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def main(vars_):
    cb = pl.read_csv(CB, infer_schema_length=0)
    cb = cb.filter(pl.col("table").is_in(TABLES) & pl.col("variable").is_in(vars_))
    for (src, tab, var), g in sorted(cb.group_by(["source", "table", "variable"]), key=lambda x: x[0]):
        print(f"\n===== {src} {tab} {var}  years={sorted(set(g['year'].to_list()))}")
        codes = defaultdict(lambda: defaultdict(list))
        cnt = defaultdict(dict)
        for r in g.iter_rows(named=True):
            codes[r["code"]][r["label"]].append(r["year"][-2:])
            cnt[r["code"]][r["year"]] = r["n"]

        def key(c):
            try:
                return (0, float(c))
            except ValueError:
                return (1, c)

        for c in sorted(codes, key=key):
            labs = codes[c]
            nn = {norm(l) for l in labs}
            flag = " **NORMDIFF**" if len(nn) > 1 else (" (cosmetic)" if len(labs) > 1 else "")
            labtxt = " | ".join(f"[{','.join(sorted(ys))}] {l}" for l, ys in labs.items())
            print(f"  {c:>6}: {labtxt}{flag}")


if __name__ == "__main__":
    main(sys.argv[1:])
