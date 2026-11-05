"""Diff regenerated tables (scratch) vs committed outputs/tables for the given modules.
Usage: 01_diff_tables.py mod1 mod2 ...   Reports missing/extra tables, shape, column order,
row order (cell-by-cell), numeric max abs/rel diff, text-cell diffs. Small CSVs only (no data load)."""
import sys, pathlib, pandas as pd, numpy as np
RT = pathlib.Path("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/X6/outputs/tables")
REPO = pathlib.Path("/home/user/nhtsa-stats-US/outputs/tables")
for m in sys.argv[1:]:
    a = {p.relative_to(REPO/m) for p in (REPO/m).rglob("*.csv")}
    b = {p.relative_to(RT/m) for p in (RT/m).rglob("*.csv")} if (RT/m).exists() else set()
    print(f"== {m}: committed {len(a)} regenerated {len(b)} missing={sorted(map(str,a-b))} extra={sorted(map(str,b-a))}")
    for p in sorted(a & b):
        x = pd.read_csv(REPO/m/p, dtype=object, keep_default_na=False)
        y = pd.read_csv(RT/m/p, dtype=object, keep_default_na=False)
        if list(x.columns) != list(y.columns) or x.shape != y.shape:
            print("  SHAPE/COL DIFF", p, x.shape, y.shape); continue
        raw_same = (x.values == y.values).all()
        if raw_same: continue
        mx_abs = 0.0; mx_rel = 0.0; txt = 0; ex = []
        for c in x.columns:
            for u, v in zip(x[c], y[c]):
                if u == v: continue
                try:
                    fu, fv = float(u), float(v); d = abs(fu-fv)
                    mx_abs = max(mx_abs, d); mx_rel = max(mx_rel, d/max(abs(fu), 1e-300))
                except ValueError:
                    txt += 1; ex.append((c, u, v))
        print(f"  DIFF {p}: max_abs={mx_abs:.3g} max_rel={mx_rel:.3g} text_cells={txt} {ex[:2]}")
    # sidecar json diff on non-timestamp keys
