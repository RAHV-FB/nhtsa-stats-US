"""Render the public website, ``website/index.html``, from ``website/templates/index.html``.

Every number and chart on the page is looked up in ``outputs/tables`` when the page is built, so
nothing can be typed by hand or drift from the analysis. The template uses the placeholder grammar
of :mod:`nhtsa_stats.reporting.render` (``{{module/table|filters|column|format}}``) plus these
directives, which only this renderer understands:

* ``{{chart:<id>}}``  the plot and the "Show the data" table of a registered chart (see ``CHARTS``);
* ``{{statestable}}``  the sortable states table;
* ``{{asset:css}}`` / ``{{asset:js}}``  ``website/assets/site.css`` / ``site.js``, inlined, so the
  generated page is one self-contained file.

The builders below only select, order, sum two rows of one table for a display bucket, and index a
series to a base year. They compute no other statistics.
"""

from __future__ import annotations

import html
import json
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from itertools import pairwise

import pandas as pd

from nhtsa_stats import config
from nhtsa_stats.reporting import render

SITE_DIR = config.PROJECT_ROOT / "website"
TEMPLATE = SITE_DIR / "templates" / "index.html"
OUTPUT = SITE_DIR / "index.html"
ASSETS = SITE_DIR / "assets"

MINUS = "−"
EN = "–"
# Narrowest bar a segmented bar is laid out in: a 320px viewport minus page gutter, figure padding
# and border. A share is printed inside its block only if the text fits in that width.
SEG_MIN_BAR_W = 258
SEG_CHAR_W = 7.5
SEG_PAD = 10


class SiteError(RuntimeError):
    pass


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def fv(value: float, fmt: str) -> str:
    """Format a value with the report renderer's format grammar."""
    return render._fmt(value, fmt)


# ---------------------------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------------------------


def table(path: str) -> pd.DataFrame:
    return render._table(path)


def pick(path: str, **keys: object) -> pd.Series:
    """The single row of ``path`` whose columns equal ``keys`` (compared as strings)."""
    df = table(path)
    mask = pd.Series(True, index=df.index)
    for col, val in keys.items():
        if col not in df.columns:
            raise SiteError(f"{path}: no column {col!r}")
        mask &= df[col].map(render._norm) == str(val)
    rows = df[mask]
    if len(rows) != 1:
        raise SiteError(f"{path}: {keys} matched {len(rows)} rows (need 1)")
    return rows.iloc[0]


# ---------------------------------------------------------------------------------------------
# Scales
# ---------------------------------------------------------------------------------------------


def nice_ceil(x: float) -> float:
    """Smallest 'round' number (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8 x 10^k) that is >= x."""
    if x <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(x))
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= x * (1 - 1e-9):
            return round(m * e, 10)
    return round(10 * e, 10)


def nice_step(span: float, max_intervals: int = 5) -> float:
    """A round step (1, 2, 2.5, 5 x 10^k) giving at most ``max_intervals`` intervals over ``span``."""
    e = 10 ** math.floor(math.log10(span / max_intervals))
    for m in (1, 2, 2.5, 5, 10):
        if span / (m * e) <= max_intervals + 1e-9:
            return m * e
    return 10 * e


def _ticks_at(lo: float, hi: float, step: float) -> list[float]:
    out, v = [], math.ceil(lo / step - 1e-9) * step
    while v <= hi + step * 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def nice_ticks(lo: float, hi: float, max_intervals: int = 5) -> list[float]:
    """Clean tick values in [lo, hi] with at most ``max_intervals`` intervals."""
    span = hi - lo
    if span <= 0:
        return [lo]
    return _ticks_at(lo, hi, nice_step(span, max_intervals))


def pos(v: float, lo: float, hi: float) -> float:
    """Position of ``v`` on a [lo, hi] domain as a percentage."""
    return 100.0 * (v - lo) / (hi - lo)


def check_domain(what: str, values: Sequence[float | None], lo: float, hi: float) -> None:
    """A chart with a fixed scale must raise rather than draw a value outside it."""
    for v in values:
        if v is not None and not (lo - 1e-9 <= v <= hi + 1e-9):
            raise SiteError(f"{what}: value {v} lies outside the fixed scale [{lo}, {hi}]")


def p(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".") or "0"


# ---------------------------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------------------------

NUMLIKE = re.compile(r"^[+−-]?[\d,.]+(%|×)?( \(.*\))?$")


def dataview(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """The "Show the data" table under every chart: exactly the values plotted."""
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = []
    for r in rows:
        cells = [f'<th scope="row">{esc(r[0])}</th>']
        for c in r[1:]:
            cls = ' class="num"' if NUMLIKE.match(str(c)) else ""
            cells.append(f"<td{cls}>{esc(c)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<details class="dataview"><summary>Show the data</summary><div class="table-wrap">'
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"
        "</div></details>"
    )


def legend(items: Sequence[tuple[str, str]], kind: str = "swatch") -> str:
    """Legend of (name, colour token) in series order, no numbers."""
    lis = "".join(
        f'<li><i class="sw sw-{kind}" style="background:var(--{c})"></i>{esc(n)}</li>'
        for n, c in items
    )
    return f'<ul class="legend">{lis}</ul>'


def tip_attrs(text: str) -> str:
    t = esc(text)
    return f'data-tip="{t}" title="{t}"'


@dataclass
class Bar:
    label: str
    value: float
    low: float | None = None
    high: float | None = None
    color: str = "accent"
    strong: bool = False
    gap: bool = False
    label_html: str | None = None  # trusted, pre-escaped markup that replaces the text label
    extra: dict[str, str] = field(default_factory=dict)  # additional table-view columns
    tip_note: str = ""


def _value_tip(b: Bar, fmt: str) -> str:
    text = f"{b.label}: {fv(b.value, fmt)}"
    if b.low is not None and b.high is not None:
        text += f" (95% CI {fv(b.low, fmt)}{EN}{fv(b.high, fmt)})"
    return text + (f" {b.tip_note}" if b.tip_note else "")


def _bar_table(
    bars: Sequence[Bar], fmt: str, value_header: str, label_header: str, group: str | None = None
) -> tuple[list[str], list[list[str]]]:
    has_ci = any(b.low is not None for b in bars)
    extra_keys: list[str] = []
    for b in bars:
        for k in b.extra:
            if k not in extra_keys:
                extra_keys.append(k)
    headers = [label_header, value_header]
    if has_ci:
        headers += ["95% interval low", "95% interval high"]
    headers += extra_keys
    rows = []
    for b in bars:
        r = [b.label, fv(b.value, fmt)]
        if has_ci:
            r += [fv(b.low, fmt), fv(b.high, fmt)] if b.low is not None else ["", ""]
        r += [b.extra.get(k, "") for k in extra_keys]
        rows.append(r)
    return headers, rows


# ---------------------------------------------------------------------------------------------
# Horizontal bars (hbars, pairbars)
# ---------------------------------------------------------------------------------------------


def _hb_line(
    b: Bar, fmt: str, lo: float, hi: float, thick: int, tip: str | None = None, color: str = ""
) -> str:
    """One bar with optional CI whisker and value label, in a plot spanning [lo, hi]."""
    z = pos(0, lo, hi)
    pv = pos(b.value, lo, hi)
    color = color or b.color
    negative = b.value < 0
    left, width = (pv, z - pv) if negative else (z, pv - z)
    out = [
        f'<i class="hb-bar {"neg" if negative else "pos"}" '
        f'style="left:{p(left)}%;width:{p(width)}%;height:{thick}px;'
        f'background:var(--{color})"></i>'
    ]
    reach_hi = pv
    reach_lo = pv
    if b.low is not None and b.high is not None:
        pl, ph = pos(b.low, lo, hi), pos(b.high, lo, hi)
        out.append(f'<i class="hb-ci" style="left:{p(pl)}%;width:{p(ph - pl)}%"></i>')
        reach_hi, reach_lo = max(ph, pv), min(pl, pv)
    text = esc(fv(b.value, fmt))
    if negative:
        out.append(f'<span class="hb-val neg" style="right:{p(100 - reach_lo)}%">{text}</span>')
    else:
        out.append(f'<span class="hb-val" style="left:{p(reach_hi)}%">{text}</span>')
    t = tip if tip is not None else _value_tip(b, fmt)
    return f'<div class="hb-line" style="height:{thick}px" {tip_attrs(t)}>{"".join(out)}</div>'


def _tick_fmt(tick_fmt: str, ticks: Sequence[float]) -> str:
    """An axis never prints two ticks alike: widen ``x:0`` to one decimal for fractional ticks."""
    if tick_fmt.startswith("x:0") and any(abs(t - round(t)) > 1e-9 for t in ticks):
        return "x:1"
    return tick_fmt


def _hb_grid(ticks: Sequence[float], lo: float, hi: float) -> str:
    return "".join(f'<i class="hb-grid" style="left:{p(pos(t, lo, hi))}%"></i>' for t in ticks)


def _hb_label(b_label: str, html_label: str | None = None, strong: bool = False) -> str:
    inner = html_label if html_label is not None else esc(b_label)
    if strong:
        inner = f"<strong>{inner}</strong>"
    return f'<div class="hb-label">{inner}</div>'


def _hb_axis(ticks, lo, hi, tick_fmt) -> str:
    spans = "".join(
        f'<span class="hb-tick" style="left:{p(pos(t, lo, hi))}%">{esc(fv(t, tick_fmt))}</span>'
        for t in ticks
    )
    return (
        '<div class="hb-row hb-axis" aria-hidden="true"><div class="hb-label"></div>'
        f'<div class="hb-plot">{spans}</div></div>'
    )


def _hb_refhead(ref, fmt, lo, hi) -> str:
    value, label = ref
    text = esc(f"{label} {fv(value, fmt)}")
    return (
        '<div class="hb-row hb-head"><div class="hb-label"></div><div class="hb-plot">'
        f'<span class="hb-reflabel" style="left:{p(pos(value, lo, hi))}%">{text}</span>'
        "</div></div>"
    )


def hbars(
    rows: Sequence[Bar] | None,
    *,
    fmt: str,
    value_header: str = "Value",
    label_header: str = "",
    ref: tuple[float, str] | None = None,
    vmax: float | None = None,
    tick_fmt: str | None = None,
    groups: Sequence[tuple[str, Sequence[Bar]]] | None = None,
    ref_fmt: str | None = None,
) -> str:
    """Horizontal ranked bars, optionally with CI whiskers, a reference line and groups that
    share one scale."""
    tick_fmt = tick_fmt or fmt
    all_bars = [b for _, g in groups for b in g] if groups else list(rows or [])
    if vmax is None:
        top = max((b.high if b.high is not None else b.value) for b in all_bars)
        vmax = nice_ceil(top)
    lo, hi = 0.0, float(vmax)
    check_domain(
        "horizontal bars",
        [x for b in all_bars for x in (b.value, b.low, b.high)] + ([ref[0]] if ref else []),
        lo,
        hi,
    )
    ticks = nice_ticks(lo, hi)
    grid = _hb_grid(ticks, lo, hi)
    refline = (
        f'<i class="hb-ref" style="left:{p(pos(ref[0], lo, hi))}%"></i>' if ref is not None else ""
    )

    def row_html(b: Bar) -> str:
        cls = " hb-gap" if b.gap else ""
        return (
            f'<div class="hb-row{cls}">{_hb_label(b.label, b.label_html, b.strong)}'
            f'<div class="hb-plot">{grid}{refline}{_hb_line(b, fmt, lo, hi, 18)}</div></div>'
        )

    parts = ['<div class="chart hb">']
    if ref is not None:
        parts.append(_hb_refhead(ref, ref_fmt or fmt, lo, hi))
    table_rows: list[list[str]] = []
    headers: list[str] = []
    if groups:
        for title, g in groups:
            parts.append(f'<p class="hb-group-title">{esc(title)}</p>')
            parts.extend(row_html(b) for b in g)
            h, r = _bar_table(g, fmt, value_header, label_header)
            headers = ["Group", *h]
            table_rows.extend([[title, *x] for x in r])
    else:
        parts.extend(row_html(b) for b in all_bars)
        headers, table_rows = _bar_table(all_bars, fmt, value_header, label_header)
    parts.append(_hb_axis(ticks, lo, hi, _tick_fmt(tick_fmt, ticks)))
    parts.append("</div>")
    return "".join(parts) + dataview(headers, table_rows)


@dataclass
class Indicator:
    label: str
    values: list[float | None]
    extra: dict[str, str] = field(default_factory=dict)


def pairbars(
    indicators: Sequence[Indicator],
    series: Sequence[tuple[str, str]],
    *,
    fmt: str,
    label_header: str = "",
    vmax: float | None = None,
    diverging: bool = False,
) -> str:
    """Two (or more) bars per indicator, one per comparison group, with a legend at top left.

    ``diverging`` lets values go below zero: negative bars extend left from the zero baseline."""
    vals = [v for i in indicators for v in i.values if v is not None]
    if diverging:
        lo = min(0.0, min(vals))
        hi = max(0.0, max(vals))
        span_hi = nice_ceil(hi) if hi > 0 else 0.0
        hi = vmax if vmax is not None else span_hi
        if lo < 0:
            lo = -nice_ceil(-lo)
        check_domain("paired bars", vals, lo, hi)
    else:
        lo, hi = 0.0, float(vmax if vmax is not None else nice_ceil(max(vals)))
    check_domain("paired bars", vals, lo, hi)
    ticks = nice_ticks(lo, hi)
    grid = _hb_grid(ticks, lo, hi)
    zero = f'<i class="hb-zero" style="left:{p(pos(0, lo, hi))}%"></i>' if lo < 0 else ""
    out = ['<div class="chart hb hb-pair' + (' is-div"' if lo < 0 else '"') + ">"]
    out.append(legend(list(series)))
    for ind in indicators:
        lines = []
        for (name, color), v in zip(series, ind.values, strict=True):
            if v is None:
                continue
            b = Bar(label=f"{ind.label} ({name})", value=v, color=color)
            lines.append(_hb_line(b, fmt, lo, hi, 14, tip=f"{ind.label}, {name}: {fv(v, fmt)}"))
        out.append(
            f'<div class="hb-row">{_hb_label(ind.label)}'
            f'<div class="hb-plot">{grid}{zero}<div class="hb-stack">{"".join(lines)}</div></div>'
            "</div>"
        )
    out.append(_hb_axis(ticks, lo, hi, fmt))
    out.append("</div>")
    extra_keys: list[str] = []
    for i in indicators:
        for k in i.extra:
            if k not in extra_keys:
                extra_keys.append(k)
    headers = [label_header, *[n for n, _ in series], *extra_keys]
    rows = [
        [
            i.label,
            *[fv(v, fmt) if v is not None else "" for v in i.values],
            *[i.extra.get(k, "") for k in extra_keys],
        ]
        for i in indicators
    ]
    return "".join(out) + dataview(headers, rows)


# ---------------------------------------------------------------------------------------------
# Segmented bars
# ---------------------------------------------------------------------------------------------


@dataclass
class Part:
    name: str
    value: float
    color: str
    members: list[tuple[str, float]] | None = None  # underlying rows when a part sums several


def seg_fits(text: str, share: float) -> bool:
    """Does ``text`` fit inside a block holding ``share`` of the bar at the narrowest layout?"""
    return len(text) * SEG_CHAR_W + SEG_PAD <= share * SEG_MIN_BAR_W


def segbar(
    groups: Sequence[tuple[str | None, Sequence[Part]]],
    *,
    fmt: str = "pct:0",
    name_header: str = "",
) -> str:
    """One or more tall (28px) segmented bars with a legend below each and a table view."""
    out = ['<div class="chart seg-set">']
    rows: list[list[str]] = []
    detail = any(pt.members and len(pt.members) > 1 for _, parts in groups for pt in parts)
    for title, parts in groups:
        total = sum(pt.value for pt in parts)
        blocks, alts = [], []
        for pt in parts:
            share = pt.value / total
            text = fv(pt.value, fmt)
            inner = ""
            if seg_fits(text, share):
                on = f"seg-on-{pt.color}"
                inner = f'<span class="seg-txt {on}">{esc(text)}</span>'
            blocks.append(
                f'<div class="seg-block" style="flex:{pt.value:.6f} 1 0;'
                f'background:var(--{pt.color})" {tip_attrs(f"{pt.name}: {text}")}>{inner}</div>'
            )
            alts.append(f"{pt.name} {text}")
            if detail:
                mem = pt.members or [(pt.name, pt.value)]
                for m_name, m_val in mem if len(mem) > 1 else [("", pt.value)]:
                    rows.append([*([title] if title else []), pt.name, m_name, fv(m_val, fmt)])
            else:
                rows.append([*([title] if title else []), pt.name, fv(pt.value, fmt)])
        head = f'<p class="seg-title">{esc(title)}</p>' if title else ""
        aria = esc((f"{title}: " if title else "") + "; ".join(alts))
        out.append(
            f'<div class="seg">{head}<div class="seg-bar" role="img" aria-label="{aria}">'
            f"{''.join(blocks)}</div>{legend([(pt.name, pt.color) for pt in parts])}</div>"
        )
    out.append("</div>")
    headers = ([name_header or "Bar"] if groups[0][0] else []) + ["Part"]
    headers += ["Detail"] if detail else []
    headers += ["Share"]
    return "".join(out) + dataview(headers, rows)


# ---------------------------------------------------------------------------------------------
# Vertical charts (columns, strip)
# ---------------------------------------------------------------------------------------------


def _v_grid(ticks, lo, hi, tick_fmt) -> str:
    return "".join(
        f'<i class="vg" style="bottom:{p(pos(t, lo, hi))}%"><b>{esc(fv(t, tick_fmt))}</b></i>'
        for t in ticks
    )


def columns(
    cols: Sequence[Bar],
    *,
    fmt: str,
    value_header: str = "Value",
    label_header: str = "",
    ref: tuple[float, str] | None = None,
    vmax: float | None = None,
    tick_fmt: str | None = None,
) -> str:
    """Vertical columns (few categories) with optional CI whiskers and a reference line."""
    tick_fmt = tick_fmt or fmt
    top = max((c.high if c.high is not None else c.value) for c in cols)
    hi = float(vmax if vmax is not None else nice_ceil(top))
    check_domain(
        "columns",
        [x for c in cols for x in (c.value, c.low, c.high)] + ([ref[0]] if ref else []),
        0,
        hi,
    )
    ticks = nice_ticks(0, hi)
    cells, labels = [], []
    for c in cols:
        top_pct = pos(c.high if c.high is not None else c.value, 0, hi)
        parts = [
            f'<i class="col-bar" style="height:{p(pos(c.value, 0, hi))}%;'
            f'background:var(--{c.color})"></i>'
        ]
        if c.low is not None and c.high is not None:
            lo_p, hi_p = pos(c.low, 0, hi), pos(c.high, 0, hi)
            parts.append(
                f'<i class="col-ci" style="bottom:{p(lo_p)}%;height:{p(hi_p - lo_p)}%"></i>'
            )
        parts.append(
            f'<span class="col-val" style="bottom:calc({p(top_pct)}% + 6px)">'
            f"{esc(fv(c.value, fmt))}</span>"
        )
        cells.append(
            f'<div class="col-cell" {tip_attrs(_value_tip(c, fmt))}>{"".join(parts)}</div>'
        )
        inner = c.label_html if c.label_html is not None else esc(c.label)
        labels.append(f'<div class="col-label">{inner}</div>')
    refhtml, refkey = "", ""
    if ref is not None:
        refhtml = f'<i class="vref" style="bottom:{p(pos(ref[0], 0, hi))}%"></i>'
        refkey = f'<p class="ref-key"><i class="ref-sw"></i>{esc(ref[1])} ({esc(fv(ref[0], tick_fmt))})</p>'
    n = len(cols)
    headers, rows = _bar_table(cols, fmt, value_header, label_header)
    return (
        f'<div class="chart cols">{refkey}<div class="vplot">{_v_grid(ticks, 0, hi, _tick_fmt(tick_fmt, ticks))}'
        f'{refhtml}<div class="col-set" style="--n:{n}">{"".join(cells)}</div></div>'
        f'<div class="col-labels" style="--n:{n}">{"".join(labels)}</div></div>'
    ) + dataview(headers, rows)


def strip(
    items: Sequence[Bar],
    *,
    fmt: str,
    ref: tuple[float, str],
    label_header: str = "",
    value_header: str = "Value",
    vmax: float | None = None,
) -> str:
    """Many thin sorted columns (one per state). Only the highest, the lowest and the reference
    are labelled on the chart; every value is in the tooltip and the table view."""
    items = sorted(items, key=lambda b: -b.value)
    hi = float(vmax if vmax is not None else nice_ceil(max(b.value for b in items)))
    check_domain("state strip", [b.value for b in items] + [ref[0]], 0, hi)
    ticks = nice_ticks(0, hi)
    cells = []
    for i, b in enumerate(items):
        extra = ""
        if i in (0, len(items) - 1):
            side = "l" if i == 0 else "r"
            top_pct = pos(b.value, 0, hi)
            extra = (
                f'<i class="vlead" style="bottom:{p(top_pct)}%"></i>'
                f'<span class="vlabel vlabel-{side}">{esc(b.label)} {esc(fv(b.value, fmt))}</span>'
            )
        cells.append(
            f'<div class="col-cell" {tip_attrs(_value_tip(b, fmt))}>'
            f'<i class="col-bar" style="height:{p(pos(b.value, 0, hi))}%;'
            f'background:var(--{b.color})"></i>{extra}</div>'
        )
    refline = f'<i class="vref" style="bottom:{p(pos(ref[0], 0, hi))}%"></i>'
    reflab = (
        f'<span class="vreflabel" style="bottom:{p(pos(ref[0], 0, hi))}%">'
        f"{esc(ref[1])} {esc(fv(ref[0], fmt))}</span>"
    )
    headers, rows = _bar_table(items, fmt, value_header, label_header)
    return (
        f'<div class="chart cols strip"><div class="vplot">{_v_grid(ticks, 0, hi, fmt)}{refline}'
        f'{reflab}<div class="col-set" style="--n:{len(items)}">{"".join(cells)}</div></div></div>'
    ) + dataview(headers, rows)


# ---------------------------------------------------------------------------------------------
# Line charts
# ---------------------------------------------------------------------------------------------


@dataclass
class Line:
    name: str
    values: list[float]
    color: str = "accent"
    end_label: bool = True
    label_idx: list[int] = field(default_factory=list)  # points that carry a value label
    width: float = 2.0


LAYOUTS = {
    # name: (viewBox width, height, left, right, top, bottom, end labels carry the series name)
    "wide": (720, 300, 44, 148, 18, 30, True),
    "narrow": (360, 260, 40, 40, 18, 28, False),
}


def _wrap_name(name: str, width: int = 22) -> list[str]:
    words, lines, cur = name.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return [*lines, cur] if cur else lines


def _spread(ys: list[float], gap: float) -> list[float]:
    """Nudge label positions apart so neighbours are at least ``gap`` apart (rarely needed)."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for a, b in pairwise(order):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out


def _svg_lines(
    layout: str,
    lines: Sequence[Line],
    xs: Sequence[str],
    fmt: str,
    ylo: float,
    yhi: float,
    ticks: Sequence[float],
    base: float | None,
    end_fmt: str,
) -> str:
    w, h, ml, mr, mt, mb, named = LAYOUTS[layout]
    x0, x1, y0, y1 = ml, w - mr, mt, h - mb
    n = len(xs)

    def X(i: int) -> float:
        return x0 + i * (x1 - x0) / (n - 1)

    def Y(v: float) -> float:
        return y1 - (v - ylo) / (yhi - ylo) * (y1 - y0)

    out = [
        f'<svg class="ln ln-{layout}" viewBox="0 0 {w} {h}" data-x0="{x0}" data-x1="{x1}" '
        f'data-y0="{y0}" data-y1="{y1}" focusable="false" aria-hidden="true">'
    ]
    for t in ticks:
        cls = "ln-grid ln-base" if base is not None and abs(t - base) < 1e-9 else "ln-grid"
        out.append(f'<line class="{cls}" x1="{x0}" x2="{x1}" y1="{Y(t):.2f}" y2="{Y(t):.2f}"/>')
        out.append(
            f'<text class="ln-tick" x="{x0 - 8}" y="{Y(t) + 4:.2f}" text-anchor="end">'
            f"{esc(fv(t, fmt))}</text>"
        )
    step = 1 if layout == "wide" or n <= 5 else 2
    for i, label in enumerate(xs):
        if i % step == 0:
            out.append(
                f'<text class="ln-tick" x="{X(i):.2f}" y="{h - 8}" text-anchor="middle">'
                f"{esc(label)}</text>"
            )
    single = len(lines) == 1
    if single:
        ln = lines[0]
        pts = " ".join(f"{X(i):.2f},{Y(v):.2f}" for i, v in enumerate(ln.values))
        out.append(f'<polygon class="ln-area" points="{X(0):.2f},{y1} {pts} {X(n - 1):.2f},{y1}"/>')
    for ln in lines:
        pts = " ".join(f"{X(i):.2f},{Y(v):.2f}" for i, v in enumerate(ln.values))
        out.append(
            f'<polyline class="ln-line" points="{pts}" '
            f'style="stroke:var(--{ln.color});stroke-width:{ln.width:g}"/>'
        )
    # end labels (name + value on wide, value only on narrow) with minimal de-collision
    ends = [ln for ln in lines if ln.end_label]
    label_h = 14 * (2 if named else 1)
    ys = _spread([Y(ln.values[-1]) for ln in ends], label_h)
    for ln, ly in zip(ends, ys, strict=True):
        val = esc(fv(ln.values[-1], end_fmt))
        cx = X(n - 1)
        if named and len(lines) > 1:
            name_lines = _wrap_name(ln.name)
            tsp = []
            for k, t in enumerate(name_lines):
                tail = (
                    f' <tspan class="ln-endval">{val}</tspan>' if k == len(name_lines) - 1 else ""
                )
                tsp.append(
                    f'<tspan x="{cx + 10:.2f}" dy="{0 if k == 0 else 14}">{esc(t)}{tail}</tspan>'
                )
            top = ly - 7 * (len(name_lines) - 1) + 4
            out.append(
                f'<text class="ln-end" x="{cx + 10:.2f}" y="{top:.2f}">{"".join(tsp)}</text>'
            )
        else:
            out.append(
                f'<text class="ln-end ln-endval" x="{cx + 10:.2f}" y="{ly + 4:.2f}">{val}</text>'
            )
    # dots: end points of end-labelled lines, and labelled points of single-series charts
    for ln in lines:
        marks = set(ln.label_idx)
        if ln.end_label:
            marks.add(n - 1)
        for i in sorted(marks):
            v = ln.values[i]
            nb = [ln.values[j] for j in (i - 1, i + 1) if 0 <= j < n]
            below = ln.label_idx and all(v < q for q in nb)
            if i in ln.label_idx:
                ty = Y(v) + 20 if below else Y(v) - 10
                out.append(
                    f'<text class="ln-val" x="{X(i):.2f}" y="{ty:.2f}" text-anchor="middle">'
                    f"{esc(fv(v, end_fmt))}</text>"
                )
            tip = f"{ln.name}, {xs[i]}: {fv(v, end_fmt)}"
            out.append(
                f'<circle class="ln-dot" cx="{X(i):.2f}" cy="{Y(v):.2f}" r="4" '
                f'style="fill:var(--{ln.color})" {tip_attrs(tip)}/>'
            )
    out.append(f'<line class="ln-xhair" x1="0" x2="0" y1="{y0}" y2="{y1}" hidden/>')
    out.append(
        f'<rect class="ln-hit" x="{x0 - 4}" y="{y0}" width="{x1 - x0 + 8}" height="{y1 - y0}"/>'
    )
    out.append("</svg>")
    return "".join(out)


def lines_chart(
    series: Sequence[Line],
    xs: Sequence[str],
    *,
    fmt: str,
    tick_fmt: str | None = None,
    end_fmt: str | None = None,
    ydomain: tuple[float, float] | None = None,
    base: float | None = None,
    x_header: str = "Year",
) -> str:
    """SVG line chart. Two SVGs (wide and narrow) are emitted; CSS shows one so text never
    shrinks. The data is embedded as JSON for the crosshair tooltip."""
    tick_fmt = tick_fmt or fmt
    end_fmt = end_fmt or fmt
    if len(series) > 4:
        raise SiteError("a line chart carries at most four series")
    allv = [v for s in series for v in s.values]
    if ydomain is None:
        lo, hi = min(allv), max(allv)
        step = nice_step(hi - lo)
        ylo = math.floor(lo / step + 1e-9) * step
        yhi = math.ceil(hi / step - 1e-9) * step
        ticks = _ticks_at(ylo, yhi, step)
    else:
        ylo, yhi = ydomain
        check_domain("line chart", allv, ylo, yhi)
        ticks = nice_ticks(ylo, yhi)
    data = {
        "xs": list(xs),
        "series": [
            {
                "name": s.name,
                "color": s.color,
                "values": [round(v, 6) for v in s.values],
                "text": [fv(v, end_fmt) for v in s.values],
            }
            for s in series
        ],
    }
    attr = esc(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    leg = legend([(s.name, s.color) for s in series], kind="line") if len(series) > 1 else ""
    svgs = "".join(
        _svg_lines(name, series, xs, tick_fmt, ylo, yhi, ticks, base, end_fmt)
        for name in ("wide", "narrow")
    )
    rows = [[x, *[fv(s.values[i], end_fmt) for s in series]] for i, x in enumerate(xs)]
    return f'<div class="chart lines" data-series="{attr}">{leg}{svgs}</div>' + dataview(
        [x_header, *[s.name for s in series]], rows
    )


# ---------------------------------------------------------------------------------------------
# Chart registry
# ---------------------------------------------------------------------------------------------

CHARTS: dict[str, Callable[[], str]] = {}


def chart(name: str):
    def deco(fn: Callable[[], str]):
        CHARTS[name] = fn
        return fn

    return deco


def _ceil_tenth(x: float) -> float:
    return math.ceil(x * 10 - 1e-9) / 10


@chart("behaviours")
def _behaviours() -> str:
    t = "deaths/behaviour_summary"
    rows = [
        ("alcohol", "Drunk driver (.08 or more)"),
        ("speeding", "Speeding-related crash"),
        ("unbelted", "Victim not wearing a seat belt"),
        ("unhelmeted", "Motorcyclist without a helmet"),
    ]
    bars = [Bar(lab, float(pick(t, row=k)["share_of_all"])) for k, lab in rows]
    any_v = float(pick(t, row="any")["share_of_all"])
    bars.append(Bar("At least one of the four", any_v, color="accent-ink", strong=True, gap=True))
    return hbars(
        bars,
        fmt="pct:1",
        vmax=_ceil_tenth(any_v),
        tick_fmt="pct:0",
        value_header="Share of all deaths",
        label_header="Behaviour",
    )


@chart("overlap")
def _overlap() -> str:
    t = "deaths/behaviour_summary"
    spec = [
        ("exactly_1", "One of the four", "accent"),
        ("exactly_2", "Two", "series-2"),
        ("three_or_more", "Three", "aqua"),
        ("none", "None of the four", "deemph"),
    ]
    parts = [Part(n, float(pick(t, row=k)["share_of_all"]), c) for k, n, c in spec]
    return segbar([(None, parts)], fmt="pct:0")


def _roles_parts(group: str, driver: str, passenger: str) -> list[Part]:
    spec = [
        ("risk_driver", driver, "accent"),
        ("risk_passenger", passenger, "series-2"),
        ("other_vehicle_occupant", "People in other vehicles", "aqua"),
        ("pedestrian_or_cyclist", "Pedestrians and cyclists", "violet"),
        ("other_nonoccupant", "Others", "deemph"),
    ]
    return [
        Part(n, float(pick("deaths/victim_roles", group=group, role=k)["share_of_group"]), c)
        for k, n, c in spec
    ]


@chart("alcohol_victims")
def _alcohol_victims() -> str:
    parts = _roles_parts("alcohol_impaired", "The drunk driver", "Their passengers")
    return segbar([(None, parts)])


@chart("speeding_victims")
def _speeding_victims() -> str:
    parts = _roles_parts("speeding", "The speeding driver", "Their passengers")
    return segbar([(None, parts)])


@chart("truck_victims")
def _truck_victims() -> str:
    parts = _roles_parts("large_truck", "The truck driver", "Truck passengers")
    return segbar([(None, parts)])


@chart("alcohol_records")
def _alcohol_records() -> str:
    t = "deaths/driver_records"
    inds = [
        ("licence_invalid", "No valid licence"),
        ("suspended_or_revoked", "Licence suspended or revoked"),
        ("unlicensed", "Never licensed"),
        ("prior_suspension", "Licence suspended before (since 2018)"),
        ("prior_dwi", "DWI conviction"),
        ("prior_speeding", "Speeding conviction"),
        ("prior_crash", "Recorded crash"),
    ]
    series = [
        ("Drunk drivers (.08 or more)", "series-2", "bac_08_plus"),
        ("Drivers with no alcohol", "accent", "bac_zero"),
    ]
    rows = []
    for key, label in inds:
        recs = [pick(t, group=g, indicator=key) for _, _, g in series]
        extra = {
            f"Drivers with known record: {n.lower() if i else n}": f"{int(r['n_known']):,}"
            for i, ((n, _, _), r) in enumerate(zip(series, recs, strict=True))
        }
        rows.append(Indicator(label, [float(r["share"]) for r in recs], extra))
    return pairbars(
        rows, [(n, c) for n, c, _ in series], fmt="pct:0", label_header="Driver record", vmax=0.3
    )


@chart("unbelted_by")
def _unbelted_by() -> str:
    t = "deaths/restraint"
    spec = [
        (
            "Time of day",
            [("time_of_day", "night", "Night (6 pm–6 am)"), ("time_of_day", "day", "Day")],
        ),
        (
            "Vehicle",
            [
                ("vehicle", "pickup", "Pickup"),
                ("vehicle", "suv", "SUV"),
                ("vehicle", "car", "Car"),
                ("vehicle", "van", "Van"),
            ],
        ),
        ("Sex", [("sex", "male", "Men"), ("sex", "female", "Women")]),
        (
            "Age",
            [
                ("age_band", "16-24", f"16{EN}24"),
                ("age_band", "25-34", f"25{EN}34"),
                ("age_band", "35-54", f"35{EN}54"),
                ("age_band", "55-74", f"55{EN}74"),
                ("age_band", "75+", "75 and over"),
            ],
        ),
    ]
    groups = []
    for title, items in spec:
        bars = []
        for dim, lvl, label in items:
            r = pick(t, dimension=dim, level=lvl)
            bars.append(
                Bar(
                    label,
                    float(r["unbelted_share"]),
                    extra={"Occupants with known belt use": f"{int(r['known']):,}"},
                )
            )
        groups.append((title, bars))
    overall = float(pick(t, dimension="overall", level="all")["unbelted_share"])
    return hbars(
        None,
        groups=groups,
        fmt="pct:0",
        vmax=0.7,
        ref=(overall, "All"),
        value_header="Share unbelted",
        label_header="Group",
    )


@chart("belt_lives")
def _belt_lives() -> str:
    t = "deaths/potential_lives"
    spec = [
        ("as_recorded", "Belt use as recorded"),
        ("misreport_5pct", "If 1 in 20 belted survivors were misrecorded"),
        ("misreport_10pct", "If 1 in 10 were misrecorded"),
        ("misreport_20pct", "If 1 in 5 were misrecorded"),
    ]
    bars = []
    for k, label in spec:
        r = pick(t, measure="seat_belts", scenario=k)
        bars.append(
            Bar(
                label,
                float(r["lives_per_year"]),
                float(r["lives_per_year_low"]),
                float(r["lives_per_year_high"]),
            )
        )
    return hbars(bars, fmt="rnd:-2", value_header="Lives a year", label_header="Assumption")


@chart("speeding_types")
def _speeding_types() -> str:
    t = "severity/fatal_speeding_type"
    spec = [
        ("exceeded_limit_or_racing", "Exceeded the limit or racing"),
        ("speeding_unspecified", "Speeding, kind not recorded"),
        ("too_fast_for_conditions", "Too fast for conditions"),
    ]
    bars = []
    for k, label in spec:
        r = pick(t, outcome="fatal", factor="speeding_type", level=k)
        bars.append(Bar(label, float(r["adj_rr"]), float(r["adj_rr_low"]), float(r["adj_rr_high"])))
    vmax = math.ceil(max(b.high for b in bars))
    return hbars(
        bars,
        fmt="x:2",
        tick_fmt="x:0",
        vmax=vmax,
        ref=(1, "No speeding"),
        ref_fmt="x:1",
        value_header="Adjusted risk ratio",
        label_header="Kind of speeding",
    )


@chart("ped_where")
def _ped_where() -> str:
    t = "deaths/pedestrians"

    def share(dim: str, lvl: str) -> float:
        return float(pick(t, dimension=dim, level=lvl)["share"])

    def part(name, color, dim, *levels) -> Part:
        members = [(f"{dim}: {lv}".replace("_", " "), share(dim, lv)) for lv in levels]
        return Part(name, sum(v for _, v in members), color, members)

    palette = ["accent", "series-2", "aqua", "violet", "deemph"]
    spec = [
        (
            "Light",
            "light",
            [
                ("Daylight", ["daylight"]),
                ("Dark, street lights", ["dark_lighted"]),
                ("Dark, no street lights", ["dark_not_lighted"]),
                ("Dawn or dusk", ["dawn_dusk"]),
                (
                    "Other, incl. dark with lighting unknown",
                    ["dark_unknown_lighting", "other_unknown"],
                ),
            ],
        ),
        (
            "Location",
            "location",
            [
                ("On the road, away from an intersection", ["midblock_roadway"]),
                ("At an intersection", ["at_intersection"]),
                ("Shoulder, median or parking lane", ["roadside_shoulder_median_parking"]),
                ("Sidewalk, off road or unknown", ["sidewalk_or_off_road", "unknown"]),
            ],
        ),
        (
            "Road",
            "road_class",
            [
                ("Principal arterial", ["principal_arterial"]),
                ("Minor arterial", ["minor_arterial"]),
                ("Interstate or freeway", ["interstate_freeway"]),
                ("Collector", ["collector"]),
                ("Local or unknown", ["local", "unknown"]),
            ],
        ),
    ]
    groups = []
    for title, dim, items in spec:
        cols = [*palette[: len(items) - 1], "deemph"]
        groups.append(
            (title, [part(n, c, dim, *lv) for (n, lv), c in zip(items, cols, strict=True)])
        )
    return segbar(groups, fmt="pct:0", name_header="Measure")


SIGN_LEVELS = [
    ("<=25", "25"),
    ("30-35", f"30{EN}35"),
    ("40-45", f"40{EN}45"),
    ("50-55", f"50{EN}55"),
    ("60-65", f"60{EN}65"),
    ("70+", "70+"),
]


def sign_html(number: str) -> str:
    return (
        f'<span class="sign"><span class="sign-t">SPEED<br>LIMIT</span>'
        f'<span class="sign-n">{esc(number)}</span></span>'
    )


@chart("ped_speed")
def _ped_speed() -> str:
    t = "vulnerable/pedestrian_killed_contrasts"
    bars = []
    for lvl, label in SIGN_LEVELS:
        r = pick(t, victim="pedestrian", outcome="killed", factor="str_speed_limit", level=lvl)
        bars.append(
            Bar(
                f"{label} mph",
                float(r["crude_rate"]),
                label_html=sign_html(label),
                extra={
                    "Pedestrians struck (sample)": f"{int(r['n']):,}",
                    "Pedestrians killed (sample)": f"{int(r['n_events']):,}",
                },
            )
        )
    return columns(
        bars,
        fmt="pct:0",
        vmax=0.5,
        value_header="Share who died",
        label_header="Speed limit",
    )


@chart("helmet_states")
def _helmet_states() -> str:
    h = table("deaths/helmet")
    states = table("deaths/states").set_index("state")["state_name"]
    h = h[h["dimension"] == "state"]
    bars = []
    for _, r in h.iterrows():
        code = str(r["level"])
        name = str(states.get(code, code))
        bars.append(
            Bar(
                code,
                float(r["unhelmeted_share"]),
                tip_note=f"({int(r['known']):,} riders)",
                extra={"State": name, "Riders with known helmet use": f"{int(r['known']):,}"},
            )
        )
    us = float(pick("deaths/helmet", dimension="overall", level="all")["unhelmeted_share"])
    return strip(
        bars,
        fmt="pct:0",
        ref=(us, "US"),
        label_header="State code",
        value_header="Share without a helmet",
        vmax=0.8,
    )


@chart("veh_age_rr")
def _veh_age_rr() -> str:
    t = "person/lpv_killed_crude_vs_adjusted"
    spec = [
        ("0-3", f"0{EN}3 years"),
        ("4-7", f"4{EN}7"),
        ("8-12", f"8{EN}12"),
        ("13-17", f"13{EN}17"),
        ("18+", "18 or more"),
    ]
    bars = []
    for lvl, label in spec:
        r = pick(t, population="lpv", outcome="killed", factor="veh_age_band", level=lvl)
        ref_row = lvl == "0-3"
        bars.append(
            Bar(
                label,
                float(r["A_adj_rr"]),
                None if ref_row else float(r["A_adj_rr_low"]),
                None if ref_row else float(r["A_adj_rr_high"]),
                color="deemph" if ref_row else "accent",
            )
        )
    return columns(
        bars,
        fmt="x:1",
        tick_fmt="x:0",
        vmax=math.ceil(max(b.high for b in bars if b.high is not None)),
        ref=(1, "Same risk as vehicles 0–3 years old"),
        value_header="Adjusted risk ratio",
        label_header="Vehicle age",
    )


def _years(df: pd.DataFrame, col: str = "YEAR") -> list[int]:
    return sorted(
        {int(render._norm(v)) for v in df[col] if re.fullmatch(r"\d{4}", render._norm(v))}
    )


@chart("veh_age_share")
def _veh_age_share() -> str:
    df = table("deaths/vehicle_age")
    years = _years(df)
    vals = [float(pick("deaths/vehicle_age", YEAR=y, band="18+")["share"]) for y in years]
    ln = Line("Vehicles 18 or more years old", vals, end_label=False, label_idx=[0, len(vals) - 1])
    return lines_chart(
        [ln],
        [str(y) for y in years],
        fmt="pct:0",
        end_fmt="pct:0",
        ydomain=(0, 0.35),
        x_header="Year",
    )


@chart("trend_index")
def _trend_index() -> str:
    t = "deaths/annual"
    years = _years(table(t))
    spec = [
        ("motorcyclists", "Motorcyclists", "series-2"),
        ("pedestrians", "Pedestrians", "aqua"),
        ("pv_occupants", "In cars, SUVs, pickups and vans", "accent"),
        ("all", "All deaths", "ink-2"),
    ]
    series = []
    for seg, name, color in spec:
        raw = {y: float(pick(t, YEAR=y, segment=seg)["deaths"]) for y in years}
        series.append(Line(name, [100 * raw[y] / raw[2019] for y in years], color))
    return lines_chart(
        series,
        [str(y) for y in years],
        fmt=".0f",
        base=100,
        x_header="Year (2019 = 100)",
    )


@chart("change_bars")
def _change_bars() -> str:
    t = "deaths/segments"
    spec = [
        ("all", "All deaths"),
        ("invalid_licence_crash", "Crash with a driver without a valid licence"),
        ("hit_and_run", "Hit-and-run crash"),
        ("alcohol_impaired", "Drunk driving"),
        ("speeding", "Speeding"),
        ("unbelted", "Unbelted occupants"),
        ("unhelmeted", "Unhelmeted motorcyclists"),
        ("urban", "Urban roads"),
        ("rural", "Rural roads"),
        ("pv_occupants", "In cars, SUVs, pickups and vans"),
        ("motorcyclists", "Motorcyclists"),
        ("pedestrians", "Pedestrians"),
        ("cyclists", "Cyclists"),
    ]
    inds = []
    for seg, label in spec:
        r = pick(t, segment=seg)
        inds.append(
            Indicator(label, [float(r["pct_change_2019_2021"]), float(r["pct_change_2019_2024"])])
        )
    return pairbars(
        inds,
        [("2019 to 2021", "series-2"), ("2019 to 2024", "accent")],
        fmt="pctsign:0",
        label_header="Group",
        diverging=True,
    )


@chart("licence_trend")
def _licence_trend() -> str:
    t = "deaths/driver_records_by_year"
    df = table(t)
    years = _years(df)
    vals = [
        float(pick(t, YEAR=y, group="all", indicator="licence_invalid")["share"]) for y in years
    ]
    idx = [years.index(y) for y in (2019, 2020, 2024)]
    ln = Line("Drivers without a valid licence", vals, end_label=False, label_idx=idx)
    return lines_chart(
        [ln],
        [str(y) for y in years],
        fmt="pct:0",
        end_fmt="pct:1",
        ydomain=(0.10, 0.18),
        x_header="Year",
    )


# ---------------------------------------------------------------------------------------------
# States table
# ---------------------------------------------------------------------------------------------

# (header, column, kind, known-count column or None)
STATE_COLS = [
    ("Deaths 2024", "deaths_2024", "count", None),
    (f"Change 2019{chr(0x2192)}24", "pct_change_2019_2024", "change", None),
    ("Drunk driving", "alcohol_impaired_share", "share", None),
    ("Speeding", "speeding_share", "share", None),
    ("Unbelted", "unbelted_share_known", "share", "pv_known"),
    ("No helmet", "unhelmeted_share_known", "share", "mc_known"),
    ("Pedestrians", "pedestrian_share", "share", None),
    ("Rural", "rural_share", "share", None),
]
SMALL_BASE = 50


def states_table() -> str:
    df = table("deaths/states").copy()
    us = df[df["state"] == "US"]
    rest = df[df["state"] != "US"].sort_values("deaths_2024", ascending=False)
    ordered = pd.concat([us, rest])
    colmax = {col: float(rest[col].max()) for _, col, kind, _ in STATE_COLS if kind == "share"}
    head = [
        '<th scope="col" aria-sort="none" data-type="text"><button type="button">State</button></th>'
    ]
    for header, col, kind, _ in STATE_COLS:
        aria = "descending" if col == "deaths_2024" else "none"
        head.append(
            f'<th scope="col" class="{"num sh" if kind == "share" else "num"}" '
            f'aria-sort="{aria}" data-type="number">'
            f'<button type="button">{esc(header)}</button></th>'
        )
    body = []
    for _, r in ordered.iterrows():
        is_us = r["state"] == "US"
        cells = [
            f'<th scope="row" data-sort="{esc(str(r["state_name"]).lower())}">'
            f'<span class="st-name">{esc(r["state_name"])}</span>'
            + ("" if is_us else f' <span class="st-code">{esc(r["state"])}</span>')
            + "</th>"
        ]
        for _, col, kind, known_col in STATE_COLS:
            v = r[col]
            if pd.isna(v):
                cells.append('<td class="num" data-sort="">–</td>')
                continue
            v = float(v)
            if kind == "count":
                cells.append(f'<td class="num" data-sort="{v:g}">{v:,.0f}</td>')
            elif kind == "change":
                cells.append(f'<td class="num" data-sort="{v:.6f}">{esc(fv(v, "pctsign:0"))}</td>')
            else:
                small = known_col is not None and float(r[known_col]) < SMALL_BASE
                width = 100 * v / colmax[col] if colmax[col] else 0
                title = (
                    f' title="Small base: only {int(r[known_col])} people with a known record"'
                    if small
                    else ""
                )
                cls = "num sh small" if small else "num sh"
                cells.append(
                    f'<td class="{cls}" data-sort="{v:.6f}"{title}>'
                    f'<span class="st-val">{esc(fv(v, "pct:0"))}</span>'
                    f'<span class="st-bar"><i style="width:{min(width, 100):.1f}%"></i></span></td>'
                )
        cls = ' class="us-row" data-pinned="true"' if is_us else ""
        body.append(
            f'<tr{cls} data-name="{esc((str(r["state_name"]) + " " + str(r["state"])).lower())}">{"".join(cells)}</tr>'
        )
    body.append(
        f'<tr class="st-empty" hidden><td colspan="{len(STATE_COLS) + 1}">No state matches.</td></tr>'
    )
    return (
        '<div class="table-wrap states-wrap"><table class="states" id="states-table">'
        '<caption class="sr-only">Deaths and the mix of deaths by state, 2016–2024</caption>'
        f"<thead><tr>{''.join(head)}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


# ---------------------------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------------------------


def _asset(name: str) -> str:
    f = ASSETS / f"site.{name}"
    if not f.exists():
        raise SiteError(f"asset not found: {f}")
    text = f.read_text()
    if "{{" in text:
        raise SiteError(f"{f.name} must not contain '{{{{' (it would look like a placeholder)")
    return text.strip("\n")


def render_template(text: str) -> str:
    errors: list[str] = []

    def sub(m: re.Match) -> str:
        spec = m.group(1).strip()
        try:
            if spec.startswith("chart:"):
                name = spec[len("chart:") :]
                if name not in CHARTS:
                    raise SiteError(f"unknown chart {name!r}")
                return CHARTS[name]()
            if spec == "statestable":
                return states_table()
            if spec in ("asset:css", "asset:js"):
                return _asset(spec[len("asset:") :])
            return esc(render.resolve(spec))
        except (render.RenderError, SiteError, KeyError, IndexError, ValueError) as exc:
            errors.append(f"{m.group(0)} -> {exc}")
            return m.group(0)

    out = render.PLACEHOLDER.sub(sub, text)
    if errors:
        raise SiteError("unresolved placeholders:\n" + "\n".join(errors))
    return out


# "None of the four" is a real chart label; every other None/NaN/inf is a leaked value
BAD_TOKEN = re.compile(r"\b(?:nan|NaN|inf|-inf|None(?! of the four))\b")


def validate(page: str) -> None:
    """The rendered page has no unresolved placeholder and no NaN-like text."""
    stripped = re.sub(r"<(style|script)\b.*?</\1>", "", page, flags=re.S)
    for token in ("{{", "}}"):
        if token in stripped:
            i = stripped.find(token)
            raise SiteError(f"unresolved placeholder near: {stripped[max(0, i - 40) : i + 60]!r}")
    m = BAD_TOKEN.search(stripped)
    if m:
        raise SiteError(
            f"found {m.group(0)!r} near: {stripped[max(0, m.start() - 60) : m.end() + 60]!r}"
        )


def build() -> str:
    render._table.cache_clear()
    page = render_template(TEMPLATE.read_text())
    validate(page)
    return page


def run() -> dict:
    page = build()
    OUTPUT.write_text(page)
    return {"written": [str(OUTPUT)], "bytes": len(page.encode())}
