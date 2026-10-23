"""The committed reports equal a fresh render of their templates from the committed tables."""

from __future__ import annotations

import pytest

from nhtsa_stats.reporting import render


@pytest.mark.parametrize(
    "template",
    sorted(p.name for p in render.TEMPLATE_DIR.glob("*") if p.suffix in (".md", ".json")),
)
def test_report_matches_fresh_render(tmp_path, template):
    render.render_all(out_dir=tmp_path)
    fresh = (tmp_path / template).read_text()
    committed = (render.REPORT_DIR / template).read_text()
    assert fresh == committed, f"reports/{template} is stale: run `nhtsa analyze report`"
