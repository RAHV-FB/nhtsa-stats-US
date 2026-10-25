#!/usr/bin/env python3
"""Synchronise the standalone public website with the project's generated evidence.

The research analysis and report renderer remain the sole source of truth.
No statistic is computed or estimated by this script.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SITE = REPO / "website"
SOURCES = {
    "reports/findings.json": "findings.json",
    "outputs/tables/descriptive/frequency_vs_severity.csv": "tables/descriptive/frequency_vs_severity.csv",
    "outputs/tables/severity/fatal_crude_vs_adjusted.csv": "tables/severity/fatal_crude_vs_adjusted.csv",
    "outputs/tables/contributions/ranking.csv": "tables/contributions/ranking.csv",
    "outputs/tables/descriptive/fars_annual.csv": "tables/descriptive/fars_annual.csv",
    "outputs/tables/contributions/fars_overlap_summary.csv": "tables/contributions/fars_overlap_summary.csv",
    "outputs/tables/simulation/threshold_required_share.csv": "tables/simulation/threshold_required_share.csv",
    **{
        f"{folder}/{name}.md": f"reports/{name}.md"
        for folder, name in (
            ("reports", "findings"),
            ("reports", "speeding_confounding"),
            ("reports", "factor_contributions"),
            ("reports", "alcohol_drugs_restraints"),
            ("reports", "multifactor_interactions"),
            ("reports", "case_comparisons"),
            ("reports", "interactions"),
            ("reports", "policy_analysis"),
            ("docs", "methodology"),
            ("docs", "limitations"),
            ("docs", "model_validation"),
        )
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if a bundled snapshot differs from its original")
    args = parser.parse_args()
    stale = []
    for source, target in SOURCES.items():
        src, dst = REPO / source, SITE / "data" / target
        if not src.is_file():
            stale.append(f"Missing research artifact: {source}")
            continue
        if args.check:
            if not dst.is_file() or not filecmp.cmp(src, dst, shallow=False):
                stale.append(f"Stale website snapshot: {target} (source: {source})")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            print(f"{source} -> website/data/{target}")
    if stale:
        print("\n".join(stale), file=sys.stderr)
        if args.check:
            print("Run: python website/tools/sync_public_data.py", file=sys.stderr)
        return 1
    print(f"Research data {'matches' if args.check else 'synchronised'} ({len(SOURCES)} artifacts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
