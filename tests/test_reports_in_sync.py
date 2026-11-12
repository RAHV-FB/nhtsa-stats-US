"""The committed reports and README equal a fresh render of their templates from the committed tables."""

from __future__ import annotations

import re

import pytest

from nhtsa_stats import config
from nhtsa_stats.reporting import render

TEMPLATES = sorted(p.name for p in render.TEMPLATE_DIR.glob("*") if p.suffix in (".md", ".json"))


def _committed(template: str):
    root = config.PROJECT_ROOT if template in render.ROOT_TEMPLATES else render.REPORT_DIR
    return root / template


def test_readme_is_a_template():
    assert "README.md" in TEMPLATES
    assert "README.md" in render.ROOT_TEMPLATES


@pytest.mark.parametrize("template", TEMPLATES)
def test_report_matches_fresh_render(tmp_path, template):
    render.render_all(out_dir=tmp_path, root_dir=tmp_path)
    fresh = (tmp_path / template).read_text()
    committed = _committed(template).read_text()
    where = "README.md" if template in render.ROOT_TEMPLATES else f"reports/{template}"
    assert fresh == committed, f"{where} is stale: run `nhtsa analyze report`"


@pytest.mark.parametrize("template", [t for t in TEMPLATES if t.endswith(".md")])
def test_committed_report_has_no_unresolved_placeholder(template):
    text = _committed(template).read_text()
    assert "{{" not in text and "}}" not in text
    assert not re.search(r"\bnan\b", text, flags=re.IGNORECASE)
