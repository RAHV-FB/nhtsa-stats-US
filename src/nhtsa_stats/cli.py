"""Command-line entry point: ``nhtsa <command>``.

    nhtsa ingest      convert changed raw archives to the typed Parquet cache (incremental)
    nhtsa inventory   write the machine-readable data inventory (outputs/audit)
    nhtsa validate    run relational-integrity checks; non-zero exit on structural failures
    nhtsa features    build the harmonised analytic datasets (data/processed)
    nhtsa build       ingest + inventory + validate + features
    nhtsa analyze [MODULE ...]   run analysis modules (default: all, in dependency order)
    nhtsa all         build + analyze
    nhtsa list        list analysis modules
    nhtsa status      list tables whose code or input data changed since they were written,
                      and tables without a code hash

Each analysis module exposes ``run()`` and writes its own tables/figures, so a single module
can be re-run without rebuilding anything else.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
import time
from typing import NamedTuple

# Analysis modules in dependency order (later modules may read earlier outputs).
ANALYSES: dict[str, str] = {
    "descriptive": "nhtsa_stats.analysis.descriptive",
    "severity": "nhtsa_stats.analysis.severity",
    "measurement": "nhtsa_stats.analysis.measurement",
    "interactions": "nhtsa_stats.analysis.interactions",
    "confounding": "nhtsa_stats.analysis.confounding",
    "trends": "nhtsa_stats.analysis.trends",
    "person": "nhtsa_stats.analysis.person",
    "matched": "nhtsa_stats.analysis.matched",
    "exposure": "nhtsa_stats.analysis.exposure",
    "burden": "nhtsa_stats.analysis.burden",
    "vulnerable": "nhtsa_stats.analysis.vulnerable",
    "ml": "nhtsa_stats.models.severity_ml",
    # Phase 2 (docs/research_plan_phase2.md)
    "speeding": "nhtsa_stats.analysis.speeding",
    "drugs": "nhtsa_stats.analysis.drugs",
    "multifactor": "nhtsa_stats.analysis.multifactor",
    "restraint_behaviour": "nhtsa_stats.analysis.restraint_behaviour",
    "contributions": "nhtsa_stats.analysis.contributions",
    "stages": "nhtsa_stats.analysis.stages",
    "deaths": "nhtsa_stats.analysis.deaths",
    "policy": "nhtsa_stats.simulation.evidence",
    "figures": "nhtsa_stats.reporting.figures",
    "report": "nhtsa_stats.reporting.render",
    "site": "nhtsa_stats.reporting.site",
    "docs": "nhtsa_stats.reporting.docs_gen",
}

log = logging.getLogger("nhtsa")


def cmd_ingest(args: argparse.Namespace) -> None:
    from nhtsa_stats.ingestion.cache import build_interim

    build_interim(force=args.force, workers=args.workers)


def cmd_inventory(_: argparse.Namespace) -> None:
    from nhtsa_stats.validation.inventory import build_inventory

    build_inventory()


def cmd_validate(_: argparse.Namespace) -> None:
    from nhtsa_stats.validation.integrity import run_integrity_checks

    res = run_integrity_checks()
    fails = res.filter(res["status"] == "fail")
    warns = res.filter(res["status"] == "warn")
    log.info("%d checks: %d fail, %d warn", res.height, fails.height, warns.height)
    if fails.height:
        log.error("structural integrity failures:\n%s", fails)
        sys.exit(2)


def cmd_features(_: argparse.Namespace) -> None:
    from nhtsa_stats.processing import drivers
    from nhtsa_stats.processing.features import build_all

    build_all()
    # Driver-level files and person links (Phase 2) read the crash files written above.
    drivers.build_all()


def cmd_build(args: argparse.Namespace) -> None:
    cmd_ingest(args)
    cmd_inventory(args)
    cmd_validate(args)
    cmd_features(args)


def cmd_analyze(args: argparse.Namespace) -> None:
    unknown = [n for n in args.modules if n not in ANALYSES]
    if unknown:
        raise SystemExit(f"unknown module(s): {unknown}; see `nhtsa list`")
    from nhtsa_stats.reporting.io import snapshot_code_sha256

    # Always in dependency order, whatever order the modules were named in.
    names = [n for n in ANALYSES if not args.modules or n in args.modules]
    for name in names:
        t0 = time.time()
        mod = importlib.import_module(ANALYSES[name])
        # Digest of the code as loaded, before run(): edits during a long run cannot make
        # the tables written by this run look fresh.
        snapshot_code_sha256(ANALYSES[name])
        log.info("running %s", name)
        mod.run()
        log.info("%s finished in %.0fs", name, time.time() - t0)


def cmd_all(args: argparse.Namespace) -> None:
    cmd_build(args)
    args.modules = []
    cmd_analyze(args)


def cmd_list(_: argparse.Namespace) -> None:
    for k, v in ANALYSES.items():
        print(f"{k:14} {v}")


class TableStatus(NamedTuple):
    stale: list[str]  # code (module or an imported helper) changed since the table was written
    unhashed: list[str]  # sidecar has no code_sha256
    inputs_changed: list[str]  # a local input file differs from the recorded inputs_sha256
    n_checked: int


def stale_tables() -> TableStatus:
    """Compare table sidecars (and ``_provenance`` of JSON outputs) under ``outputs/tables``
    with the current code and, where the data exist locally, the current input files."""
    import json

    from nhtsa_stats import config
    from nhtsa_stats.reporting.io import current_code_sha256, input_sha256

    stale: list[str] = []
    unhashed: list[str] = []
    changed: list[str] = []
    n = 0
    current: dict[str, str | None] = {}
    for side in sorted(config.TABLES_DIR.rglob("*.json")):
        try:
            meta = json.loads(side.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        if "module" in meta and "table" in meta:
            rel, prov = meta["table"], meta
        elif isinstance(meta.get("_provenance"), dict):
            rel, prov = side.relative_to(config.TABLES_DIR).as_posix(), meta["_provenance"]
        else:
            continue  # neither a table sidecar nor a provenance-carrying JSON output
        n += 1
        recorded = prov.get("code_sha256")
        if not recorded:
            unhashed.append(rel)
            continue
        mod = prov["module"]
        if mod not in current:
            current[mod] = current_code_sha256(mod)
        if current[mod] != recorded:
            stale.append(rel)
        for spec, digest in (prov.get("inputs_sha256") or {}).items():
            now = input_sha256(spec)
            if now is not None and now != digest:
                changed.append(rel)
                break
    return TableStatus(stale, unhashed, changed, n)


def cmd_status(_: argparse.Namespace) -> None:
    st = stale_tables()
    print(
        f"{st.n_checked} table sidecars / provenance-carrying JSON outputs: {len(st.stale)} stale "
        f"(code changed), {len(st.unhashed)} without code_sha256, "
        f"{len(st.inputs_changed)} with changed input data"
    )
    for label, items in (
        ("stale", st.stale),
        ("no-hash", st.unhashed),
        ("inputs-changed", st.inputs_changed),
    ):
        for t in items:
            print(f"{label:14} {t}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="nhtsa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (
        ("ingest", cmd_ingest),
        ("inventory", cmd_inventory),
        ("validate", cmd_validate),
        ("features", cmd_features),
        ("build", cmd_build),
        ("all", cmd_all),
        ("list", cmd_list),
        ("status", cmd_status),
    ):
        p = sub.add_parser(name)
        p.set_defaults(func=fn)
        if name in ("ingest", "build", "all"):
            p.add_argument("--force", action="store_true", help="re-extract every archive")
            p.add_argument("--workers", type=int, default=2)
    pa = sub.add_parser("analyze")
    pa.add_argument("modules", nargs="*")
    pa.set_defaults(func=cmd_analyze)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    args.func(args)


if __name__ == "__main__":
    main()
