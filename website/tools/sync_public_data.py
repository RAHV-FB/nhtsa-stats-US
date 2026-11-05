#!/usr/bin/env python3
"""Copy the CSV tables the public page offers for download into website/data/tables.

The research analysis is the sole source of truth: this script copies files and computes nothing.
The tables are the ones cited in the "Source" lines of website/templates/index.html. Snapshots no
longer listed are deleted; `--check` fails on a missing, stale or orphan file.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SITE = REPO / "website"
DATA = SITE / "data"
TABLES = REPO / "outputs" / "tables"

# Tables outside outputs/tables/deaths that the page cites (CRSS estimates and matched effects).
CITED = [
    "severity/fatal_speeding_type",
    "vulnerable/pedestrian_killed_contrasts",
    "vulnerable/fars_pedestrian_deaths_by_striking_vehicle",
    "person/lpv_killed_crude_vs_adjusted",
    "matched/belt_effect",
    "matched/double_pair_comparison",
]


def sources() -> dict[str, str]:
    """Source path (relative to the repository) -> snapshot path (relative to website/data)."""
    names = sorted(p.relative_to(TABLES).as_posix() for p in (TABLES / "deaths").glob("*.csv"))
    names += [f"{c}.csv" for c in CITED]
    return {f"outputs/tables/{n}": f"tables/{n}" for n in names}


def orphans(targets: set[str]) -> list[Path]:
    if not DATA.exists():
        return []
    return sorted(p for p in DATA.rglob("*") if p.is_file() and p.relative_to(DATA).as_posix() not in targets)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Fail if a snapshot is missing, stale or orphaned"
    )
    args = parser.parse_args()
    mapping = sources()
    problems = []
    for source, target in mapping.items():
        src, dst = REPO / source, DATA / target
        if not src.is_file():
            problems.append(f"Missing research artifact: {source}")
        elif args.check:
            if not dst.is_file() or not filecmp.cmp(src, dst, shallow=False):
                problems.append(f"Stale website snapshot: {target} (source: {source})")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            print(f"{source} -> website/data/{target}")
    for path in orphans(set(mapping.values())):
        rel = path.relative_to(SITE).as_posix()
        if args.check:
            problems.append(f"Orphan file no longer listed in SOURCES: {rel}")
        else:
            path.unlink()
            print(f"removed orphan {rel}")
    if not args.check and DATA.exists():  # drop directories left empty by the cleanup
        for d in sorted((p for p in DATA.rglob("*") if p.is_dir()), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
    if problems:
        print("\n".join(problems), file=sys.stderr)
        if args.check:
            print("Run: python website/tools/sync_public_data.py", file=sys.stderr)
        return 1
    print(f"Research data {'matches' if args.check else 'synchronised'} ({len(mapping)} tables).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
