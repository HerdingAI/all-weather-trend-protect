"""Tests for the study panel construction.

Every assertion here exists because a code review found the corresponding
defect in a panel that had already been used to publish results:

  * the splice ran oldest-first and kept only months the accumulating series
    lacked, so the OLD PROXY overwrote the ETF on every overlapping month --
    the panel's "US Total Market" matched VFINX at 0.00 bps/month and VTI at
    34.04, for VTI's entire life;
  * two exposures resolved to the same underlying fund and became byte-identical
    columns, which let the optimiser treat one asset as two independent ones;
  * PM Equity was spliced with splice_allowed=True although its anchor ETF was
    absent from the data, so the equivalence test that authorises splicing was
    never run for it;
  * the seam check compared MEAN RETURN ONLY, so two series with equal means and
    different risk could splice cleanly.

A single "the panel equals its ETF where the ETF exists" assertion would have
caught the first and most damaging one before it propagated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import audit_study_data as A
import build_study_panel as B


IDX = pd.date_range("2000-01-31", periods=60, freq="ME")


def _series(vals, start=0, name="x"):
    return pd.Series(vals, index=IDX[start:start + len(vals)], name=name)


class TestStitchPrecedence:
    """The newer vehicle must win wherever both exist."""

    @staticmethod
    def _pair(seed=7):
        """A proxy and an ETF that track each other closely enough to splice,
        but differ enough per month that precedence is observable."""
        rng = np.random.default_rng(seed)
        base = rng.normal(0.006, 0.03, 60)
        old = _series(base, name="PROXY")
        new = _series(base[30:] + rng.normal(0, 0.002, 30), start=30, name="ETF")
        return old, new

    def test_newer_series_wins_the_overlap(self):
        old, new = self._pair()
        out, _ = B.stitch([("ETF", new), ("PROXY", old)])
        for ts in new.index:
            assert out.loc[ts] == pytest.approx(new.loc[ts]), (
                f"at {ts:%Y-%m} the panel took the proxy, not the ETF")

    def test_older_series_supplies_only_the_earlier_span(self):
        old, new = self._pair()
        out, _ = B.stitch([("ETF", new), ("PROXY", old)])
        assert out.loc[IDX[0]] == pytest.approx(old.loc[IDX[0]])
        assert len(out) == 60

    def test_result_is_sorted_and_has_no_duplicate_months(self):
        old, new = self._pair()
        out, _ = B.stitch([("ETF", new), ("PROXY", old)])
        assert out.index.is_monotonic_increasing
        assert not out.index.duplicated().any()

    def test_single_part_passes_through(self):
        only = _series(np.full(20, 0.03))
        out, used = B.stitch([("ETF", only)])
        assert out.equals(only) and len(used) == 1


class TestSeamCheck:
    """The seam must test risk, not only average return."""

    def test_equal_means_but_different_risk_is_refused(self):
        rng = np.random.default_rng(0)
        base = rng.normal(0.005, 0.01, 60)
        old = _series(base)
        # same mean, four times the volatility -> a different asset
        noisy = base.mean() + (base - base.mean()) * 4.0
        new = _series(noisy[30:], start=30)
        with pytest.raises(SystemExit):
            B.stitch([("ETF", new), ("PROXY", old)])

    def test_matching_series_splices_cleanly(self):
        rng = np.random.default_rng(1)
        base = rng.normal(0.005, 0.02, 60)
        old = _series(base)
        new = _series(base[30:] + rng.normal(0, 0.0005, 30), start=30)
        out, _ = B.stitch([("ETF", new), ("PROXY", old)])
        assert len(out) == 60

    def test_short_overlap_is_refused_rather_than_waved_through(self):
        # Under 24 shared months the seam cannot be measured; splicing anyway
        # would admit an unvalidated join.
        rng = np.random.default_rng(11)
        base = rng.normal(0.006, 0.03, 60)
        old = _series(base)
        new = _series(base[45:], start=45)          # only 15 shared months
        with pytest.raises(SystemExit):
            B.stitch([("ETF", new), ("PROXY", old)])


class TestPanelInvariants:
    """Properties the built panel must satisfy against the real ticker data."""

    @pytest.fixture(scope="class")
    def built(self):
        return B.build()

    def test_every_column_matches_its_etf_where_the_etf_exists(self, built):
        panel, _ = built
        w = B.load_ticker_panel()
        for label, etf, _proxies, _ok in B.EXPOSURES:
            if label not in panel.columns or etf not in w.columns:
                continue
            e = w[etf].dropna()
            ov = panel.index.intersection(e.index)
            if len(ov) < 12:
                continue
            diff = (panel.loc[ov, label] - e.loc[ov]).abs().max()
            assert diff < 1e-12, (
                f"{label} does not follow {etf} on months where {etf} exists "
                f"(max diff {diff:.2e}) -- the proxy is winning the overlap")

    def test_columns_are_pairwise_distinct(self, built):
        panel, _ = built
        cols = list(panel.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                j = pd.concat([panel[a], panel[b]], axis=1).dropna()
                if len(j) < 24:
                    continue
                d = (j.iloc[:, 0] - j.iloc[:, 1]).abs().max()
                assert d > 1e-12, f"{a} and {b} are the same series"

    def test_no_interior_gaps(self, built):
        panel, _ = built
        for c in panel.columns:
            s = panel[c]
            f, l = s.first_valid_index(), s.last_valid_index()
            assert s.loc[f:l].isna().sum() == 0, f"{c} has interior gaps"


class TestSpliceAuthorisation:
    """Splicing is only legitimate where the equivalence test actually ran."""

    def test_every_spliced_exposure_was_graded_pass(self):
        readiness = pd.read_csv("output/study_data_readiness.csv")
        graded = {r["proxy"]: r["verdict"]
                  for _, r in readiness.iterrows() if pd.notna(r.get("proxy"))}
        for label, _etf, proxies, splice_ok in B.EXPOSURES:
            if not splice_ok:
                continue
            for p in proxies:
                assert p in graded, (
                    f"{label} splices {p} but the audit never graded it")
                assert graded[p] == "PASS", (
                    f"{label} splices {p} which the audit graded {graded[p]}")


class TestCompareSymmetry:
    """The equivalence verdict must not depend on argument order."""

    def test_te_ratio_is_symmetric(self):
        rng = np.random.default_rng(2)
        a = pd.Series(rng.normal(0.004, 0.005, 120), index=pd.date_range("2000-01-31", periods=120, freq="ME"))
        b = a + pd.Series(rng.normal(0, 0.004, 120), index=a.index)
        ab, ba = A.compare(a, b), A.compare(b, a)
        assert ab["te_ratio"] == pytest.approx(ba["te_ratio"]), (
            "the same pair scores differently depending on which series is "
            "passed second -- the denominator is one side's volatility")

    def test_verdict_is_symmetric(self):
        rng = np.random.default_rng(3)
        a = pd.Series(rng.normal(0.003, 0.004, 240), index=pd.date_range("2000-01-31", periods=240, freq="ME"))
        b = a + pd.Series(rng.normal(0, 0.0016, 240), index=a.index)
        assert A.grade(A.compare(a, b)) == A.grade(A.compare(b, a))
