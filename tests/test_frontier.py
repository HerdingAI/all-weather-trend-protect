"""Tests for the exhaustive frontier sweep.

The enumeration has to be complete and the evaluation has to be right, because
the headline claim ("your book is at the 98.9th percentile of everything
constructible") is only as good as those two things.
"""
from __future__ import annotations

import itertools
from math import comb

import numpy as np
import pandas as pd
import pytest

import frontier_sweep as F


class TestCompositions:
    def test_counts_match_stars_and_bars(self):
        for total, parts in ((10, 3), (20, 4), (6, 2)):
            got = len(list(F.compositions(total, parts)))
            assert got == comb(total - 1, parts - 1)

    def test_every_composition_is_positive_and_sums_correctly(self):
        for c in F.compositions(10, 3):
            assert sum(c) == 10
            assert all(x > 0 for x in c)

    def test_no_duplicates(self):
        got = list(map(tuple, F.compositions(12, 3)))
        assert len(got) == len(set(got))


class TestEnumeration:
    def test_total_count_matches_the_closed_form(self, monkeypatch):
        monkeypatch.setattr(F, "GRID", 10)
        monkeypatch.setattr(F, "MAX_SLEEVES", 3)
        n = 5
        W, k = F.enumerate_weights(n)
        expected = sum(comb(n, i) * comb(9, i - 1) for i in range(1, 4))
        assert len(W) == expected == len(k)

    def test_every_row_is_long_only_and_fully_invested(self, monkeypatch):
        monkeypatch.setattr(F, "GRID", 10)
        monkeypatch.setattr(F, "MAX_SLEEVES", 3)
        W, _ = F.enumerate_weights(5)
        assert (W >= 0).all()
        assert np.allclose(W.sum(axis=1), 1.0, atol=1e-6)

    def test_sleeve_count_label_matches_the_nonzeros(self, monkeypatch):
        monkeypatch.setattr(F, "GRID", 10)
        monkeypatch.setattr(F, "MAX_SLEEVES", 3)
        W, k = F.enumerate_weights(5)
        assert np.array_equal((W > 0).sum(axis=1), k)

    def test_single_sleeve_books_are_present(self, monkeypatch):
        monkeypatch.setattr(F, "GRID", 10)
        monkeypatch.setattr(F, "MAX_SLEEVES", 2)
        W, _ = F.enumerate_weights(4)
        pure = W[(W > 0).sum(axis=1) == 1]
        assert len(pure) == 4                      # one per asset


class TestEvaluate:
    def test_single_asset_reproduces_that_asset(self):
        rng = np.random.default_rng(0)
        R = rng.normal(0.01, 0.04, (120, 3)).astype(np.float32)
        W = np.eye(3, dtype=np.float32)
        got = F.evaluate(R, W, cost_bps=0.0)
        for i in range(3):
            w = np.cumprod(1 + R[:, i])
            assert got["cagr"][i] == pytest.approx(
                (w[-1] ** (12 / 120) - 1) * 100, rel=1e-4)

    def test_a_constant_series_has_no_drawdown(self):
        R = np.full((60, 1), 0.01, dtype=np.float32)
        got = F.evaluate(R, np.ones((1, 1), dtype=np.float32), cost_bps=0.0)
        assert got["maxdd"][0] == pytest.approx(0.0, abs=1e-4)

    def test_costs_reduce_return_when_sleeves_diverge(self):
        rng = np.random.default_rng(1)
        R = np.column_stack([rng.normal(0.02, 0.06, 120),
                             rng.normal(-0.01, 0.06, 120)]).astype(np.float32)
        W = np.array([[0.5, 0.5]], dtype=np.float32)
        free = F.evaluate(R, W, cost_bps=0.0)["cagr"][0]
        paid = F.evaluate(R, W, cost_bps=50.0)["cagr"][0]
        assert paid < free

    def test_identical_sleeves_incur_no_turnover_cost(self):
        rng = np.random.default_rng(2)
        c = rng.normal(0.01, 0.04, 120).astype(np.float32)
        R = np.column_stack([c, c])
        W = np.array([[0.5, 0.5]], dtype=np.float32)
        assert F.evaluate(R, W, cost_bps=0.0)["cagr"][0] == pytest.approx(
            F.evaluate(R, W, cost_bps=100.0)["cagr"][0], rel=1e-6)

    def test_known_drawdown_is_recovered(self):
        R = np.array([[0.0], [-0.5], [0.0]], dtype=np.float32)
        got = F.evaluate(R, np.ones((1, 1), dtype=np.float32), cost_bps=0.0)
        assert got["maxdd"][0] == pytest.approx(-50.0, abs=1e-3)

    def test_sortino_uses_mar_zero(self):
        r = np.array([0.10, -0.10] * 60, dtype=np.float32)
        R = r.reshape(-1, 1)
        got = F.evaluate(R, np.ones((1, 1), dtype=np.float32), cost_bps=0.0)
        dsd = np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(12)
        assert got["sortino"][0] == pytest.approx(r.mean() * 12 / dsd, rel=1e-4)


class TestBookVector:
    def test_maps_weights_onto_the_right_columns(self):
        assets = ["A", "B", "C"]
        v = F.book_vector({"A": 0.6, "C": 0.4}, assets)
        assert list(v) == pytest.approx([0.6, 0.0, 0.4])

    def test_returns_none_when_a_sleeve_is_missing(self):
        assert F.book_vector({"A": 1.0}, ["B", "C"]) is None
