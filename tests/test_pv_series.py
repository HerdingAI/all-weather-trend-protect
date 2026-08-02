"""Tests for the shared PV series gate, and for DFSVX specifically.

Three PV conventions were each discovered by a failing test rather than known
in advance: population moments, a silently-dropped partial first month, and a
meaningful `-0.00%` sign. All three are pinned here so they are not
rediscovered the hard way on the next supplied series.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import pv_series as PV
import validate_dfsvx_series as D


class TestPositiveMask:
    def test_signed_zero_is_not_positive(self):
        assert not PV.positive_mask(np.array([-0.0]))[0]

    def test_unsigned_zero_is_positive(self):
        assert PV.positive_mask(np.array([0.0]))[0]

    def test_ordinary_values_behave_normally(self):
        got = PV.positive_mask(np.array([1.0, -1.0, 0.01, -0.01]))
        assert list(got) == [True, False, True, False]

    def test_the_dfsvx_series_needs_this_to_reconcile(self):
        # 245 months are strictly positive; PV reports 246 because one of the
        # two zero months is `0.00` and the other `-0.00`.
        r = PV.load_pv_csv(D.DFSVX_CSV)["monthly_return"].values
        assert (r > 0).sum() == 245
        assert PV.positive_mask(r).sum() == 246


class TestBalanceTolerance:
    def _series(self, returns, balances):
        idx = pd.date_range("2000-01-31", periods=len(returns), freq="ME")
        return pd.DataFrame({"monthly_return": returns, "balance": balances},
                            index=idx)

    def test_exact_path_passes(self):
        r = [1.0] * 12
        bal, out = 10_000.0, []
        for x in r:
            bal *= 1.01
            out.append(bal)
        assert PV.check_balance(self._series(r, out)) == []

    def test_a_typo_in_the_last_decimal_is_caught(self):
        # 2.29 -> 2.39 is ~0.1%, far outside the rounding allowance at k=1.
        r = [2.29] * 12
        bal, out = 10_000.0, []
        for x in r:
            bal *= 1.0229
            out.append(bal)
        bad = list(r)
        bad[5] = 2.39
        assert PV.check_balance(self._series(bad, out)) != []

    def test_rounding_drift_over_a_long_series_is_tolerated(self):
        # Perturb every month within its rounding half-width; the path must
        # still reconcile, which a fixed relative tolerance could not do.
        rng = np.random.default_rng(0)
        n = 400
        true_r = rng.normal(1.0, 5.0, n)
        bal, out = 10_000.0, []
        for x in true_r:
            bal *= 1.0 + x / 100.0
            out.append(bal)
        shown = np.round(true_r, 2)
        assert PV.check_balance(self._series(shown, out)) == []


class TestPopulationMoments:
    def test_std_divides_by_n(self):
        std, _, _ = PV.population_moments(np.array([1.0, 2.0, 3.0, 4.0]))
        assert std == pytest.approx(np.sqrt(1.25))

    def test_normal_sample_has_near_zero_excess_kurtosis(self):
        x = np.random.default_rng(0).normal(0, 1, 200_000)
        assert abs(PV.population_moments(x)[2]) < 0.05


class TestGradeIsOrderInvariant:
    def test_te_ratio_does_not_depend_on_argument_order(self):
        rng = np.random.default_rng(3)
        i = pd.date_range("2000-01-31", periods=120, freq="ME")
        a = pd.Series(rng.normal(0.01, 0.05, 120), index=i)
        b = pd.Series(rng.normal(0.01, 0.02, 120), index=i)
        assert PV.grade(a, b)["te_ratio"] == pytest.approx(
            PV.grade(b, a)["te_ratio"])


class TestDfsvxRealSeries:
    def test_every_gate_passes(self):
        D.main()

    def test_covers_the_dot_com_run_up_that_visvx_misses(self):
        r = PV.load_pv_csv(D.DFSVX_CSV)
        assert r.index.min() == pd.Timestamp("1993-03-31")
        assert len(r) == 401

    def test_no_partial_first_month(self):
        # Unlike DFUS, all months reconcile, so nothing may be dropped.
        assert D.FIRST_FULL_MONTH is None
        r = PV.load_pv_csv(D.DFSVX_CSV)["monthly_return"]
        assert PV.check_distribution(r, D.PV_STATS, D.PV_PCTILES) == []
