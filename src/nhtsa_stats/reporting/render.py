"""Render report templates whose numbers are looked up in the output tables.

Every quantitative statement in ``reports/*.md`` is written in ``reports/templates/*.md`` as a
placeholder that is resolved against ``outputs/tables`` when the report is rendered, so the
reports cannot drift from the analysis outputs and every number has a traceable source.

Placeholder grammar::

    {{module/table|filters|column|format}}
    {{json:module/name|dotted.key.path|format}}

* ``filters`` is ``key=value`` pairs separated by semicolons (string comparison); may be empty.
  The filters must select exactly one row, otherwise rendering fails.
* ``format`` is a Python format spec (``.2f``, ``,.0f``) or one of
  ``pct:N`` (x100, N decimals, with %), ``ci:N`` (``est (low–high)`` using the companion
  columns ``<column>_low`` / ``<column>_high``), ``cipct:N`` (the same, x100 with %),
  ``cix1000:N`` (the same, x1000), ``x1000:N`` (x1000), ``pctc:N`` (complement, ``(1-x)`` as
  percent), ``pctsign:N`` (signed percent, ``+8%`` / ``−12%``), ``rnd:K`` (``round(x, K)`` with
  thousands separators, e.g. ``rnd:-2`` gives ``11,800``), ``x:N`` (ratio such as ``2.2×``),
  ``in10`` (``6 in 10``) and ``oneinN`` (``1 in 4``).
* A filter value ``a~b`` matches either ``a`` or ``b``.
* ``column`` may be ``min(col)`` or ``max(col)``: the minimum / maximum of ``col`` over all
  rows the filters select (any number of rows).

Unresolvable placeholders raise ``RenderError`` listing every failure.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from nhtsa_stats import config

PLACEHOLDER = re.compile(r"\{\{(.+?)\}\}", re.DOTALL)
TEMPLATE_DIR = config.PROJECT_ROOT / "reports" / "templates"
REPORT_DIR = config.PROJECT_ROOT / "reports"
# Templates written to the repository root instead of ``reports/`` (README.md is generated too).
ROOT_TEMPLATES = frozenset({"README.md"})


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

    if fmt.startswith(("ci:", "cipct:", "cix1000:")):
        # "ci:2" reads <column>_low/_high (or plain low/high); "ci:2@or" reads or_low/or_high.
        kind, nd = fmt.split(":")
        nd, _, prefix = nd.partition("@")
        nd = int(nd)
        lo_col, hi_col = (f"{prefix or column}_low", f"{prefix or column}_high")
        if not prefix and row is not None and lo_col not in row and "low" in row:
            lo_col, hi_col = "low", "high"
        if row is None or lo_col not in row or hi_col not in row:
            raise RenderError(f"CI columns {lo_col}/{hi_col} missing")
        mult, suf = {"cipct": (100.0, "%"), "cix1000": (1000.0, ""), "ci": (1.0, "")}[kind]
        est, lo, hi = (mult * num(row[c]) for c in (column, lo_col, hi_col))
        sep = " to " if min(lo, hi) < 0 else "–"  # "-6–-4" is unreadable
        return f"{est:.{nd}f}{suf} ({lo:.{nd}f}{sep}{hi:.{nd}f}{suf})"
    if fmt.startswith("pct:"):
        return f"{100 * num(value):.{int(fmt[4:])}f}%"
    if fmt.startswith("x1000:"):
        return f"{1000 * num(value):.{int(fmt[6:])}f}"
    if fmt.startswith("pctc:"):
        return f"{100 * (1 - num(value)):.{int(fmt[5:])}f}%"
    if fmt.startswith("pctsign:"):
        nd = int(fmt[8:])
        pct = 100 * num(value)
        text = f"{abs(pct):.{nd}f}"
        if float(text) == 0:
            return f"{text}%"
        return f"{'+' if pct > 0 else chr(0x2212)}{text}%"
    if fmt.startswith("rnd:"):
        return f"{round(num(value), int(fmt[4:])):,.0f}"
    if fmt.startswith("mn:"):
        # Millions, e.g. "mn:1" renders 5_312_000 as "5.3" (the template adds "million").
        return f"{num(value) / 1e6:.{int(fmt[3:])}f}"
    if fmt.startswith("x:"):
        return f"{num(value):.{int(fmt[2:])}f}\u00d7"
    if fmt == "in10":
        return f"{round(num(value) * 10)} in 10"
    if fmt == "oneinN":
        return f"1 in {round(1 / num(value))}"
    if fmt == "":
        return str(value)
    try:
        return format(num(value), fmt)
    except (TypeError, ValueError):
        return format(value, fmt)


def _filtered(table: str, filters: str, spec: str) -> pd.DataFrame:
    df = _table(table)
    mask = pd.Series(True, index=df.index)
    if filters:
        for f in filters.split(";"):
            k, v = (x.strip() for x in f.split("=", 1))
            if k not in df.columns:
                raise RenderError(f"{table}: no column {k!r} (filter in {spec})")
            vals = [x.strip() for x in v.split("~")]  # "a~b" matches either value
            mask &= df[k].map(_norm).isin(vals)
    return df[mask]


def mdtable(spec: str) -> str:
    """``mdtable:module/table|filters|col:Header:fmt;col:Header:fmt`` -> markdown table of the
    matching rows (in table order).  ``fmt`` may itself contain ':' (e.g. ``ci:2``)."""
    parts = [p.strip() for p in spec.split("|")]
    if len(parts) != 3:
        raise RenderError(f"mdtable needs table|filters|columns: {spec}")
    table, filters, cols = parts[0][len("mdtable:") :], parts[1], parts[2]
    rows = _filtered(table, filters, spec)
    if rows.empty:
        raise RenderError(f"{table}: mdtable filters {filters!r} matched no rows")
    columns = []
    for c in cols.split(";"):
        name, header, *fmt = c.split(":")
        if name not in rows.columns:
            raise RenderError(f"{table}: no column {name!r} in mdtable")
        columns.append((name, header or name, ":".join(fmt)))
    lines = ["| " + " | ".join(h for _, h, _ in columns) + " |", "|" + "---|" * len(columns)]
    for _, r in rows.iterrows():
        cells = []
        for name, _, fmt in columns:
            v = r[name]
            cells.append("—" if pd.isna(v) else _fmt(v, fmt, r, name))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def resolve(spec: str) -> str:
    if spec.startswith("mdtable:"):
        return mdtable(spec)
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
    rows = _filtered(table, filters, spec)
    agg = re.fullmatch(r"(min|max)\((\w+)\)", column)
    if agg:
        how, col = agg.groups()
        if col not in df.columns or rows.empty:
            raise RenderError(f"{table}: cannot aggregate {column!r} over {len(rows)} rows: {spec}")
        return _fmt(getattr(rows[col], how)(), fmt)
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


def render_all(
    template_dir: Path = TEMPLATE_DIR,
    out_dir: Path = REPORT_DIR,
    root_dir: Path | None = None,
) -> list[Path]:
    """Render every template; ``ROOT_TEMPLATES`` (README.md) go to ``root_dir``
    (the repository root by default), the rest to ``out_dir``."""
    root_dir = config.PROJECT_ROOT if root_dir is None else root_dir
    _table.cache_clear()
    _json.cache_clear()
    written = []
    for tpl in sorted(template_dir.glob("*.md")):
        header = (
            f"<!-- Generated from reports/templates/{tpl.name} by `nhtsa analyze report`; "
            "every number is looked up in outputs/tables. Edit the template, not this file. -->\n\n"
        )
        out = (root_dir if tpl.name in ROOT_TEMPLATES else out_dir) / tpl.name
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
