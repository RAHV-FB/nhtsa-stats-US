"""Report renderer: placeholders resolve from output tables and fail loudly otherwise."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from nhtsa_stats import config
from nhtsa_stats.reporting import render


@pytest.fixture
def tables(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path)
    (tmp_path / "m").mkdir()
    pd.DataFrame(
        {
            "factor": ["speeding", "speeding", "alcohol"],
            "level": ["yes", "no", "yes"],
            "YEAR": [2016.0, 2016.0, 2017.0],
            "adj_rr": [1.83, 1.0, 4.44],
            "adj_rr_low": [1.49, 1.0, 3.71],
            "adj_rr_high": [2.25, 1.0, 5.31],
            "share": [0.1008, 0.86, 0.052],
            "deaths": [37806, 1, 2],
        }
    ).to_csv(tmp_path / "m" / "t.csv", index=False)
    (tmp_path / "m" / "j.json").write_text(json.dumps({"a": {"b": 3871.2}}))
    render._table.cache_clear()
    render._json.cache_clear()
    yield tmp_path
    render._table.cache_clear()
    render._json.cache_clear()


def test_formats(tables):
    assert render.render_text("{{m/t|factor=speeding;level=yes|adj_rr|.2f}}") == "1.83"
    assert render.render_text("{{m/t|factor=speeding;level=yes|adj_rr|ci:2}}") == "1.83 (1.49–2.25)"
    assert render.render_text("{{m/t|factor=speeding;level=yes|share|pct:1}}") == "10.1%"
    assert render.render_text("{{m/t|factor=speeding;level=yes|deaths|,.0f}}") == "37,806"
    assert render.render_text("{{m/t|YEAR=2017|adj_rr|.1f}}") == "4.4"
    assert render.render_text("{{json:m/j|a.b|,.0f}}") == "3,871"


def test_ambiguous_or_missing_fails(tables):
    with pytest.raises(render.RenderError, match="matched 2 rows"):
        render.render_text("{{m/t|factor=speeding|adj_rr|.2f}}")
    with pytest.raises(render.RenderError, match="matched 0 rows"):
        render.render_text("{{m/t|factor=nothing|adj_rr|.2f}}")
    with pytest.raises(render.RenderError, match="no column"):
        render.render_text("{{m/t|factor=alcohol|nope|.2f}}")
    with pytest.raises(render.RenderError, match="table not found"):
        render.render_text("{{m/zzz||x|.2f}}")


def test_mdtable(tables):
    out = render.render_text(
        "{{mdtable:m/t|factor=speeding|level:Level:;adj_rr:RR (95% CI):ci:2;share:Share:pct:0}}"
    )
    lines = out.splitlines()
    assert lines[0] == "| Level | RR (95% CI) | Share |"
    assert lines[2] == "| yes | 1.83 (1.49–2.25) | 10% |"
    assert len(lines) == 4


def test_multi_value_filter(tables):
    out = render.render_text("{{mdtable:m/t|factor=speeding~alcohol;level=yes|factor::}}")
    assert out.splitlines()[2:] == ["| speeding |", "| alcohol |"]


def test_ci_column_variants(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TABLES_DIR", tmp_path)
    (tmp_path / "m").mkdir()
    pd.DataFrame(
        {
            "term": ["a"],
            "estimate": [0.66],
            "low": [0.65],
            "high": [0.67],
            "odds_ratio": [5.07],
            "or_low": [4.84],
            "or_high": [5.31],
            "share": [-0.05],
            "share_low": [-0.06],
            "share_high": [-0.04],
        }
    ).to_csv(tmp_path / "m" / "v.csv", index=False)
    render._table.cache_clear()
    assert render.render_text("{{m/v|term=a|estimate|ci:2}}") == "0.66 (0.65–0.67)"
    assert render.render_text("{{m/v|term=a|odds_ratio|ci:2@or}}") == "5.07 (4.84–5.31)"
    assert render.render_text("{{m/v|term=a|share|cipct:0}}") == "-5% (-6 to -4%)"
    render._table.cache_clear()
