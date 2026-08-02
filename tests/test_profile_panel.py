"""Tests for profile_study_panel's return and statistic helpers.

`port()` computes every number in the candidate comparison now that the search
is withdrawn, and its drift/rebalance branch had no caller and no test at all.
`stats()` feeds the reconciliation gate. Both are pinned here against
closed-form answers rather than against themselves.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import profile_study_panel as P


IDX = pd.date_range("2000-01-31", periods=48, freq="ME")


class TestPortMonthlyRebalance:
    def test_single_asset_returns_that_asset(self):
        panel = pd.DataFrame({"A": np.full(48, 0.01), "B": np.full(48, 0.05)},
                             index=IDX)
        r = P.port(panel, {"A": 1.0})
        assert np.allclose(r.values, 0.01)

    def test_fifty_fifty_is_the_average_when_rebalanced_monthly(self):
        panel = pd.DataFrame({"A": np.full(48, 0.10), "B": np.full(48, 0.00)},
                             index=IDX)
        r = P.port(panel, {"A": 0.5, "B": 0.5})
        assert np.allclose(r.values, 0.05)

    def test_weights_are_normalised(self):
        panel = pd.DataFrame({"A": np.full(48, 0.10), "B": np.full(48, 0.00)},
                             index=IDX)
        # 2:2 must behave exactly like 0.5:0.5
        assert np.allclose(P.port(panel, {"A": 2.0, "B": 2.0}).values, 0.05)

    def test_only_months_where_every_constituent_has_data(self):
        panel = pd.DataFrame({"A": np.full(48, 0.01), "B": np.full(48, 0.01)},
                             index=IDX)
        panel.loc[IDX[:6], "B"] = np.nan
        assert len(P.port(panel, {"A": 0.5, "B": 0.5})) == 42


class TestPortDriftBranch:
    """The annual/quarterly path: weights drift between rebalance dates."""

    def test_annual_differs_from_monthly_when_returns_diverge(self):
        rng = np.random.default_rng(0)
        panel = pd.DataFrame({"A": rng.normal(0.02, 0.05, 48),
                              "B": rng.normal(-0.01, 0.05, 48)}, index=IDX)
        m = P.port(panel, {"A": 0.5, "B": 0.5}, rebalance="M")
        a = P.port(panel, {"A": 0.5, "B": 0.5}, rebalance="A")
        assert not np.allclose(m.values, a.values), \
            "the drift branch produced the monthly-rebalanced answer"

    def test_identical_assets_make_rebalancing_irrelevant(self):
        panel = pd.DataFrame({"A": np.full(48, 0.01), "B": np.full(48, 0.01)},
                             index=IDX)
        for freq in ("M", "Q", "A"):
            assert np.allclose(P.port(panel, {"A": 0.5, "B": 0.5},
                                      rebalance=freq).values, 0.01)

    def test_first_month_matches_the_target_weights(self):
        # Before any drift has accumulated, every policy must agree.
        rng = np.random.default_rng(1)
        panel = pd.DataFrame({"A": rng.normal(0.01, 0.04, 48),
                              "B": rng.normal(0.00, 0.04, 48)}, index=IDX)
        expected = 0.5 * panel["A"].iloc[0] + 0.5 * panel["B"].iloc[0]
        for freq in ("M", "Q", "A"):
            got = P.port(panel, {"A": 0.5, "B": 0.5}, rebalance=freq).iloc[0]
            assert got == pytest.approx(expected)

    def test_drift_follows_the_hand_computed_second_month(self):
        # A returns +10%, B returns 0 in month 1. Under annual rebalancing the
        # month-2 weights are 0.55/0.45 (0.5*1.1 and 0.5*1.0, renormalised).
        panel = pd.DataFrame({"A": [0.10, 0.20] + [0.0] * 46,
                              "B": [0.00, 0.00] + [0.0] * 46}, index=IDX)
        r = P.port(panel, {"A": 0.5, "B": 0.5}, rebalance="A")
        w_a = (0.5 * 1.10) / (0.5 * 1.10 + 0.5 * 1.00)
        assert r.iloc[1] == pytest.approx(w_a * 0.20)


class TestStats:
    def test_constant_series_gives_that_cagr_and_no_drawdown(self):
        st = P.stats(pd.Series(np.full(120, 0.01), index=pd.date_range(
            "2000-01-31", periods=120, freq="ME")))
        assert st["cagr"] == pytest.approx((1.01 ** 12 - 1) * 100)
        assert st["maxdd"] == pytest.approx(0.0)

    def test_sortino_uses_mar_zero(self):
        # Downside deviation must be measured about 0, not about the clipped
        # series' own mean -- the bug the code review found.
        r = pd.Series([0.10, -0.10] * 60,
                      index=pd.date_range("2000-01-31", periods=120, freq="ME"))
        expected_dsd = np.sqrt((np.minimum(r, 0.0) ** 2).mean()) * np.sqrt(12)
        st = P.stats(r)
        assert st["sortino"] == pytest.approx((r.mean() * 12) / expected_dsd)

    def test_known_drawdown_is_reported(self):
        r = pd.Series([0.0, -0.5, 0.0], index=pd.date_range(
            "2000-01-31", periods=3, freq="ME"))
        assert P.maxdd(r) == pytest.approx(-0.5)

    def test_short_series_returns_nothing_rather_than_a_wrong_number(self):
        assert P.stats(pd.Series([0.01] * 6)) == {}
