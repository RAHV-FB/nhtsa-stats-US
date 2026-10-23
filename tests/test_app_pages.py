"""Research interface pages that need the processed CRSS file (skipped when it is absent)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nhtsa_stats import config

APP = Path(__file__).resolve().parents[1] / "app"


def _page(tmp_path, view):
    pytest.importorskip("streamlit")
    if not (config.PROCESSED_DIR / "crss_crash.parquet").exists():
        pytest.skip("processed CRSS file not built")
    from streamlit.testing.v1 import AppTest

    script = tmp_path / f"{view}.py"
    script.write_text(
        f"import sys\nsys.path.insert(0, {str(APP)!r})\n"
        f"import common  # noqa: F401\nfrom views import {view}\n{view}.render()\n"
    )
    return AppTest.from_file(str(script), default_timeout=600)


@pytest.mark.processed
def test_factor_explorer_region_and_area_filters(tmp_path):
    at = _page(tmp_path, "factors").run()
    at.multiselect(key="fx_reg").set_value(["west"]).run()
    at.multiselect(key="fx_area").set_value(["rural"]).run()
    assert not at.exception


@pytest.mark.processed
def test_severity_model_blocks_impossible_configuration(tmp_path):
    at = _page(tmp_path, "severity_model").run()
    at.radio[1].set_value("B").run()
    at.selectbox(key="sm_crash_type").set_value("sv_rollover_first").run()
    at.selectbox(key="sm_n_vehicles").set_value("3+").run()
    assert not at.exception
    assert any("cannot have 3+ vehicles" in w.value for w in at.warning)
    assert not at.metric
