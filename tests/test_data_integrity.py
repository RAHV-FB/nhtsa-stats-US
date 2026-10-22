"""Relational-integrity tests on the real interim cache (skipped when it is absent)."""

from __future__ import annotations

import json

import polars as pl
import pytest

from nhtsa_stats import config
from nhtsa_stats.ingestion.archives import discover_archives
from nhtsa_stats.ingestion.cache import load_table
from nhtsa_stats.validation.integrity import check_year

pytestmark = pytest.mark.data


def test_all_36_archives_present_and_classified():
    arch = discover_archives()
    assert len(arch) == 36
    keys = {(a.source, a.year, a.kind) for a in arch}
    assert keys == {
        (s, y, k) for s in ("FARS", "CRSS") for y in config.YEARS for k in ("main", "aux")
    }


def test_manifest_covers_every_archive_with_checksums():
    manifest = json.loads((config.INTERIM_DIR / "manifest.json").read_text())
    assert len(manifest) == 36
    for rec in manifest.values():
        assert rec["lfs_oid_match"] in (True, None)
        assert len(rec["sha256"]) == 64
        assert rec["tables"]


@pytest.mark.parametrize("source", ["FARS", "CRSS"])
@pytest.mark.parametrize("year", [2016, 2020, 2024])
def test_structural_integrity(source, year):
    results = check_year(source, year)
    failures = [r.as_dict() for r in results if r.status == "fail"]
    assert not failures, failures


def test_fars_fatalities_reconcile_with_person_records():
    acc = load_table("FARS", "accident", columns=["ST_CASE", "FATALS"])
    per = load_table("FARS", "person", columns=["ST_CASE", "INJ_SEV"])
    a = acc.group_by("YEAR").agg(pl.col("FATALS").sum()).sort("YEAR")
    p = per.filter(pl.col("INJ_SEV") == 4).group_by("YEAR").len().sort("YEAR")
    assert a["FATALS"].to_list() == p["len"].to_list()


def test_crss_design_ids_stable_across_years():
    a = load_table("CRSS", "accident", columns=["PSU_VAR", "PSUSTRAT"])
    per_psu = a.group_by("PSU_VAR").agg(pl.col("PSUSTRAT").n_unique())
    assert per_psu["PSUSTRAT"].max() == 1
    n_psu = a.group_by(["YEAR", "PSUSTRAT"]).agg(pl.col("PSU_VAR").n_unique())
    assert n_psu["PSU_VAR"].min() >= 2, "a stratum with a single PSU needs lonely-PSU handling"
