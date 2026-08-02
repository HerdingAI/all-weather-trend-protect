"""Tests for the DFUS series gate.

The two things that actually went wrong when this series arrived were a
convention mismatch (population vs sample moments) and a partial first month
being compounded as though it were full. Both are pinned here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import validate_dfus_series as V


class TestPopulationMoments:
    def test_std_divides_by_n_not_n_minus_1(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        std, _, _ = V.population_moments(x)
        assert std == pytest.approx(np.sqrt(1.25))          # not sqrt(5/3)

    def test_symmetric_sample_has_zero_skew(self):
        std, skew, _ = V.population_moments(np.array([-2.0, -1.0, 1.0, 2.0]))
        assert skew == pytest.approx(0.0)

    def test_normal_sample_has_excess_kurtosis_near_zero(self):
        x = np.random.default_rng(0).normal(0, 1, 200_000)
        _, _, exkurt = V.population_moments(x)
        assert abs(exkurt) < 0.05

    def test_differs_from_pandas_sample_estimator(self):
        # The bug: pandas' default is bias-corrected, PV's is not. On 61
        # observations that gap is large enough to fail a 0.02 tolerance.
        x = np.random.default_rng(1).normal(0, 1, 61)
        std, _, _ = V.population_moments(x)
        assert std != pytest.approx(pd.Series(x).std(), abs=1e-6)


class TestRealSeries:
    def test_the_supplied_series_passes_every_gate(self):
        V.main()                                             # exits non-zero on failure

    def test_balance_column_reproduces_the_returns(self):
        assert V.test_1_balance(V.load_dfus()) == []

    def test_pv_stats_need_the_partial_month_dropped(self):
        raw = V.load_dfus()
        full = raw[raw.index >= pd.Timestamp(V.FIRST_FULL_MONTH)]
        assert V.test_2_distribution(full["monthly_return"]) == []
        # ...and including it breaks the reconciliation, which is what told us
        # 2021-06 is a stub month rather than a real one.
        assert V.test_2_distribution(raw["monthly_return"]) != []

    def test_exactly_one_month_is_dropped(self):
        raw = V.load_dfus()
        full = raw[raw.index >= pd.Timestamp(V.FIRST_FULL_MONTH)]
        assert len(raw) - len(full) == 1


class TestPower:
    def test_years_scales_with_the_square_of_tracking_error(self):
        a = V.years_for_t(1.96, 1.0, 0.60)
        b = V.years_for_t(1.96, 2.0, 0.60)
        assert b == pytest.approx(4 * a)

    def test_smaller_edges_need_quadratically_longer_records(self):
        assert V.years_for_t(1.96, 1.0, 0.30) == pytest.approx(
            4 * V.years_for_t(1.96, 1.0, 0.60))

    def test_the_assumed_range_that_closed_q2_was_wrong(self):
        # Q2 was closed on an ASSUMED TE of 0.75-2.0%/yr, which implied 6-44
        # years. The measured TE is 0.67, which implies under 5. This test
        # exists so that arithmetic error is not repeated from memory.
        assert V.years_for_t(1.96, 0.67, 0.60) < 5.0
        assert V.years_for_t(1.96, 0.75, 0.60) > 5.0
