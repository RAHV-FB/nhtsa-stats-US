"""The public site is a pure function of its template and the committed tables."""

from __future__ import annotations

import json
import re

import pytest

from nhtsa_stats.reporting import site
from nhtsa_stats.reporting.site import Bar, Indicator, Line, Part

# ---------------------------------------------------------------------------------------------
# 1. the committed page equals a fresh render
# ---------------------------------------------------------------------------------------------


def test_index_matches_fresh_render():
    assert site.build() == site.OUTPUT.read_text(), (
        "website/index.html is stale: run `nhtsa analyze site`"
    )


def test_every_chart_in_the_template_is_registered():
    used = set(re.findall(r"\{\{chart:(\w+)\}\}", site.TEMPLATE.read_text()))
    assert used <= set(site.CHARTS), used - set(site.CHARTS)


def test_page_is_self_contained_and_clean():
    page = site.OUTPUT.read_text()
    assert "{{" not in re.sub(r"<(style|script)\b.*?</\1>", "", page, flags=re.S)
    assert page.count("<h1") == 1
    assert page.count("<figure") == page.count("<figcaption") == page.count('class="dataview"')


# ---------------------------------------------------------------------------------------------
# 2. no hand-typed numbers in the template prose
# ---------------------------------------------------------------------------------------------

EN = "–"
# Definitional literals allowed in the template's own text. A token mapped to a pattern is
# allowed only where the surrounding text matches it; None allows it anywhere.
YEARS = {str(y): None for y in range(2016, 2025)}
ALLOWED: dict[str, str | None] = {
    **YEARS,
    "2016" + EN + "2024": None,
    "2020" + EN + "21": r"The 2020" + EN + r"21 surge",
    ".08": None,  # blood alcohol threshold
    ".15": None,
    "30": r"within 30 days",  # FARS 30-day definition
    "10,000": r"10,000 lb",  # large-truck definition
    "95": r"95% confidence interval",
    "100": r"2019 = 100",  # the index base
    "1": r"ratio of 1 means",
    # speed-limit, vehicle-age and age-band labels (the chart vocabulary)
    "25": r"\b25 mph",
    "30" + EN + "35": None,
    "40" + EN + "45": None,
    "50" + EN + "55": None,
    "60" + EN + "65": None,
    "70": None,
    "75": None,
    "13": None,
    "18": r"\b18 or more years",
    "4": r"under 4 years",
    "0" + EN + "3": r"0" + EN + r"3 years",
    "25" + EN + "34": None,
    "16" + EN + "24": None,
    "55" + EN + "74": None,
    "35" + EN + "54": None,
}
NUMBER = re.compile(r"(?<![\w.])(?:\.\d+|\d[\d,]*(?:\.\d+)?(?:" + EN + r"\d[\d,]*)?)")


def template_prose() -> str:
    t = site.TEMPLATE.read_text()
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<(style|script)\b.*?</\1>", "", t, flags=re.S)
    t = re.sub(r"\{\{.*?\}\}", " ", t, flags=re.S)  # placeholders and directives
    t = re.sub(r"<[^>]*>", " ", t)  # tags, with their attribute values
    return t


def test_no_hand_typed_numbers():
    prose = template_prose()
    bad = []
    for m in NUMBER.finditer(prose):
        token = m.group(0).rstrip(",")
        if token not in ALLOWED:
            bad.append((token, prose[max(0, m.start() - 40) : m.end() + 40]))
            continue
        needed = ALLOWED[token]
        window = prose[max(0, m.start() - 40) : m.end() + 40]
        if needed and not re.search(needed, " ".join(window.split())):
            bad.append((token, window))
    assert not bad, "numbers typed in the template (use a placeholder):\n" + "\n".join(
        f"  {t!r} in ...{c!r}..." for t, c in bad
    )


def test_number_check_catches_a_typed_number(monkeypatch, tmp_path):
    f = tmp_path / "t.html"
    f.write_text("<p>About 41,700 people died.</p>")
    monkeypatch.setattr(site, "TEMPLATE", f)
    assert [m.group(0) for m in NUMBER.finditer(template_prose())] == ["41,700"]


# ---------------------------------------------------------------------------------------------
# 3. chart builders on tiny synthetic data
# ---------------------------------------------------------------------------------------------


def test_nice_scales():
    assert site.nice_ceil(0.596) == 0.6
    assert site.nice_ceil(7027) == 8000
    assert site.nice_ticks(0, 0.6) == [0, 0.2, 0.4, 0.6]
    assert site.nice_ticks(0, 7) == [0, 2, 4, 6]
    assert site.nice_ticks(-0.02, 0.5)[0] == 0


def test_hbars_widths_table_and_escaping():
    out = site.hbars(
        [Bar("A <b>&", 0.5), Bar("B", 0.25, low=0.2, high=0.3)],
        fmt="pct:0",
        vmax=1.0,
        ref=(0.4, "All"),
    )
    assert "width:50%" in out and "width:25%" in out
    assert "A &lt;b&gt;&amp;" in out and "<b>" not in out
    assert "left:20%;width:10%" in out  # CI whisker 0.2 to 0.3
    assert 'data-tip="B: 25% (95% CI 20%–30%)"' in out
    assert "hb-ref" in out and "All 40%" in out
    table = out[out.index("<table>") :]
    assert "50%" in table and "25%" in table and "95% interval low" in table
    assert "18px" in out  # bars stay thin


def test_hbars_groups_share_one_scale():
    out = site.hbars(
        None, groups=[("G1", [Bar("a", 0.5)]), ("G2", [Bar("b", 0.25)])], fmt="pct:0", vmax=0.5
    )
    assert "width:100%" in out and "width:50%" in out
    assert out.count("hb-group-title") == 2 and '<th scope="col">Group</th>' in out


def test_pairbars_diverging_handles_a_negative_bar():
    inds = [Indicator("up", [0.4, 0.2]), Indicator("down", [0.1, -0.02])]
    out = site.pairbars(
        inds, [("one", "series-2"), ("two", "accent")], fmt="pctsign:0", diverging=True
    )
    assert 'class="hb-bar neg"' in out and "hb-zero" in out and "is-div" in out
    assert "−2%" in out
    assert out.count('class="legend"') == 1  # legend whenever there are two series


def test_segbar_prints_a_share_only_when_it_fits():
    assert site.seg_fits("61%", 0.5)
    assert not site.seg_fits("6%", 0.06)
    out = site.segbar([(None, [Part("big", 0.9, "accent"), Part("tiny", 0.02, "series-2")])])
    assert out.count('class="seg-txt') == 1
    assert '<th scope="col">Share</th>' in out
    assert "tiny" in out.split("<table>")[1]


def test_segbar_sums_members_and_lists_them_in_the_table():
    part = Part("Other", 0.3, "deemph", [("a", 0.1), ("b", 0.2)])
    out = site.segbar([("Light", [Part("x", 0.7, "accent"), part])])
    table = out.split("<table>")[1]
    assert "Detail" in table and ">a<" in table and ">b<" in table


def test_columns_reference_whisker_and_labels():
    out = site.columns(
        [Bar("ref", 1.0, color="deemph"), Bar("hi <x>", 2.0, 1.5, 2.5)],
        fmt="x:1",
        vmax=3,
        ref=(1, "Same risk"),
    )
    assert "height:66.667%" in out and "col-ci" in out and "vref" in out
    assert "hi &lt;x&gt;" in out and "2.0×" in out
    assert "Same risk" in out


def test_strip_labels_only_the_extremes_and_the_reference():
    bars = [Bar(f"S{i}", i / 100) for i in range(1, 52)]
    out = site.strip(bars, fmt="pct:0", ref=(0.3, "US"), vmax=0.6)
    assert out.count("vlabel vlabel") == 2
    assert out.count("col-cell") == 51
    assert "S51 51%" in out and "S1 1%" in out and "US 30%" in out
    # sorted high to low: the first bar is the 51% one
    assert out.index("S51: 51%") < out.index("S1: 1%")


def test_lines_two_svgs_dots_and_embedded_data():
    s = [Line("A <1>", [100.0, 110.0, 120.0], "accent"), Line("B", [100.0, 95.0, 90.0], "series-2")]
    out = site.lines_chart(s, ["2019", "2020", "2021"], fmt=".0f", base=100)
    assert out.count("<svg") == 2 and "ln-wide" in out and "ln-narrow" in out
    assert out.count("<circle") == 4  # one end dot per series per svg
    assert "A &lt;1&gt;" in out
    attr = re.search(r'data-series="([^"]*)"', out).group(1)
    data = json.loads(
        attr.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    )
    assert data["xs"] == ["2019", "2020", "2021"] and data["series"][0]["text"][-1] == "120"
    assert out.count('class="legend"') == 1
    assert '<th scope="col">B</th>' in out


def test_lines_single_series_has_no_legend_and_labels_chosen_points():
    ln = Line("Only", [0.12, 0.17, 0.14], end_label=False, label_idx=[0, 1])
    out = site.lines_chart([ln], ["2019", "2020", "2021"], fmt="pct:0", end_fmt="pct:1")
    assert "legend" not in out.split("<table>")[0]
    assert "12.0%" in out and "17.0%" in out


def test_lines_reject_more_than_four_series():
    many = [Line(str(i), [1.0, 2.0]) for i in range(5)]
    with pytest.raises(site.SiteError):
        site.lines_chart(many, ["a", "b"], fmt=".0f")


def test_validate_rejects_leaked_values():
    site.validate("<p>None of the four</p>")
    for bad in ("<p>nan</p>", "<p>NaN%</p>", "<p>None</p>", "<p>{{x}}</p>"):
        with pytest.raises(site.SiteError):
            site.validate(bad)


def test_states_table_pins_us_and_sorts_by_2024_deaths():
    out = site.states_table()
    assert out.index("United States") < out.index("Texas") < out.index("California")
    assert 'data-pinned="true"' in out and 'aria-sort="descending"' in out
    assert out.count("<tr") == 1 + 1 + 51 + 1  # head, US, states, empty-state row
