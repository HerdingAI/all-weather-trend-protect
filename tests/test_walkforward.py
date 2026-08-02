"""Tests for the walk-forward ladder.

The only property that makes a walk-forward result worth anything is that
selection never sees the months it is scored on. Everything else is bookkeeping.
So the first test plants an obvious signal in the future and asserts the
selection cannot exploit it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import walkforward_ladder as WF


def _dates(n):
    return pd.date_range("1990-01-31", periods=n, freq="ME")


class TestNoLookAhead:
    def test_selection_cannot_see_the_test_period(self):
        # Asset 1 is flat for the whole training span, then becomes wildly the
        # best performer AFTER the first refit boundary. A selector with
        # hindsight would load into it; one without cannot.
        n, k = 300, 3
        rng = np.random.default_rng(0)
        R = rng.normal(0.004, 0.02, (n, k))
        cut = 120                                   # min_train=10y
        R[:cut, 1] = 0.0
        R[cut:, 1] = 0.05                           # unmistakable future edge
        _, folds = WF.walk_forward(R, _dates(n), 0.40, min_train=10, hold=12,
                                   rng=np.random.default_rng(1), draws=3000)
        first = folds[0]
        assert first["feasible"]
        assert first["weights"][1] < 0.60, (
            "the first selection loaded into an asset that only outperforms "
            "after the training window ends -- hindsight leaked in")

    def test_first_refit_lands_exactly_at_min_train(self):
        n = 200
        R = np.random.default_rng(2).normal(0.004, 0.02, (n, 3))
        d = _dates(n)
        _, folds = WF.walk_forward(R, d, 0.40, min_train=10, hold=12,
                                   rng=np.random.default_rng(3), draws=1500)
        assert folds[0]["train_end"] == d[120]

    def test_oos_length_matches_the_held_out_span(self):
        n = 200
        R = np.random.default_rng(4).normal(0.004, 0.02, (n, 3))
        oos, _ = WF.walk_forward(R, _dates(n), 0.40, min_train=10, hold=12,
                                 rng=np.random.default_rng(5), draws=1500)
        assert len(oos) == n - 120

    def test_refits_partition_the_out_of_sample_span(self):
        n = 187                                      # deliberately not a multiple
        R = np.random.default_rng(6).normal(0.004, 0.02, (n, 3))
        oos, folds = WF.walk_forward(R, _dates(n), 0.40, min_train=10, hold=12,
                                     rng=np.random.default_rng(7), draws=1500)
        assert sum(f["n_test"] for f in folds) == len(oos) == n - 120


class TestInfeasibleHandling:
    def test_no_feasible_book_holds_cash_rather_than_guessing(self):
        # A ceiling nothing can satisfy: the fold must be recorded infeasible
        # and contribute zeros, not a book chosen by relaxing the constraint.
        n = 200
        R = np.random.default_rng(8).normal(0.01, 0.25, (n, 3))
        oos, folds = WF.walk_forward(R, _dates(n), 0.01, min_train=10, hold=12,
                                     rng=np.random.default_rng(9), draws=800)
        assert any(not f["feasible"] for f in folds)
        infeasible_months = sum(f["n_test"] for f in folds if not f["feasible"])
        assert np.count_nonzero(oos == 0.0) >= infeasible_months


class TestSummary:
    def test_constant_series_summarises_to_its_own_rate(self):
        st = WF.summarise(np.full(240, 0.01))
        assert st["cagr"] == pytest.approx((1.01 ** 12 - 1) * 100)
        assert st["maxdd"] == pytest.approx(0.0)

    def test_short_series_returns_nothing_rather_than_a_wrong_number(self):
        assert WF.summarise(np.full(6, 0.01)) == {}
