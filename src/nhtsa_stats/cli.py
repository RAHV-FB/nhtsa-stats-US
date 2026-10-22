"""Command-line entry point: ``nhtsa <command>``.

    nhtsa ingest      convert changed raw archives to the typed Parquet cache (incremental)
    nhtsa inventory   write the machine-readable data inventory (outputs/audit)
    nhtsa validate    run relational-integrity checks; non-zero exit on structural failures
    nhtsa features    build the harmonised analytic datasets (data/processed)
    nhtsa build       ingest + inventory + validate + features
    nhtsa analyze [MODULE ...]   run analysis modules (default: all, in dependency order)
    nhtsa all         build + analyze
    nhtsa list        list analysis modules

Each analysis module exposes ``run()`` and writes its own tables/figures, so a single module
can be re-run without rebuilding anything else.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
import time

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
    "policy": "nhtsa_stats.simulation.evidence",
    "figures": "nhtsa_stats.reporting.figures",
    "report": "nhtsa_stats.reporting.render",
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
    from nhtsa_stats.processing.features import build_all

    build_all()


def cmd_build(args: argparse.Namespace) -> None:
    cmd_ingest(args)
    cmd_inventory(args)
    cmd_validate(args)
    cmd_features(args)


def cmd_analyze(args: argparse.Namespace) -> None:
    names = args.modules or list(ANALYSES)
    unknown = [n for n in names if n not in ANALYSES]
    if unknown:
        raise SystemExit(f"unknown module(s): {unknown}; see `nhtsa list`")
    for name in names:
        t0 = time.time()
        mod = importlib.import_module(ANALYSES[name])
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
