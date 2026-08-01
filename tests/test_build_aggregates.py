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

    def test_truncated_final_archive_month_is_dropped_for_everyone(self):
        # The real archive ends 2026-07-17. Every ticker trades through that
        # date, so a per-ticker completeness test alone would call July
        # "complete" and publish a 17-day stub as a full month.
        dates, tks, rets = [], [], []
        for d in pd.bdate_range("2026-06-01", "2026-07-17"):
            dates.append(d); tks.append("A"); rets.append(0.001)
        panel = pd.DataFrame({"date": dates, "ticker": tks, "daily_return": rets})
        out = ba.daily_to_monthly_returns(panel, complete_only=True)
        assert pd.Timestamp("2026-07-31") not in out.index, "truncated final month kept"
        assert pd.Timestamp("2026-06-30") in out.index, "complete month dropped"

    def test_final_month_kept_when_archive_reaches_month_end(self):
        dates, tks, rets = [], [], []
        for d in pd.bdate_range("2026-06-01", "2026-07-31"):
            dates.append(d); tks.append("A"); rets.append(0.001)
        panel = pd.DataFrame({"date": dates, "ticker": tks, "daily_return": rets})
        out = ba.daily_to_monthly_returns(panel, complete_only=True)
        assert pd.Timestamp("2026-07-31") in out.index


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

class TestSpliceTail:
    """The daily archive ends mid-July 2026, so the extended panel stops at
    2026-06. Dropping July from the canonical file would silently shorten every
    downstream window (the eval TEST end is 2026-07-31). The two constructions
    agree to <1 bp/month over 497 overlapping months, so carrying the missing
    tail months over from the monthly-native panel is safe -- and reported.
    """

    IDX = pd.to_datetime(["2000-01-31", "2000-02-29", "2000-03-31"])

    def test_appends_months_missing_from_extended(self):
        ext = pd.DataFrame({"X": [0.1, 0.2]}, index=self.IDX[:2])
        native = pd.DataFrame({"X": [0.9, 0.9, 0.3]}, index=self.IDX)
        out, added = ba.splice_tail(ext, native)
        assert added == [pd.Timestamp("2000-03-31")]
        assert out.loc[pd.Timestamp("2000-03-31"), "X"] == pytest.approx(0.3)

    def test_does_not_overwrite_existing_extended_months(self):
        ext = pd.DataFrame({"X": [0.1, 0.2]}, index=self.IDX[:2])
        native = pd.DataFrame({"X": [0.9, 0.9, 0.3]}, index=self.IDX)
        out, _ = ba.splice_tail(ext, native)
        assert out.loc[pd.Timestamp("2000-01-31"), "X"] == pytest.approx(0.1)

    def test_no_op_when_extended_already_current(self):
        ext = pd.DataFrame({"X": [0.1, 0.2, 0.3]}, index=self.IDX)
        native = pd.DataFrame({"X": [0.9, 0.9, 0.9]}, index=self.IDX)
        out, added = ba.splice_tail(ext, native)
        assert added == []
        assert out["X"].tolist() == pytest.approx([0.1, 0.2, 0.3])

    def test_never_backfills_history_before_extended_start(self):
        # Only the TAIL is spliced. Older native months must not reappear, or
        # the panel would silently mix constructions across its whole span.
        ext = pd.DataFrame({"X": [0.2, 0.3]}, index=self.IDX[1:])
        native = pd.DataFrame({"X": [0.9, 0.9, 0.9]}, index=self.IDX)
        out, added = ba.splice_tail(ext, native)
        assert added == []
        assert pd.Timestamp("2000-01-31") not in out.index


class TestAssetClassSummary:
    """`asset_class_summary.csv` is derived from the panel, and `docs/coverage.md`
    is a transcription of it. Rebuilding the panel without rebuilding this leaves
    a published file contradicting the data beside it -- which is exactly what
    happened: it kept advertising the contaminated 2.24% Treasuries sleeve and a
    `Volatility` row that no longer exists.

    Schema must match pull_returns.py's writer exactly so the two producers stay
    interchangeable.
    """

    IDX = pd.to_datetime(["2000-01-31", "2000-02-29", "2000-03-31"])

    def _panel(self):
        return pd.DataFrame({"A": [0.10, -0.05, 0.02], "B": [np.nan, 0.01, 0.03]},
                            index=self.IDX)

    def test_schema_matches_the_puller(self):
        out = ba.asset_class_summary(self._panel())
        assert list(out.columns) == [
            "asset_class", "first_month", "last_month", "n_months",
            "ann_return_pct", "ann_vol_pct", "min_month_pct", "max_month_pct"]

    def test_stats_are_computed_over_non_null_months_only(self):
        out = ba.asset_class_summary(self._panel()).set_index("asset_class")
        assert out.loc["B", "n_months"] == 2
        assert out.loc["B", "first_month"] == pd.Timestamp("2000-02-29")
        assert out.loc["A", "ann_return_pct"] == pytest.approx(
            self._panel()["A"].mean() * 12 * 100)

    def test_percentages_not_fractions(self):
        out = ba.asset_class_summary(self._panel()).set_index("asset_class")
        assert out.loc["A", "max_month_pct"] == pytest.approx(10.0)

    def test_empty_sleeve_is_omitted(self):
        p = self._panel()
        p["C"] = np.nan
        assert "C" not in set(ba.asset_class_summary(p)["asset_class"])


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

    def test_lost_data_is_not_reported_as_a_match(self):
        # a - b is NaN wherever EITHER side is NaN, and nanmax ignores exactly
        # those cells -- so a rebuild that dropped a whole sleeve read as a
        # perfect reproduction. This is the script's own failure mode: the fix
        # works by removing constituents, which turns values into NaN.
        good = pd.DataFrame({"X": [0.1, 0.2], "Y": [0.3, 0.4]}, index=self.IDX)
        lost = good.copy()
        lost["Y"] = np.nan
        d, why = ba._max_abs_diff(lost, good)
        assert d is None, "a rebuild that lost an entire sleeve compared equal"
        assert "missing" in why.lower() or "nan" in why.lower()

    def test_spurious_data_is_not_reported_as_a_match(self):
        good = pd.DataFrame({"X": [0.1, 0.2], "Y": [np.nan, np.nan]}, index=self.IDX)
        gained = good.copy()
        gained["Y"] = [0.9, 0.9]
        d, why = ba._max_abs_diff(gained, good)
        assert d is None

    def test_matching_nan_positions_still_compare_equal(self):
        a = pd.DataFrame({"X": [np.nan, 0.2]}, index=self.IDX)
        d, why = ba._max_abs_diff(a, a.copy())
        assert d == pytest.approx(0.0) and why == ""

    def test_all_nan_frames_are_equal_not_different(self):
        # np.nanmax over an all-NaN slice warns and returns nan; nan <= tol is
        # False, so two identical frames were reported as differing.
        a = pd.DataFrame({"X": [np.nan, np.nan]}, index=self.IDX)
        d, why = ba._max_abs_diff(a, a.copy())
        assert d == pytest.approx(0.0)


class TestBusinessDayHelpers:
    """`_last_bday` backs the archive-truncation guard. Rolling the wrong way
    silently drops genuinely complete months (29% of months end on a weekend).
    """

    def test_last_bday_of_month_ending_on_sunday(self):
        # 2026-05-31 is a Sunday; the last business day is Friday 2026-05-29.
        assert ba._last_bday(pd.Period("2026-05", "M")) == pd.Timestamp("2026-05-29")

    def test_last_bday_of_month_ending_on_saturday(self):
        # 2026-02-28 is a Saturday -> Friday 2026-02-27.
        assert ba._last_bday(pd.Period("2026-02", "M")) == pd.Timestamp("2026-02-27")

    def test_last_bday_of_month_ending_on_weekday(self):
        assert ba._last_bday(pd.Period("2026-07", "M")) == pd.Timestamp("2026-07-31")

    def test_last_bday_never_leaves_the_month(self):
        for p in pd.period_range("1990-01", "2030-12", freq="M"):
            assert ba._last_bday(p).to_period("M") == p, f"{p} escaped its month"

    def test_first_bday_of_month_starting_on_weekend(self):
        # 2026-08-01 is a Saturday -> Monday 2026-08-03.
        assert ba._first_bday(pd.Period("2026-08", "M")) == pd.Timestamp("2026-08-03")

    def test_first_bday_never_leaves_the_month(self):
        for p in pd.period_range("1990-01", "2030-12", freq="M"):
            assert ba._first_bday(p).to_period("M") == p


class TestCompleteMonthEndToEnd:
    """A weekend-ending month that the archive fully covers must survive."""

    def test_month_ending_on_a_weekend_is_kept(self):
        # Archive runs through Fri 2026-05-29. May is complete (05-30/31 are the
        # weekend), so it must not be dropped as truncated.
        dates = pd.bdate_range("2026-04-01", "2026-05-29")
        panel = pd.DataFrame({"date": dates, "ticker": "A",
                              "daily_return": [0.001] * len(dates)})
        out = ba.daily_to_monthly_returns(panel, complete_only=True)
        assert pd.Timestamp("2026-05-31") in out.index, "complete May was dropped"


class TestInteriorCoverage:
    """Edge-month checks only look at a ticker's global first/last month, so a
    mid-history gap (delist/relist, halt, vendor gap) was compounded from a stub
    and published as a full month.
    """

    def _panel_with_interior_gap(self):
        rows = []
        for d in pd.bdate_range("2026-01-01", "2026-03-31"):
            rows.append((d, "MKT", 0.0))
            # A trades all of Jan and Mar, but only the last 2 days of Feb.
            if d.month != 2 or d >= pd.Timestamp("2026-02-26"):
                rows.append((d, "A", 0.05))
        return pd.DataFrame(rows, columns=["date", "ticker", "daily_return"])

    def test_sparse_interior_month_is_dropped(self):
        out = ba.daily_to_monthly_returns(self._panel_with_interior_gap(),
                                          complete_only=True)
        assert pd.isna(out.loc[pd.Timestamp("2026-02-28"), "A"]), \
            "a 2-day stub was published as a full month"

    def test_full_interior_months_are_kept(self):
        out = ba.daily_to_monthly_returns(self._panel_with_interior_gap(),
                                          complete_only=True)
        assert not pd.isna(out.loc[pd.Timestamp("2026-01-31"), "A"])
        assert not pd.isna(out.loc[pd.Timestamp("2026-03-31"), "A"])


class TestSpliceTailGuards:
    def test_empty_extended_raises_rather_than_discarding_everything(self):
        native = pd.DataFrame({"X": [0.1, 0.2]},
                              index=pd.to_datetime(["2000-01-31", "2000-02-29"]))
        empty = native.iloc[:0]
        with pytest.raises(ValueError):
            ba.splice_tail(empty, native)


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
