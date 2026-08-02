"""Tests for the third-axis diversification test.

The load-bearing claims are: the tail statistics correctly separate a
protective sleeve from a levered-market one, the rolling-excess windows
include the window starting at inception, and the verdict is calibrated
against the gold/duration control rather than an invented constant.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import factor_axis_test as F


IDX = pd.date_range("1993-03-31", periods=240, freq="ME")


def _mkt(seed=0):
    return pd.Series(np.random.default_rng(seed).normal(0.008, 0.04, 240),
                     index=IDX)


class TestTailStats:
    def test_a_levered_market_sleeve_amplifies_the_tail(self):
        m = _mkt()
        lev = m * 1.3
        t = F.tail_stats(lev, m, 0.10)
        assert t["corr"] > 0.99
        assert t["mean"] < F.tail_stats(m, m, 0.10)["mean"]

    def test_an_inverse_sleeve_offsets_the_tail(self):
        m = _mkt()
        hedge = -m
        t = F.tail_stats(hedge, m, 0.10)
        assert t["mean"] > 0
        assert t["up_rate"] > 90

    def test_an_independent_sleeve_has_near_zero_tail_correlation(self):
        m = _mkt(1)
        indep = pd.Series(np.random.default_rng(99).normal(0.005, 0.04, 240),
                          index=IDX)
        assert abs(F.tail_stats(indep, m, 0.10)["corr"]) < 0.5

    def test_the_quantile_selects_the_right_number_of_months(self):
        m = _mkt()
        assert F.tail_stats(m, m, 0.10)["n"] == 24


class TestRollingExcess:
    def test_includes_the_window_starting_at_inception(self):
        # 240 months, 36-month windows -> 205 windows if month 0 is included,
        # 204 if the off-by-one is present.
        m = _mkt()
        x = m * 1.0
        assert len(F.rolling_excess(x, m, 36)) == 240 - 36 + 1

    def test_identical_series_have_zero_excess(self):
        m = _mkt()
        assert np.allclose(F.rolling_excess(m, m, 36).values, 0.0, atol=1e-9)

    def test_a_constant_outperformer_shows_its_annualised_edge(self):
        m = pd.Series(np.full(240, 0.0), index=IDX)
        x = pd.Series(np.full(240, 0.01), index=IDX)
        got = F.rolling_excess(x, m, 36)
        assert got.iloc[0] == pytest.approx((1.01 ** 12 - 1) * 100, abs=1e-6)

    def test_too_short_a_series_returns_empty_rather_than_erroring(self):
        m = _mkt().iloc[:12]
        assert F.rolling_excess(m, m, 36).empty


class TestVerdictCalibration:
    def _corr(self, sv_gold, sv_dur, control=0.646):
        names = ["gold", "duration", "smallval"]
        c = pd.DataFrame(np.eye(3), index=names, columns=names)
        c.loc["gold", "duration"] = c.loc["duration", "gold"] = control
        c.loc["smallval", "gold"] = c.loc["gold", "smallval"] = sv_gold
        c.loc["smallval", "duration"] = c.loc["duration", "smallval"] = sv_dur
        return c

    def _monthly(self, sv_tail, mkt_tail=-7.7):
        return pd.DataFrame({"d10_mean": {"gold": 1.0, "duration": 1.6,
                                          "smallval": sv_tail,
                                          "market": mkt_tail}})

    def test_passes_a_when_less_correlated_than_the_control(self):
        v = F.verdict(self._corr(0.40, 0.38), self._monthly(-8.4))
        assert v["uncorrelated"]

    def test_fails_a_when_more_correlated_than_the_control(self):
        v = F.verdict(self._corr(0.72, 0.38), self._monthly(-8.4))
        assert not v["uncorrelated"]

    def test_an_absolute_bar_would_have_rejected_the_control_pair(self):
        # The reason the rule is calibrated: gold vs duration is 0.646, which
        # any bar tight enough to look "uncorrelated" would fail.
        assert 0.646 > F.AXIS_CORR_MAX

    def test_amplifying_the_tail_fails_b_even_when_a_passes(self):
        v = F.verdict(self._corr(0.10, 0.10), self._monthly(-8.4))
        assert v["uncorrelated"]
        assert v["amplifies_tail"]
        assert not v["is_third_axis"]

    def test_a_genuine_third_axis_passes_both(self):
        v = F.verdict(self._corr(0.10, 0.10), self._monthly(+1.2))
        assert v["is_third_axis"]

    def test_missing_market_row_raises_rather_than_guessing(self):
        m = self._monthly(-8.4).drop(index="market")
        with pytest.raises(ValueError):
            F.verdict(self._corr(0.4, 0.4), m)


class TestRealData:
    def test_the_whole_test_runs(self):
        F.main()

    def test_small_value_and_micro_are_one_decision_not_two(self):
        d = F.load_inputs()
        assert d["smallval"].corr(d["microcap"]) > 0.94

    def test_gold_and_duration_offset_while_small_value_amplifies(self):
        d = F.load_inputs()
        mkt = F.tail_stats(d["market"], d["market"], 0.10)["mean"]
        assert F.tail_stats(d["gold"], d["market"], 0.10)["mean"] > 0
        assert F.tail_stats(d["duration"], d["market"], 0.10)["mean"] > 0
        assert F.tail_stats(d["smallval"], d["market"], 0.10)["mean"] < mkt
