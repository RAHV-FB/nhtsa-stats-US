"""Render report templates whose numbers are looked up in the output tables.

Every quantitative statement in ``reports/*.md`` is written in ``reports/templates/*.md`` as a
placeholder that is resolved against ``outputs/tables`` when the report is rendered, so the
reports cannot drift from the analysis outputs and every number has a traceable source.

Placeholder grammar::

    {{module/table|filters|column|format}}
    {{json:module/name|dotted.key.path|format}}

* ``filters`` is ``key=value`` pairs separated by commas (string comparison); may be empty.
  The filters must select exactly one row, otherwise rendering fails.
* ``format`` is a Python format spec (``.2f``, ``,.0f``) or one of
  ``pct:N`` (x100, N decimals, with %), ``ci:N`` (``est (low–high)`` using the companion
  columns ``<column>_low`` / ``<column>_high``; columns named ``*_rr``/``adj_rr``/``rr`` also
  accept ``<column>_low``), ``cipct:N`` (the same, x100 with %), ``x1000:N`` (x1000).

Unresolvable placeholders raise ``RenderError`` listing every failure.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from nhtsa_stats import config

PLACEHOLDER = re.compile(r"\{\{(.+?)\}\}")
TEMPLATE_DIR = config.PROJECT_ROOT / "reports" / "templates"
REPORT_DIR = config.PROJECT_ROOT / "reports"


class RenderError(RuntimeError):
    pass


@lru_cache(maxsize=256)
def _table(path: str) -> pd.DataFrame:
    p = config.TABLES_DIR / f"{path}.csv"
    if not p.exists():
        raise RenderError(f"table not found: {p}")
    return pd.read_csv(p)


@lru_cache(maxsize=64)
def _json(path: str):
    p = config.TABLES_DIR / f"{path}.json"
    if not p.exists():
        raise RenderError(f"json not found: {p}")
    return json.loads(p.read_text())


def _norm(v) -> str:
    """String form used for filter matching: 2016.0 -> '2016', 'yes' -> 'yes'."""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _fmt(value, fmt: str, row: pd.Series | None = None, column: str | None = None) -> str:
    def num(v):
        return float(v)

    if fmt.startswith(("ci:", "cipct:")):
        kind, nd = fmt.split(":")
        nd = int(nd)
        lo_col, hi_col = f"{column}_low", f"{column}_high"
        if row is None or lo_col not in row or hi_col not in row:
            raise RenderError(f"CI columns {lo_col}/{hi_col} missing")
        mult, suf = (100.0, "%") if kind == "cipct" else (1.0, "")
        est, lo, hi = (mult * num(row[c]) for c in (column, lo_col, hi_col))
        return f"{est:.{nd}f}{suf} ({lo:.{nd}f}–{hi:.{nd}f}{suf})"
    if fmt.startswith("pct:"):
        return f"{100 * num(value):.{int(fmt[4:])}f}%"
    if fmt.startswith("x1000:"):
        return f"{1000 * num(value):.{int(fmt[6:])}f}"
    if fmt == "":
        return str(value)
    try:
        return format(num(value), fmt)
    except (TypeError, ValueError):
        return format(value, fmt)


def resolve(spec: str) -> str:
    parts = [p.strip() for p in spec.split("|")]
    if parts[0].startswith("json:"):
        if len(parts) not in (2, 3):
            raise RenderError(f"bad json placeholder: {spec}")
        obj = _json(parts[0][5:])
        for key in parts[1].split("."):
            obj = obj[int(key)] if isinstance(obj, list) else obj[key]
        return _fmt(obj, parts[2] if len(parts) == 3 else "")
    if len(parts) != 4:
        raise RenderError(f"placeholder needs 4 fields (table|filters|column|format): {spec}")
    table, filters, column, fmt = parts
    df = _table(table)
    mask = pd.Series(True, index=df.index)
    if filters:
        for f in filters.split(","):
            k, v = (x.strip() for x in f.split("=", 1))
            if k not in df.columns:
                raise RenderError(f"{table}: no column {k!r} (filter in {spec})")
            mask &= df[k].map(_norm) == v
    rows = df[mask]
    if len(rows) != 1:
        raise RenderError(f"{table}: filters {filters!r} matched {len(rows)} rows (need 1): {spec}")
    if column not in df.columns:
        raise RenderError(f"{table}: no column {column!r}: {spec}")
    row = rows.iloc[0]
    return _fmt(row[column], fmt, row, column)


def render_text(text: str) -> str:
    errors = []

    def sub(m: re.Match) -> str:
        try:
            return resolve(m.group(1))
        except (RenderError, KeyError, IndexError, ValueError) as exc:
            errors.append(f"{m.group(0)} -> {exc}")
            return m.group(0)

    out = PLACEHOLDER.sub(sub, text)
    if errors:
        raise RenderError("unresolved placeholders:\n" + "\n".join(errors))
    return out


def render_all(template_dir: Path = TEMPLATE_DIR, out_dir: Path = REPORT_DIR) -> list[Path]:
    _table.cache_clear()
    _json.cache_clear()
    written = []
    for tpl in sorted(template_dir.glob("*.md")):
        header = (
            f"<!-- Generated from reports/templates/{tpl.name} by `nhtsa analyze report`; "
            "every number is looked up in outputs/tables. Edit the template, not this file. -->\n\n"
        )
        out = out_dir / tpl.name
        out.write_text(header + render_text(tpl.read_text()))
        written.append(out)
    for tpl in sorted(template_dir.glob("*.json")):
        out = out_dir / tpl.name
        out.write_text(render_text(tpl.read_text()))
        json.loads(out.read_text())  # must remain valid JSON
        written.append(out)
    return written


def run() -> dict:
    return {"written": [str(p) for p in render_all()]}
