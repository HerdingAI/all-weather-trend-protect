"""Tests for the drawdown-ladder search.

Each assertion pins a defect a code review found in a ladder that had already
been reported:

  * the ceiling was enforced GROSS of costs but reported NET, so every rung
    breached the constraint it was labelled with (-40.04, -35.05, -30.04,
    -25.02, -20.01 against 40/35/30/25/20);
  * window slicing used dropna(axis=1, how="any"), deleting a whole asset class
    over a handful of missing months -- the 1986 window lost Long Treasuries and
    US Aggregate Bonds and concluded a 20% ceiling was infeasible, when shifting
    the start five months yields a feasible 20% book;
  * worst_rolling dropped the earliest window, the one an unlucky entrant cares
    most about;
  * the reported optimum was a best-of-475k with no selection-bias correction.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import drawdown_ladder as D


class TestMetrics:
    """Closed-form properties. A monotonic series has no drawdown; a constant
    series compounds to its own rate."""

    def test_monotonic_series_has_zero_drawdown(self):
        w = np.cumprod(1 + np.full((120, 1), 0.01), axis=0)
        assert D.max_drawdown(w)[0] == pytest.approx(0.0)

    def test_monotonic_series_is_never_underwater(self):
        w = np.cumprod(1 + np.full((120, 1), 0.01), axis=0)
        assert D.longest_underwater(w)[0] == 0

    def test_known_drawdown_is_measured_exactly(self):
        r = np.array([0.0, -0.5, 0.0, 0.0])[:, None]
        assert D.max_drawdown(np.cumprod(1 + r, axis=0))[0] == pytest.approx(-0.5)

    def test_constant_return_gives_that_cagr(self):
        r = np.full((120, 1), 0.01)
        w = np.cumprod(1 + r, axis=0)
        assert D.cagr(w, 120)[0] == pytest.approx(1.01 ** 12 - 1)

    def test_underwater_counts_months_below_the_prior_peak(self):
        r = np.array([0.10, -0.20, 0.0, 0.0, 0.50])[:, None]
        assert D.longest_underwater(np.cumprod(1 + r, axis=0))[0] == 3

    def test_worst_rolling_includes_the_very_first_month(self):
        # The crash is in month 0 ONLY. Because w is already post-first-return,
        # w[120]/w[0] spans months 1..120 and misses it entirely -- so an
        # investor who bought at inception, the unlucky entrant the study is
        # about, is the one case the metric skipped.
        r = np.concatenate([[-0.40], np.zeros(130)])[:, None]
        w = np.cumprod(1 + r, axis=0)
        got = D.worst_rolling(w, 120)[0]
        assert got < -0.04, (
            f"the inception-start window was omitted (worst 10y = {got:.4%}; "
            "a -40% first month should dominate it)")


class TestCosts:
    def test_no_turnover_means_no_cost(self):
        # Identical returns on every asset: weights never drift, nothing to trade.
        R = np.tile(np.full((60, 1), 0.01), (1, 3))
        w = np.array([1 / 3, 1 / 3, 1 / 3])
        assert D.net_of_costs(R, w)["turnover_ann"] == pytest.approx(0.0, abs=1e-12)

    def test_costs_reduce_return(self):
        rng = np.random.default_rng(0)
        R = rng.normal(0.006, 0.04, (240, 3))
        w = np.array([0.5, 0.3, 0.2])
        assert D.net_of_costs(R, w, cost_bps=50)["cagr"] < \
               D.net_of_costs(R, w, cost_bps=0)["cagr"]

    def test_turnover_matches_a_hand_computed_month(self):
        # Two assets at 50/50; one returns +10%, the other 0. Portfolio return
        # is 5%; turnover = sum_i w_i |r_i - r_p| / (1 + r_p).
        R = np.array([[0.10, 0.00]])
        w = np.array([0.5, 0.5])
        expected = (0.5 * abs(0.10 - 0.05) + 0.5 * abs(0.00 - 0.05)) / 1.05
        assert D.net_of_costs(R, w, cost_bps=0)["turnover_ann"] == \
               pytest.approx(expected * 12)


class TestWeightEnumeration:
    def test_grid_weights_sum_to_one(self):
        gw = D.grid_weights(3, 0.25)
        assert np.allclose(gw.sum(axis=1), 1.0)

    def test_grid_is_complete(self):
        # compositions of 1.0 into k parts on a 1/n grid = C(n+k-1, k-1)
        from math import comb
        for k, step in ((2, 0.25), (3, 0.25), (4, 0.5)):
            n = int(round(1 / step))
            assert len(D.grid_weights(k, step)) == comb(n + k - 1, k - 1)

    def test_weights_are_non_negative(self):
        assert (D.grid_weights(4, 0.25) >= 0).all()


class TestWindowSelection:
    """A whole asset class must not vanish over a few missing months."""

    def test_exposure_is_kept_when_it_covers_the_window(self):
        idx = pd.date_range("1990-01-31", periods=120, freq="ME")
        panel = pd.DataFrame({"A": 0.01, "B": 0.01}, index=idx)
        panel.loc[idx[:5], "B"] = np.nan          # starts 5 months late
        sub, dropped = D.window_slice(panel, "1990-06")
        assert "B" in sub.columns, f"B was dropped: {dropped}"

    def test_exposure_absent_from_the_window_is_dropped_and_named(self):
        idx = pd.date_range("1990-01-31", periods=120, freq="ME")
        panel = pd.DataFrame({"A": 0.01, "B": np.nan}, index=idx)
        panel.loc[idx[60:], "B"] = 0.01           # only the second half
        sub, dropped = D.window_slice(panel, "1990-01")
        assert "B" not in sub.columns and any("B" in d for d in dropped)

    def test_result_has_no_missing_values(self):
        idx = pd.date_range("1990-01-31", periods=60, freq="ME")
        panel = pd.DataFrame({"A": 0.01, "B": 0.02}, index=idx)
        panel.loc[idx[:3], "B"] = np.nan
        sub, _ = D.window_slice(panel, "1990-04")
        assert not sub.isna().any().any()


class TestCeilingIsEnforcedNet:
    def test_reported_book_satisfies_its_own_ceiling(self):
        rng = np.random.default_rng(3)
        R = rng.normal(0.006, 0.045, (360, 4))
        w = D.solve_ceiling(R, 0.25, rng, draws=4000)
        assert w is not None
        m = D.net_of_costs(R, w)
        assert -m["dd"] <= 0.25 + 1e-9, (
            f"reported net drawdown {m['dd']:.4f} breaches the 25% ceiling")

    def test_infeasible_ceiling_returns_none_rather_than_a_breach(self):
        rng = np.random.default_rng(4)
        R = rng.normal(0.01, 0.20, (240, 3))       # far too volatile for 1%
        assert D.solve_ceiling(R, 0.01, rng, draws=1500) is None
