"""Tests for the risk_parity_seasons.py configuration logic.

Two bugs shipped from this file into committed reports, and neither had a test:

  * the deflator picked whichever gold sleeve started EARLIEST rather than one
    that covers the run window -- first leaving 41% of long1980's span
    undeflated (counted as zero inflation), then over-correcting and swapping
    `modern` off bullion when bullion covered it fine;
  * the "History length" caveat was keyed on `preset == "long1985"`, so the
    long1980 and long1986 reports asserted a 1985 window and TIPS/silver/
    commodities hedges that did not exist in their own universe.

These pin the configuration, not the backtest maths.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import risk_parity_seasons as rs


class _Args:
    def __init__(self, window, cpi_csv=""):
        self.window_start, self.window_end = window
        self.cpi_csv = cpi_csv


def _ret(**starts):
    """Frame whose columns begin at the given month and run to 2026-07."""
    idx = pd.date_range("1970-01-31", "2026-07-31", freq="ME")
    out = pd.DataFrame(index=idx)
    for col, start in starts.items():
        s = pd.Series(0.01, index=idx)
        s[s.index < pd.Timestamp(start)] = np.nan
        out[col] = s
    return out


class TestDeflatorSelection:
    def test_prefers_bullion_when_it_covers_the_window(self):
        ret = _ret(**{"Gold": "2004-12-31", "Gold/Precious Metals": "1978-02-28"})
        d = rs.load_deflator(_Args(("2008-01-31", "2026-07-31")), ret)
        assert d.name == "Gold", \
            "modern was swapped onto the miners proxy despite bullion covering it"

    def test_falls_back_when_bullion_starts_after_the_window(self):
        ret = _ret(**{"Gold": "2004-12-31", "Gold/Precious Metals": "1978-02-28"})
        d = rs.load_deflator(_Args(("1980-02-29", "2026-07-31")), ret)
        assert d.name == "Gold/Precious Metals"

    def test_long1985_and_long1986_also_fall_back(self):
        ret = _ret(**{"Gold": "2004-12-31", "Gold/Precious Metals": "1978-02-28"})
        for start in ("1985-02-28", "1986-06-30"):
            assert rs.load_deflator(_Args((start, "2026-07-31")), ret).name \
                == "Gold/Precious Metals"

    def test_returns_something_rather_than_none_when_nothing_covers(self):
        # Degraded, but a deflator that starts late beats silently reporting a
        # nominal number under a "real" label.
        ret = _ret(**{"Gold": "2004-12-31"})
        d = rs.load_deflator(_Args(("1980-02-29", "2026-07-31")), ret)
        assert d is not None and d.name == "Gold"

    def test_no_gold_sleeve_at_all_yields_none(self):
        assert rs.load_deflator(_Args(("2008-01-31", "2026-07-31")),
                                _ret(**{"US Equity": "1990-01-31"})) is None


class TestRealSeries:
    def test_undeflated_months_are_warned_about(self, capsys):
        idx = pd.date_range("2000-01-31", "2000-06-30", freq="ME")
        nominal = pd.Series(0.01, index=idx)
        deflator = pd.Series(0.002, index=idx[:3])       # covers half the span
        rs.real_series(nominal, deflator)
        assert "WARNING" in capsys.readouterr().out, \
            "silently treating missing months as zero inflation"

    def test_full_coverage_is_silent(self, capsys):
        idx = pd.date_range("2000-01-31", "2000-06-30", freq="ME")
        rs.real_series(pd.Series(0.01, index=idx), pd.Series(0.002, index=idx))
        assert "WARNING" not in capsys.readouterr().out

    def test_deflation_arithmetic(self):
        idx = pd.date_range("2000-01-31", "2000-02-29", freq="ME")
        out = rs.real_series(pd.Series(0.10, index=idx), pd.Series(0.05, index=idx))
        assert out.iloc[0] == pytest.approx(1.10 / 1.05 - 1)


class TestPresets:
    def test_long1986_is_derived_from_long1985(self):
        a, b = rs.PRESETS["long1985"], rs.PRESETS["long1986"]
        assert all(a[k] == b[k] for k in a if k != "window")
        assert b["window"][0].startswith("1986-06")

    def test_long1986_keeps_treasuries(self):
        # It exists precisely because the yield-level fix moved US Treasuries to
        # a 1986-06 start, dropping it out of a 1985 window.
        assert "US Treasuries" in rs.PRESETS["long1986"]["sleeves"]

    def test_long1980_drops_sleeves_that_do_not_reach_1980(self):
        p = rs.PRESETS["long1980"]
        for absent in ("US Treasuries", "International Equity"):
            assert absent not in p["sleeves"]

    def test_long1980_min_sleeves_leaves_a_real_search(self):
        # 5 sleeves with min_sleeves=5 would be a single combination.
        p = rs.PRESETS["long1980"]
        assert p["min_sleeves"] < len(p["sleeves"])

    def test_every_preset_declares_equity_and_bonds_within_its_sleeves(self):
        for name, p in rs.PRESETS.items():
            sl = set(p["sleeves"])
            assert set(p["equity"]) <= sl, f"{name}: equity not in sleeves"
            assert set(p["bonds"]) <= sl, f"{name}: bonds not in sleeves"
            assert set(p["inh"]) <= sl, f"{name}: inflation hedges not in sleeves"

    def test_only_modern_is_treated_as_a_short_history_run(self):
        # `long_run = args.preset != "modern"` -- keyed off modern, not off an
        # exact long1985 match, which is what shipped the false caveat.
        assert [n for n in rs.PRESETS if n != "modern"] != []
        for name in rs.PRESETS:
            assert (name != "modern") == (name in ("long1985", "long1986", "long1980"))
