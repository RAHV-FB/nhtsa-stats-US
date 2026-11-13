"""Recode defects found in the year-by-year label audit (synthetic frames)."""

from __future__ import annotations

import polars as pl

from nhtsa_stats.processing import drivers as dv
from nhtsa_stats.processing import harmonize as h
from nhtsa_stats.processing.features import any_flag


def _apply(expr: pl.Expr, **cols) -> list:
    return pl.DataFrame(cols).select(expr.alias("out"))["out"].to_list()


def test_fatal_is_zero_when_no_crash_death_is_possible():
    # MAXSEV_IM / INJ_SEV: 5 injured severity unknown, 6 died prior to crash, 8 no person
    # involved cannot hold a crash death (K would be 4); only 9 (unknown) stays null.
    assert _apply(h.fatal("S"), S=[4, 3, 0, 5, 6, 8, 9]) == [1, 0, 0, 0, 0, 0, None]


def test_killed_or_serious_keeps_injured_severity_unknown_null():
    # 5 may hide an A injury -> null; 6 / 8 cannot be K or A -> 0.
    assert _apply(h.killed_or_serious("S"), S=[4, 3, 2, 5, 6, 8, 9]) == [1, 1, 0, None, 0, 0, None]


def test_person_killed_is_missing_for_died_prior_to_crash():
    # INJ_SEV 6 is neither a crash death nor a survivor: missing, not 0.
    assert _apply(h.person_fatal("S"), S=[4, 3, 0, 5, 6, 9]) == [1, 0, 0, 0, None, None]
    assert _apply(h.person_killed_or_serious("S"), S=[4, 3, 2, 5, 6, 9]) == [
        1,
        1,
        0,
        None,
        None,
        None,
    ]


def test_distraction_looked_but_did_not_see_is_not_distracted():
    out = _apply(h.distraction_flag("c"), c=[0, 1, 5, 93, 16, 96, 99, None])
    assert out == [0, 0, 1, 1, None, None, None, None]


def test_looked_but_did_not_see_alone_is_not_distracted_but_other_code_wins():
    df = pl.DataFrame({"k": [1, 1, 2], "c": [1, 5, 1]}).with_columns(
        h.distraction_flag("c").alias("distracted")
    )
    out = df.group_by("k").agg(any_flag("distracted")).sort("k")["distracted"].to_list()
    assert out == [1, 0]


def test_rollover_not_applicable_is_zero_only_for_motorcycle_bodies():
    out = _apply(
        h.rollover_flag("ROLLOVER", "BODY_TYP"),
        ROLLOVER=[8, 8, 8, 0, 1, 2, 3, 9, None],
        BODY_TYP=[80, 84, 4, 4, 4, 4, 4, 4, 4],
    )
    # code 8 on a car (never observed) is unknown, not "no rollover"
    assert out == [0, 0, None, 0, 1, 1, 1, 1, None]


def test_prior_suspension_count_is_null_before_2018():
    # 2016-17 PREV_SUS counts suspensions of any type: a different quantity, so null.
    out = _apply(
        h.fars_prior_suspensions(),
        YEAR=[2016, 2017, 2018, 2018, 2018],
        PREV_SUS1=[3, 0, 0, 2, 99],
    )
    assert out == [None, None, 0, 2, 99]


def test_crss_driver_does_not_carry_crash_level_hit_and_run_duplicate():
    assert "hit_and_run" not in dv.CRSS_CRASH_COLS


# ---- person-level killed must stay unknown (never a raw recode) ----------------------------
def _alias_sources(path: str, names: set[str]) -> dict[str, list[str]]:
    """For every ``<expr>.alias(name)`` in the file, the source of ``<expr>``."""
    import ast
    from pathlib import Path

    src = Path(path).read_text()
    out: dict[str, list[str]] = {}
    for node in ast.walk(ast.parse(src)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "alias"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in names
        ):
            out.setdefault(node.args[0].value, []).append(ast.unparse(node.func.value))
    return out


def test_features_and_vulnerable_define_killed_with_person_fatal():
    import nhtsa_stats.analysis.vulnerable as vu
    import nhtsa_stats.processing.features as ft

    wanted = {"killed", "killed_cc", "killed_or_serious", "killed_or_serious_cc"}
    for mod in (ft, vu):
        found = _alias_sources(mod.__file__, wanted)
        assert {"killed", "killed_or_serious"} <= set(found), mod.__name__
        for name, exprs in found.items():
            for e in exprs:
                fn = "person_killed_or_serious" if name.startswith("killed_or") else "person_fatal"
                # either the shared recode, or a copy of the column made from it
                assert f"h.{fn}(" in e or e.startswith("pl.col('killed"), (mod.__name__, name, e)


def test_vulnerable_killed_is_unknown_for_died_prior_and_unknown_severity(monkeypatch):
    import nhtsa_stats.analysis.vulnerable as vu

    person = pl.DataFrame(
        {
            "YEAR": [2022] * 6,
            "ST_CASE": [1, 2, 3, 4, 5, 6],
            "VEH_NO": [1] * 6,
            "PER_NO": [1] * 6,
            "PER_TYP": [5] * 6,
            "STR_VEH": [1] * 6,
            "AGE": [30] * 6,
            "SEX": [1] * 6,
            "INJ_SEV": [4, 3, 0, 5, 6, 9],
            "LOCATION": [1] * 6,
        }
    )
    vehicle = pl.DataFrame(
        {
            "YEAR": [2022] * 6,
            "ST_CASE": [1, 2, 3, 4, 5, 6],
            "VEH_NO": [1] * 6,
            "BODY_TYP": [4] * 6,
            "VSPD_LIM": [35] * 6,
            "SPEEDREL": [0] * 6,
        }
    )
    monkeypatch.setattr(vu, "load_table", lambda s, t, y, c: person if t == "person" else vehicle)
    out = vu.build("FARS", (2022,)).sort("case_id")
    assert out["killed"].to_list() == [1, 0, 0, 0, None, None]
    assert out["killed_cc"].to_list() == [1, 0, 0, 0, None, None]
