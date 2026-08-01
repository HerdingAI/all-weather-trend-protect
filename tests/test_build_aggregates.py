"""Unit tests for build_aggregates.py — the offline, corrected asset-class builder.

These cover the pure functions only. The end-to-end data gates (old-rule
reproduction, expected per-sleeve deltas) are assertions inside
build_aggregates.py itself, in the style of audit_integrity.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import build_aggregates as ba


# --------------------------------------------------------------------------- #
# Return-series policy
# --------------------------------------------------------------------------- #

class TestReturnPolicy:
    def test_yield_levels_are_not_returns(self):
        for t in ("^TNX", "^FVX", "^TYX"):
            assert not ba.is_return_series(t, ("n", "US Treasuries", "YIELD", ""))

    def test_price_only_indices_and_vix_are_not_returns(self):
        for t in ("^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX"):
            assert not ba.is_return_series(t, ("n", "US Equity", "INDEX", ""))

    def test_funds_and_etfs_are_returns(self):
        assert ba.is_return_series("VUSTX", ("n", "US Treasuries", "MUTUALFUND", ""))
        assert ba.is_return_series("SPY", ("n", "US Equity", "ETF", ""))

    def test_single_stock_schema_is_safe(self):
        # STOCKS tuples are (name, asset_class, gics_sector) — meta[2] is a
        # sector, never a kind, so the same test must not misfire.
        assert ba.is_return_series("GE", ("GE common stock", "Equity (single stock)", "Industrials"))


# --------------------------------------------------------------------------- #
# Grouping
# --------------------------------------------------------------------------- #

class TestAggregatableGroups:
    META = {
        "SPY":   ("SPDR", "US Equity", "ETF", ""),
        "^GSPC": ("S&P",  "US Equity", "INDEX", ""),
        "VUSTX": ("Vang", "US Treasuries", "MUTUALFUND", ""),
        "^TNX":  ("10y",  "US Treasuries", "YIELD", ""),
        "^VIX":  ("VIX",  "Volatility", "INDEX", ""),
        "XLF":   ("XLF",  "Sector-Financials", "ETF", ""),
        "GE":    ("GE",   "Equity (single stock)", "Industrials"),
    }

    def test_excludes_non_return_series(self):
        g = ba.aggregatable_groups(self.META, available=set(self.META))
        assert g["US Equity"] == ["SPY"]
        assert g["US Treasuries"] == ["VUSTX"]

    def test_volatility_sleeve_disappears_entirely(self):
        g = ba.aggregatable_groups(self.META, available=set(self.META))
        assert "Volatility" not in g

    def test_still_excludes_sectors_and_single_stocks(self):
        g = ba.aggregatable_groups(self.META, available=set(self.META))
        assert not any(k.startswith("Sector-") for k in g)
        assert "Equity (single stock)" not in g

    def test_legacy_mode_reproduces_the_buggy_rule(self):
        # The reproduction gate depends on this reproducing pull_returns.py
        # exactly as it was before the fix.
        g = ba.aggregatable_groups(self.META, available=set(self.META), legacy=True)
        assert sorted(g["US Treasuries"]) == ["VUSTX", "^TNX"]
        assert g["Volatility"] == ["^VIX"]

    def test_unavailable_tickers_are_skipped(self):
        g = ba.aggregatable_groups(self.META, available={"SPY"})
        assert g == {"US Equity": ["SPY"]}


# --------------------------------------------------------------------------- #
# Equal-weight aggregation
# --------------------------------------------------------------------------- #

class TestEqualWeight:
    def test_mean_across_constituents(self):
        idx = pd.to_datetime(["2000-01-31", "2000-02-29"])
        wide = pd.DataFrame({"A": [0.10, 0.20], "B": [0.30, 0.40]}, index=idx)
        out = ba.equal_weight(wide, {"X": ["A", "B"]})
        assert out["X"].tolist() == pytest.approx([0.20, 0.30])

    def test_skips_missing_constituents_that_month(self):
        idx = pd.to_datetime(["2000-01-31", "2000-02-29"])
        wide = pd.DataFrame({"A": [0.10, np.nan], "B": [0.30, 0.40]}, index=idx)
        out = ba.equal_weight(wide, {"X": ["A", "B"]})
        # Feb averages only B, matching the time-varying equal-weight convention.
        assert out["X"].tolist() == pytest.approx([0.20, 0.40])

    def test_sleeve_with_no_constituent_that_month_is_nan_not_zero(self):
        idx = pd.to_datetime(["2000-01-31", "2000-02-29"])
        wide = pd.DataFrame({"A": [np.nan, 0.05], "B": [0.10, 0.20]}, index=idx)
        out = ba.equal_weight(wide, {"X": ["A"], "Y": ["B"]})
        assert pd.isna(out.loc[pd.Timestamp("2000-01-31"), "X"])
        assert out.loc[pd.Timestamp("2000-01-31"), "Y"] == pytest.approx(0.10)

    def test_month_with_no_data_at_all_is_dropped(self):
        # Matches pull_returns.py's dropna(how="all"): coverage starts at the
        # first month any sleeve exists, rather than padding empty leading rows.
        idx = pd.to_datetime(["2000-01-31", "2000-02-29"])
        wide = pd.DataFrame({"A": [np.nan, 0.05]}, index=idx)
        out = ba.equal_weight(wide, {"X": ["A"]})
        assert out.index.tolist() == [pd.Timestamp("2000-02-29")]


# --------------------------------------------------------------------------- #
# Daily -> monthly compounding
# --------------------------------------------------------------------------- #

class TestDailyToMonthly:
    def test_compounds_geometrically_not_additively(self):
        d = pd.DataFrame({
            "date": pd.to_datetime(["2000-01-04", "2000-01-05", "2000-01-31"]),
            "ticker": ["A"] * 3,
            "daily_return": [0.10, 0.10, 0.10],
        })
        out = ba.daily_to_monthly_returns(d, complete_only=False)
        # 1.1^3 - 1 = 0.331, not 0.30
        assert out.loc[pd.Timestamp("2000-01-31"), "A"] == pytest.approx(0.331)

    def test_hand_computed_month(self):
        d = pd.DataFrame({
            "date": pd.to_datetime(["2000-03-01", "2000-03-02"]),
            "ticker": ["A", "A"],
            "daily_return": [0.05, -0.02],
        })
        out = ba.daily_to_monthly_returns(d, complete_only=False)
        assert out.loc[pd.Timestamp("2000-03-31"), "A"] == pytest.approx(1.05 * 0.98 - 1)

    def test_index_is_month_end(self):
        d = pd.DataFrame({
            "date": pd.to_datetime(["2000-02-10"]),
            "ticker": ["A"],
            "daily_return": [0.01],
        })
        out = ba.daily_to_monthly_returns(d, complete_only=False)
        assert out.index[0] == pd.Timestamp("2000-02-29")  # leap year

    def test_separates_tickers(self):
        d = pd.DataFrame({
            "date": pd.to_datetime(["2000-01-10", "2000-01-10"]),
            "ticker": ["A", "B"],
            "daily_return": [0.10, 0.20],
        })
        out = ba.daily_to_monthly_returns(d, complete_only=False)
        assert out.loc[pd.Timestamp("2000-01-31"), "A"] == pytest.approx(0.10)
        assert out.loc[pd.Timestamp("2000-01-31"), "B"] == pytest.approx(0.20)


class TestPartialMonthRule:
    """A stub month must never masquerade as a full-month return."""

    def _panel(self):
        # A trades Jan 5 -> Mar 10. Jan is a partial first month (archive starts
        # Jan 3), Mar is a partial last month (archive ends Mar 31).
        dates, tks, rets = [], [], []
        for d in pd.bdate_range("2000-01-03", "2000-03-31"):
            if pd.Timestamp("2000-01-05") <= d <= pd.Timestamp("2000-03-10"):
                dates.append(d); tks.append("A"); rets.append(0.001)
            dates.append(d); tks.append("MKT"); rets.append(0.001)
        return pd.DataFrame({"date": dates, "ticker": tks, "daily_return": rets})

    def test_drops_incomplete_first_and_last_months(self):
        out = ba.daily_to_monthly_returns(self._panel(), complete_only=True)
        a = out["A"].dropna()
        assert pd.Timestamp("2000-01-31") not in a.index, "partial first month kept"
        assert pd.Timestamp("2000-03-31") not in a.index, "partial last month kept"
        assert pd.Timestamp("2000-02-29") in a.index, "complete month dropped"

    def test_full_coverage_ticker_keeps_all_months(self):
        out = ba.daily_to_monthly_returns(self._panel(), complete_only=True)
        assert out["MKT"].dropna().shape[0] == 3

    def test_complete_only_false_keeps_everything(self):
        out = ba.daily_to_monthly_returns(self._panel(), complete_only=False)
        assert out["A"].dropna().shape[0] == 3


# --------------------------------------------------------------------------- #
# Month-end level sampling (for ^TNX, which must NOT be compounded)
# --------------------------------------------------------------------------- #

class TestMonthEndLevels:
    def test_takes_last_observation_of_month(self):
        idx = pd.to_datetime(["2000-01-05", "2000-01-20", "2000-02-03"])
        px = pd.DataFrame({"^TNX": [6.0, 6.5, 5.0]}, index=idx)
        out = ba.month_end_levels(px)
        assert out.loc[pd.Timestamp("2000-01-31"), "^TNX"] == 6.5
        assert out.loc[pd.Timestamp("2000-02-29"), "^TNX"] == 5.0

    def test_does_not_compound(self):
        idx = pd.to_datetime(["2000-01-05", "2000-01-20"])
        px = pd.DataFrame({"^TNX": [6.0, 6.5]}, index=idx)
        out = ba.month_end_levels(px)
        assert out.iloc[0, 0] == 6.5  # a level, carried through untouched

    def test_gaps_are_not_forward_filled_across_months(self):
        idx = pd.to_datetime(["2000-01-05", "2000-03-05"])
        px = pd.DataFrame({"^TNX": [6.0, 5.0]}, index=idx)
        out = ba.month_end_levels(px)
        assert pd.Timestamp("2000-02-29") not in out.index or pd.isna(
            out.loc[pd.Timestamp("2000-02-29"), "^TNX"])


# --------------------------------------------------------------------------- #
# Universe reconciliation
# --------------------------------------------------------------------------- #

class TestDiffHelper:
    """Backs the reproduction gate, which must distinguish 'inputs changed'
    from 'file already fixed' rather than conflating them."""

    IDX = pd.to_datetime(["2000-01-31", "2000-02-29"])

    def test_identical_frames_report_zero(self):
        a = pd.DataFrame({"X": [0.1, 0.2]}, index=self.IDX)
        d, why = ba._max_abs_diff(a, a.copy())
        assert d == pytest.approx(0.0) and why == ""

    def test_value_difference_is_measured(self):
        a = pd.DataFrame({"X": [0.1, 0.2]}, index=self.IDX)
        b = pd.DataFrame({"X": [0.1, 0.25]}, index=self.IDX)
        d, _ = ba._max_abs_diff(a, b)
        assert d == pytest.approx(0.05)

    def test_differing_columns_reported_not_crashed(self):
        a = pd.DataFrame({"X": [0.1, 0.2]}, index=self.IDX)
        b = pd.DataFrame({"X": [0.1, 0.2], "Y": [0.0, 0.0]}, index=self.IDX)
        d, why = ba._max_abs_diff(a, b)
        assert d is None and "column sets differ" in why

    def test_differing_index_reported_not_crashed(self):
        a = pd.DataFrame({"X": [0.1]}, index=self.IDX[:1])
        b = pd.DataFrame({"X": [0.1, 0.2]}, index=self.IDX)
        d, why = ba._max_abs_diff(a, b)
        assert d is None and "index differs" in why


class TestUniverseReconciliation:
    def test_restricts_to_reference_universe(self):
        wide = pd.DataFrame(
            {"SPY": [0.01], "AUBAX": [0.02]},
            index=pd.to_datetime(["2020-01-31"]),
        )
        kept, dropped = ba.restrict_universe(wide, {"SPY"})
        assert list(kept.columns) == ["SPY"]
        assert dropped == ["AUBAX"]

    def test_reports_nothing_when_universes_match(self):
        wide = pd.DataFrame({"SPY": [0.01]}, index=pd.to_datetime(["2020-01-31"]))
        kept, dropped = ba.restrict_universe(wide, {"SPY"})
        assert dropped == []
