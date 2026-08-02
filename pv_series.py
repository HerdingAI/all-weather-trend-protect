"""
pv_series.py -- shared gate for user-supplied Portfolio Visualizer series.

Every externally-supplied series gets the same treatment gold got: validated
before use, rejected if it fails. Two series now use this (DFUS, DFSVX), and
the conventions below were each discovered by a FAILING test, not assumed.

PV CONVENTIONS, LEARNED THE HARD WAY
------------------------------------
1. PV reports POPULATION moments (divide by n), not bias-corrected ones.
   Testing against pandas' defaults fails on skew and kurtosis.

2. PV silently drops a PARTIAL first month. DFUS converted mutual-fund -> ETF
   mid-June 2021, and its 2021-06 stub only shows up as a reconciliation
   failure. Compounding a stub as a full month is a real defect.

3. PV's `-0.00%` minus sign is MEANINGFUL. It denotes a small negative that
   rounds to two decimals, as distinct from `0.00%`. DFSVX has one of each,
   and honouring the sign bit is what reproduces PV's % positive exactly.
   Do not normalise these to plain 0.0.

The `balance` column is PV's own compounded path. It is a redundant encoding
of the returns -- good for catching transcription errors, NOT an independent
source.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TICKER_CSV = os.path.join(HERE, "output", "monthly_returns_by_ticker.csv")

TOL_BALANCE = 0.02      # % on a reconstructed balance
TOL_STAT = 0.02         # pp on a recomputed summary stat
TOL_MOMENT = 0.02       # on skew / kurtosis


def load_pv_csv(path: str) -> pd.DataFrame:
    """Load a supplied series. Rows may be in any order; result is sorted."""
    df = pd.read_csv(path, comment="#")
    df["date"] = pd.PeriodIndex(df["date"], freq="M").to_timestamp("M")
    return df.set_index("date").sort_index()


def load_ticker(ticker: str) -> pd.Series:
    d = pd.read_csv(TICKER_CSV, parse_dates=["date"])
    s = d[d["ticker"] == ticker].set_index("date")["monthly_return"].sort_index()
    if s.empty:
        raise SystemExit(f"{ticker} absent from the ticker file")
    return s


def population_moments(x: np.ndarray) -> tuple[float, float, float]:
    """Population std, skew, excess kurtosis -- divide by n, no bias
    correction. This is the convention PV reports in."""
    m = x.mean()
    m2 = ((x - m) ** 2).mean()
    m3 = ((x - m) ** 3).mean()
    m4 = ((x - m) ** 4).mean()
    return float(np.sqrt(m2)), float(m3 / m2 ** 1.5), float(m4 / m2 ** 2 - 3)


def positive_mask(x: np.ndarray) -> np.ndarray:
    """PV counts `0.00` as positive and `-0.00` as not. See convention 3."""
    return (x > 0) | ((x == 0) & ~np.signbit(x))


# Returns are published to 2dp, so each month carries a rounding error uniform
# in +/-0.005%, i.e. sd = 0.005/sqrt(3) %. Compounding k months accumulates
# sd*sqrt(k). The tolerance below is 4 sigma of that, which is loose enough to
# absorb rounding over a 400-month series and still tight enough to catch a
# typo in the LAST decimal place of a single return (~0.1%, roughly 9 sigma at
# k=1). A fixed relative tolerance cannot do both.
ROUND_HALFWIDTH_PCT = 0.005
ROUND_SIGMA = ROUND_HALFWIDTH_PCT / np.sqrt(3.0) / 100.0
ROUND_SIGMAS_ALLOWED = 4.0


def check_balance(df: pd.DataFrame, initial: float = 10_000.0) -> list[str]:
    """PV's compounded balance must reproduce the return column.

    Resyncs after a mismatch so one bad row reports as one failure rather
    than cascading through every later month.
    """
    fails = []
    bal = initial
    k = 0                                   # months since the last resync
    for dt, row in df.iterrows():
        bal *= 1.0 + row["monthly_return"] / 100.0
        k += 1
        stated = row["balance"]
        drift = abs(stated) * ROUND_SIGMA * np.sqrt(k) * ROUND_SIGMAS_ALLOWED
        if abs(bal - stated) > max(TOL_BALANCE, drift):
            fails.append(f"{dt:%Y-%m}: rebuilt {bal:,.2f} vs stated "
                         f"{stated:,.2f} (allowed {drift:,.2f} over {k} mo)")
            bal, k = stated, 0
    return fails


def check_distribution(r: pd.Series, pv_stats: dict,
                       pv_pctiles: dict | None = None) -> list[str]:
    """Recompute PV's summary stats from the monthly table it printed.

    Must be given FULL months only.
    """
    fails = []
    x = r.values
    std, skew, exkurt = population_moments(x)
    got = dict(mean=float(x.mean()), std=std, minimum=float(x.min()),
               maximum=float(x.max()),
               pct_positive=float(positive_mask(x).mean() * 100),
               skew=skew, excess_kurtosis=exkurt)
    for k, want in pv_stats.items():
        tol = TOL_MOMENT if k in ("skew", "excess_kurtosis") else TOL_STAT
        if abs(got[k] - want) > tol:
            fails.append(f"{k}: got {got[k]:.4f}, PV says {want:.4f}")
    for q, want in (pv_pctiles or {}).items():
        got_v = float(np.percentile(x, q))
        if abs(got_v - want) > 0.15:
            fails.append(f"p{q}: got {got_v:.4f}, PV says {want:.4f}")
    return fails


def grade(a: pd.Series, b: pd.Series) -> dict:
    """Tracking-error grading, scaled by the AVERAGE volatility of the pair.

    Averaging both volatilities is deliberate: dividing by only one makes the
    result depend on argument order, which was a real bug in audit_study_data.
    """
    j = pd.concat([a, b], axis=1, sort=True).dropna()
    x, y = j.iloc[:, 0], j.iloc[:, 1]
    te = float((x - y).std() * np.sqrt(12) * 100)
    vol = float((x.std() + y.std()) / 2 * np.sqrt(12) * 100)
    return dict(n=len(j), corr=float(x.corr(y)), te=te, vol=vol,
                te_ratio=te / vol if vol > 0 else float("inf"),
                cagr_a=float(((1 + x).prod() ** (12 / len(x)) - 1) * 100),
                cagr_b=float(((1 + y).prod() ** (12 / len(y)) - 1) * 100),
                t=float((x - y).mean() / (x - y).std() * np.sqrt(len(j))))


def years_for_t(t: float, te_pp: float, edge_pp: float) -> float:
    """Years of record needed for a t-stat of `t` on an edge of `edge_pp`."""
    return (t * te_pp / edge_pp) ** 2


def report(name: str, raw: pd.DataFrame, first_full: str | None,
           pv_stats: dict, pv_pctiles: dict, anchor: str,
           corr_min: float = 0.90, te_ratio_max: float = 0.35) -> bool:
    """Run the standard four gates. Returns True if anything failed."""
    df = raw if first_full is None else raw[raw.index >= pd.Timestamp(first_full)]
    r = df["monthly_return"]
    print(f"{name}: {raw.index.min():%Y-%m} .. {raw.index.max():%Y-%m}  "
          f"n={len(raw)} months as supplied")
    if len(df) != len(raw):
        print(f"      dropping {len(raw) - len(df)} partial month(s); "
              f"{len(df)} full months used")
    print()

    failed = False

    print("TEST 1  balance path reproduces the return column")
    f1 = check_balance(raw)
    print("  PASS" if not f1 else "  FAIL")
    for m in f1[:10]:
        print(f"    {m}")
    failed |= bool(f1)

    print("\nTEST 2  PV summary statistics recompute from the monthly table")
    f2 = check_distribution(r, pv_stats, pv_pctiles)
    print("  PASS" if not f2 else "  FAIL")
    for m in f2:
        print(f"    {m}")
    failed |= bool(f2)

    print(f"\nTEST 3  identity: graded against {anchor}")
    g = grade(r / 100.0, load_ticker(anchor))
    print(f"  n={g['n']}  corr={g['corr']:.4f}  TE={g['te']:.2f}%/yr  "
          f"TE/vol={g['te_ratio']:.4f}")
    print(f"  {name} {g['cagr_a']:.2f}%/yr   {anchor} {g['cagr_b']:.2f}%/yr   "
          f"gap {g['cagr_a'] - g['cagr_b']:+.2f}pp/yr  t={g['t']:.2f}")
    ok3 = g["corr"] > corr_min and g["te_ratio"] < te_ratio_max
    print("  PASS" if ok3 else "  FAIL")
    failed |= not ok3

    return failed
