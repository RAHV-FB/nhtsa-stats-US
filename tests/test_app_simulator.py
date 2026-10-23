"""Policy simulator page: runs, asks for inputs, and reproduces the engine's arithmetic."""

from __future__ import annotations

from pathlib import Path

import pytest

from nhtsa_stats import config

APP = Path(__file__).resolve().parents[1] / "app"


@pytest.fixture
def page(tmp_path):
    pytest.importorskip("streamlit")
    if not (config.TABLES_DIR / "simulation" / "baseline.json").exists():
        pytest.skip("simulation baseline not built")
    from streamlit.testing.v1 import AppTest

    script = tmp_path / "page.py"
    script.write_text(
        f"import sys\nsys.path.insert(0, {str(APP)!r})\n"
        "import common  # noqa: F401\nfrom views import simulator\nsimulator.render()\n"
    )
    return AppTest.from_file(str(script), default_timeout=60)


def test_simulator_waits_for_inputs(page):
    at = page.run()
    assert not at.exception
    assert any("Enter the required inputs" in i.value for i in at.info)
    assert not at.metric


def test_generic_reduction_of_all_deaths(page):
    from nhtsa_stats.simulation import engine

    at = page.run()
    at.selectbox(key="one_kind").set_value("generic").run()
    at.selectbox(key="one_seg").set_value("all").run()
    at.number_input(key="one_red_c").set_value(0.1).run()
    assert not at.exception
    deaths = engine.EmpiricalBaseline.load().total_deaths()
    shown = float(at.metric[0].value.replace(",", ""))
    assert shown == pytest.approx(0.1 * deaths, abs=1)
    assert at.metric[1].value == "-10.00%"


def test_speed_cameras_with_ranges_show_sensitivity(page):
    at = page.run()
    at.number_input(key="one_cur").set_value(100.0)
    at.number_input(key="one_new").set_value(200.0)
    at.number_input(key="one_per_c").set_value(0.001)
    at.number_input(key="one_resp_lo").set_value(0.1)
    at.number_input(key="one_resp_c").set_value(0.2)
    at.number_input(key="one_resp_hi").set_value(0.4)
    at.number_input(key="one_occ_c").set_value(0.0)
    at.radio(key="one_sevsrc").set_value(at.radio(key="one_sevsrc").options[1])
    at.run()
    assert not at.exception
    assert at.metric and float(at.metric[0].value.replace(",", "")) > 0
    assert any("Monte Carlo" in m.value for m in at.markdown)
