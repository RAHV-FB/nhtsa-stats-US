"""Print code->label for source table variable (latest year)."""
import sys; sys.path.insert(0, "scripts/audit/aux_derived")
from helpers import labels
src, tab, var = sys.argv[1:4]
lo, hi = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (-1, 10**9)
for k, v in sorted(labels(src, tab, var).items(), key=lambda kv: (isinstance(kv[0], str), kv[0])):
    if isinstance(k, int) and lo <= k <= hi:
        print(k, v)
