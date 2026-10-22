from __future__ import annotations

import pytest

from nhtsa_stats import config


def _cache_ready() -> bool:
    return (config.INTERIM_DIR / "manifest.json").exists()


def pytest_runtest_setup(item):
    if item.get_closest_marker("data") and not _cache_ready():
        pytest.skip("interim Parquet cache not built (run `nhtsa build`)")
    if (
        item.get_closest_marker("processed")
        and not (config.PROCESSED_DIR / "crss_crash.parquet").exists()
    ):
        pytest.skip("processed analytic datasets not built (run `nhtsa build`)")
