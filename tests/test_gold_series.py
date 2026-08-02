"""Tests for the gold series validation.

A code review proved the original three tests were structurally blind to the
ORDER of every month before GLD exists (2004-12): test 1 only compares the
overlap, test 2 compounds within calendar years, and test 3's CAGR is
order-invariant while its max drawdown is fixed by the 1980-99 trough.
Permuting 1996-98 and 2002-03 left every headline number bit-identical while
moving gold's dot-com return from +7.89% to +24.24%.

TEST 4 closes that by checking path-dependent quantities against Portfolio
Visualizer's own drawdown and rolling-return tables. These tests confirm it
actually rejects the attack rather than merely existing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import validate_gold_series as V


def _audit(s: pd.Series) -> list[str]:
    """The TEST 4 checks, as a callable predicate."""
    s = s[s.index >= "1972-01-01"]
    wc = (1 + s).cumprod()
    under = wc / wc.cummax() - 1.0
    fails = []
    for name, (a, b, pv) in V.PV_STRESS_DD.items():
        win = s.loc[a:b]
        if win.empty:
            continue
        mine = V.maxdd(win) * 100
        if mine < pv - 1e-9 or (mine - pv) > 3.00:
            fails.append(f"stress:{name}")
    bad = sum(1 for st, tr, pv in V.PV_WORST_DD
              if not under.loc[st:tr].empty
              and abs(under.loc[st:tr].min() * 100 - pv) > 2.00)
    if bad > 1:
        fails.append(f"worst-dd:{bad}")
    return fails


@pytest.fixture(scope="module")
def gold():
    return V.load_gold()


class TestRealSeriesPasses:
    def test_the_shipped_series_satisfies_the_path_checks(self, gold):
        assert _audit(gold) == []

    def test_worst_drawdowns_match_pv_by_depth_and_date(self, gold):
        g = gold[gold.index >= "1972-01-01"]
        wc = (1 + g).cumprod()
        under = wc / wc.cummax() - 1.0
        for start, trough, pv_dd in V.PV_WORST_DD:
            mine = under.loc[start:trough].min() * 100
            assert abs(mine - pv_dd) <= 2.00, (
                f"drawdown {start}..{trough}: {mine:.2f}% vs PV {pv_dd:.2f}%")

    def test_monthly_drawdown_never_exceeds_pv_daily(self, gold):
        # Month-end sampling cannot see an intra-month trough, so a monthly
        # figure DEEPER than PV's daily one is impossible and would be a defect.
        g = gold[gold.index >= "1972-01-01"]
        for name, (a, b, pv) in V.PV_STRESS_DD.items():
            win = g.loc[a:b]
            if win.empty:
                continue
            assert V.maxdd(win) * 100 >= pv - 1e-9, (
                f"{name}: monthly drawdown deeper than the daily figure")


class TestPermutationIsRejected:
    """The specific attack that defeated the original tests."""

    @staticmethod
    def _permute(g, spans, seed):
        rng = np.random.default_rng(seed)
        out = g.copy()
        for lo, hi in spans:
            m = (out.index.year >= lo) & (out.index.year <= hi)
            v = out[m].values.copy()
            rng.shuffle(v)
            out.loc[m] = v
        return out

    def test_cross_year_permutation_is_caught(self, gold):
        bad = self._permute(gold, [(1996, 1998), (2002, 2003)], 0)
        assert _audit(bad), (
            "the permutation that left tests 1-3 bit-identical still passes")

    def test_caught_across_multiple_seeds(self, gold):
        caught = sum(bool(_audit(self._permute(gold, [(1996, 1998), (2002, 2003)], s)))
                     for s in range(6))
        assert caught >= 5, f"only {caught}/6 permutations rejected"

    def test_reordering_inside_a_window_cannot_change_its_return(self, gold):
        # Documents WHY the dot-com headline was never at risk from ordering:
        # compounding is commutative, so shuffling months STRICTLY INSIDE the
        # window leaves its cumulative return identical. Only the path moves --
        # which is what TEST 4 constrains. (Moving months ACROSS the window
        # boundary is a different attack, and test 2's annual returns catch it.)
        rng = np.random.default_rng(0)
        bad = gold.copy()
        m = (bad.index >= "2000-03-31") & (bad.index <= "2002-10-31")
        v = bad[m].values.copy()
        rng.shuffle(v)
        bad.loc[m] = v
        a = (1 + gold.loc["2000-03":"2002-10"]).prod()
        b = (1 + bad.loc["2000-03":"2002-10"]).prod()
        assert a == pytest.approx(b)

    def test_within_window_reshuffles_are_mostly_caught_on_the_path(self, gold):
        # Not all of them: the residual gap is a reshuffle that preserves every
        # drawdown extreme. Narrow, and benign for a cumulative-return finding.
        caught = 0
        for seed in range(6):
            rng = np.random.default_rng(seed)
            bad = gold.copy()
            m = (bad.index >= "2000-03-31") & (bad.index <= "2002-10-31")
            v = bad[m].values.copy()
            rng.shuffle(v)
            bad.loc[m] = v
            caught += bool(_audit(bad))
        assert caught >= 4, f"only {caught}/6 within-window reshuffles rejected"
