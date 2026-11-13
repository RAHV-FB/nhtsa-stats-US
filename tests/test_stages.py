"""EMS timing and BAC-implicate handling in the post-crash stage (software tests)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
import pytest

from nhtsa_stats.analysis import stages


def _interval(t_from: list[int | None], t_to: list[int | None]) -> list[int | None]:
    df = pl.DataFrame({"a": t_from, "b": t_to}, schema={"a": pl.Int64, "b": pl.Int64})
    return df.select(stages._interval(pl.col("a"), pl.col("b")).alias("m"))["m"].to_list()


def test_interval_wraps_midnight_but_not_clock_errors():
    # 10:00 -> 10:12 ordinary; 23:55 -> 00:05 is a genuine midnight crossing (10 min);
    # arrival recorded 5 minutes before the crash would be 1,435 min after the modulo: missing;
    # 7 h and 13 h intervals: 7 h kept, 13 h implausible -> missing; unknown time -> missing.
    got = _interval(
        [600, 23 * 60 + 55, 600, 0, 0, None],
        [612, 5, 595, 7 * 60, 13 * 60, 30],
    )
    assert got == [12, 10, None, 420, None, None]


def _timing_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "restraint": ["none"] * 4,
            "ptype": ["driver"] * 4,
            "speeding": [0.0] * 4,
            "rural": [0.0] * 4,
            "DOA": [7, 7, 8, 0],
            "lag_min": [0.0, 0.0, 30.0, 120.0],
            # deaths 0, 1: BAC >= .08 in 0.5 / 1.0 of implicates; death 2: 0; death 3: unknown
            "p_alcohol": [0.5, 1.0, 0.0, np.nan],
        }
    )


def test_unknown_bac_implicates_are_not_counted_as_no_bac():
    tab = stages.timing_table(_timing_frame()).set_index("group")
    yes = tab.loc["driver BAC >= .08 in crash (MI)"]
    no = tab.loc["no driver BAC >= .08 (MI)"]
    unk = tab.loc["driver BAC unknown (no driver BAC implicate)"]
    assert yes["deaths"] == pytest.approx(1.5)
    assert no["deaths"] == pytest.approx(0.5 + 0.0 + 1.0)  # the unknown death has weight 0
    assert unk["deaths"] == pytest.approx(1.0)
    # known weights + unknown weight account for every death exactly once
    assert yes["deaths"] + no["deaths"] + unk["deaths"] == pytest.approx(4.0)
    assert unk["share_died_at_scene"] == pytest.approx(0.0)  # death 3 has DOA == 0
    assert yes["share_died_at_scene"] == pytest.approx(1.0)
