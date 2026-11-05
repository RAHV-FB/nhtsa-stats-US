"""The public site is a pure function of its template and the committed tables."""

from __future__ import annotations

import importlib.util
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
# The only numeric literals the template's own prose may contain, each bound to the phrase it may
# appear in (a regex that must match text overlapping the token). Every other number has to be a
# placeholder, so it comes from a table. test_allowlist_has_no_unused_entries keeps this list tight.
ALLOWED: dict[str, list[str]] = {
    "2016": [r"2016 to (?:in )?2024", r"in 2016 and in 2024"],
    "2018": [r"start in 2018"],  # first year of the prior-suspension fields
    "2019": [
        r"(?:from|Since|against|in|than in|above|their|own) 2019",
        r"2019 (?:to|=|level|count)",
    ],
    "2020": [r"in 2020"],
    "2021": [r"(?:to|after|in) 2021"],
    "2024": [r"(?:to|in|By) (?:in )?2024", r"2024 than in 2019"],
    "2016" + EN + "2024": [r"(?:, |for |crashes |state |truck )2016" + EN + "2024"],
    "2020" + EN + "21": [r"The 2020" + EN + r"21 surge"],
    ".08": [r"\.08 or more"],  # legal blood alcohol limit
    ".15": [r"\.15 or more"],  # the "nearly twice the limit" threshold
    "30": [r"within 30 days"],  # FARS death definition
    "10,000": [r"10,000 lb"],  # large-truck definition
    "95": [r"95% confidence interval"],
    "100": [r"2019 = 100"],  # the index base
    "1": [r"ratio of 1 means"],
    "13": [r"aged 13 and over"],  # age range of the belt-effectiveness estimate
    "25": [r"25 mph"],
    "40" + EN + "45": [r"40" + EN + r"45 mph"],
    "50" + EN + "55": [r"50" + EN + r"55 mph"],
    "25" + EN + "34": [r"aged 25" + EN + "34"],
    "0" + EN + "3": [r"0" + EN + r"3 years old"],
    "18": [r"18 or more years old"],
    "4": [r"under 4 years old"],
}
NUMBER = re.compile(r"(?<![\w.])(?:\.\d+|\d[\d,]*(?:\.\d+)?(?:" + EN + r"\d[\d,]*)?)")


def template_prose() -> str:
    t = site.TEMPLATE.read_text()
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<(style|script)\b.*?</\1>", "", t, flags=re.S)
    t = re.sub(r"\{\{.*?\}\}", " ", t, flags=re.S)  # placeholders and directives
    t = re.sub(r"<[^>]*>", " ", t)  # tags, with their attribute values
    return t


def _bad_numbers(prose: str) -> list[tuple[str, str]]:
    """Numbers outside the allowlist, or inside it but away from their phrase."""
    bad = []
    for m in NUMBER.finditer(prose):
        token = m.group(0).rstrip(",")
        end = m.start() + len(token)
        ok = False
        for pat in ALLOWED.get(token, []):
            flex = pat.replace(" ", r"\s+")  # prose wraps across lines
            for mm in re.finditer(flex, prose):
                if mm.start() < end and mm.end() > m.start():
                    ok = True
        if not ok:
            window = prose[max(0, m.start() - 40) : m.end() + 40]
            bad.append((token, " ".join(window.split())))
    return bad


def test_no_hand_typed_numbers():
    bad = _bad_numbers(template_prose())
    assert not bad, "numbers typed in the template (use a placeholder):\n" + "\n".join(
        f"  {t!r} not allowed in context: ...{c}..." for t, c in bad
    )


def test_allowlist_has_no_unused_entries():
    prose = template_prose()
    present = {m.group(0).rstrip(",") for m in NUMBER.finditer(prose)}
    assert set(ALLOWED) <= present, (
        f"allowlisted but absent from the template: {set(ALLOWED) - present}"
    )
    # every phrase must occur in the template too
    flat = " ".join(prose.split())
    for token, pats in ALLOWED.items():
        for pat in pats:
            assert re.search(pat, flat), f"phrase {pat!r} for {token!r} not in the template"


def test_allowlisted_number_outside_its_phrase_is_rejected():
    assert _bad_numbers("aged 13 and over") == []
    assert _bad_numbers("about 13 people") != []
    assert _bad_numbers("at .08 or more") == []
    assert _bad_numbers("at .09 or more") != []


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


# ---------------------------------------------------------------------------------------------
# 4. fixed scales refuse values outside them
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        lambda: site.hbars([Bar("a", 0.8)], fmt="pct:0", vmax=0.7),
        lambda: site.hbars([Bar("a", 0.5, 0.4, 0.75)], fmt="pct:0", vmax=0.7),  # CI end
        lambda: site.hbars([Bar("a", 0.5)], fmt="pct:0", vmax=0.7, ref=(0.9, "All")),
        lambda: site.pairbars(
            [Indicator("a", [0.2, 0.31])], [("x", "accent"), ("y", "aqua")], fmt="pct:0", vmax=0.3
        ),
        lambda: site.columns([Bar("a", 0.6)], fmt="pct:0", vmax=0.5),
        lambda: site.columns([Bar("a", 0.4, 0.3, 0.55)], fmt="pct:0", vmax=0.5),
        lambda: site.strip([Bar("a", 0.9)], fmt="pct:0", ref=(0.3, "US"), vmax=0.8),
        lambda: site.lines_chart(
            [Line("a", [0.09, 0.12])], ["2019", "2020"], fmt="pct:0", ydomain=(0.10, 0.18)
        ),
        lambda: site.lines_chart(
            [Line("a", [0.12, 0.2])], ["2019", "2020"], fmt="pct:0", ydomain=(0.10, 0.18)
        ),
    ],
)
def test_fixed_scale_rejects_out_of_domain_values(build):
    with pytest.raises(site.SiteError, match="outside the fixed scale"):
        build()


def test_fixed_scale_accepts_values_on_the_boundary():
    site.hbars([Bar("a", 0.7, 0.6, 0.7)], fmt="pct:0", vmax=0.7)
    site.lines_chart([Line("a", [0.10, 0.18])], ["2019", "2020"], fmt="pct:0", ydomain=(0.10, 0.18))


# ---------------------------------------------------------------------------------------------
# 5. the CSV links on the page are exactly what the sync tool publishes
# ---------------------------------------------------------------------------------------------


def _sync_tool():
    path = site.OUTPUT.parent / "tools" / "sync_public_data.py"
    spec = importlib.util.spec_from_file_location("sync_public_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_csv_links_match_the_sync_tool_and_the_files_exist():
    linked = set(re.findall(r'data/(tables/[^"\'\s>]+\.csv)', site.TEMPLATE.read_text()))
    synced = set(_sync_tool().sources().values())
    assert linked == synced, (
        f"linked but not synced: {sorted(linked - synced)}; "
        f"synced but never linked: {sorted(synced - linked)}"
    )
    data = site.OUTPUT.parent / "data"
    missing = [t for t in synced if not (data / t).is_file()]
    assert not missing, f"not under website/data/: {missing} (run sync_public_data.py)"
