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


@pytest.mark.processed
def test_interaction_explorer_registered_pair_order(tmp_path):
    at = _page(tmp_path, "interactions").run()
    # Default A = speeding, B = light (dark unlit vs daylight): the registered orientation.
    assert any("Pre-specified pair 'speeding x dark_unlit'" in c.value for c in at.caption)
    # Swapped: the pre-computed row (whose "RR of A given B" rows are A-specific) is not shown.
    at.selectbox(key="av").set_value("light").run()
    at.selectbox(key="bv").set_value("speeding").run()
    for k, v in (
        ("ae", ["dark_not_lighted"]),
        ("ar", ["daylight"]),
        ("be", ["yes"]),
        ("br", ["no"]),
    ):
        at.multiselect(key=k).set_value(v).run()
    assert not at.exception
    assert any("other way round" in c.value for c in at.caption)
    assert not any("Pre-specified pair" in c.value for c in at.caption)


def test_multi_vehicle_crash_types_get_the_multi_vehicle_domain():
    import sys

    sys.path.insert(0, str(APP))
    from nhtsa_stats.analysis import interactions as it
    from views import interactions as page

    angle = it.Exposure("crash_type", ("mv_angle",), ("mv_rear_end",), "angle")
    older = it.Exposure("older_driver", ("yes",), ("no",), "older")
    ped = it.Exposure("crash_type", ("pedestrian",), ("mv_rear_end",), "ped")
    assert page._domain(older, angle) == "multi_vehicle"
    assert page._domain(older, ped) == "multi_vehicle"  # rear-end reference is multi-vehicle
    assert (
        page._domain(older, it.Exposure("light", ("dark_not_lighted",), ("daylight",), "")) is None
    )
