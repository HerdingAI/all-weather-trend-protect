"""
validate_dfus_series.py -- gate the user-supplied DFUS series before use.

Same discipline gold got. Four tests, and the series is unusable if any fail.

TEST 1  internal consistency: PV's own $10,000 balance path must reproduce the
        return column. Catches transcription errors.
TEST 2  distribution: PV computed summary stats independently of the monthly
        table it printed. Recomputing them from the table is a real check.
TEST 3  identity: does this series actually behave like a US total-market fund?
        Graded against VTI on the panel's own tracking bar, not on correlation.
TEST 4  power: measure the tracking error to VTI, and report how long a record
        would have to be to resolve a 60bps edge AT THAT MEASURED TE.

TEST 4 is the point of the exercise. The open-questions doc assumed a TE range;
this replaces the assumption with a measurement.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DFUS_CSV = os.path.join(HERE, "data", "dfus_monthly_returns.csv")
TICKER_CSV = os.path.join(HERE, "output", "monthly_returns_by_ticker.csv")

# PV's stated summary for the series, from the same page as the monthly table.
PV_STATS = dict(mean=1.11, std=4.55, minimum=-9.12, maximum=10.38,
                pct_positive=62.30, skew=-0.244, excess_kurtosis=-0.406)
PV_PCTILES = {1: -9.07, 5: -5.92, 25: -1.95, 50: 1.75, 75: 4.08,
              95: 8.45, 99: 9.73}

# DFUS converted from mutual fund to ETF mid-June 2021, so 2021-06 is a STUB
# month, not a full one. PV drops it from its summary statistics; reconciling
# all five of PV's moments requires dropping it AND using population (divide
# by n) estimators. Both facts were discovered by failing this file's TEST 2,
# and both matter: compounding a stub as though it were a full month is the
# partial-month defect the daily-archive builder already guards against.
FIRST_FULL_MONTH = "2021-07"

# The claim this series is usually cited for, from the index-rebalancing paper.
EDGE_CLAIM_PP = 0.60

# Tolerances. PV rounds to 2dp, so exact equality is not available.
TOL_BALANCE = 0.02      # % on a reconstructed balance
TOL_STAT = 0.02         # pp on a recomputed summary stat
TOL_MOMENT = 0.02       # on skew / kurtosis


def load_dfus() -> pd.DataFrame:
    df = pd.read_csv(DFUS_CSV, comment="#")
    df["date"] = pd.PeriodIndex(df["date"], freq="M").to_timestamp("M")
    return df.set_index("date").sort_index()


def load_vti() -> pd.Series:
    d = pd.read_csv(TICKER_CSV, parse_dates=["date"])
    s = d[d["ticker"] == "VTI"].set_index("date")["monthly_return"].sort_index()
    if s.empty:
        raise SystemExit("VTI absent from the ticker file; cannot grade DFUS")
    return s


def test_1_balance(df: pd.DataFrame) -> list[str]:
    """PV's compounded balance must reproduce the return column."""
    fails = []
    bal = 10_000.0
    for dt, row in df.iterrows():
        bal *= 1.0 + row["monthly_return"] / 100.0
        if abs(bal - row["balance"]) > max(TOL_BALANCE, abs(row["balance"]) * 2e-4):
            fails.append(f"{dt:%Y-%m}: rebuilt {bal:,.2f} vs stated "
                         f"{row['balance']:,.2f}")
            bal = row["balance"]          # resync so one error is not N errors
    return fails


def population_moments(x: np.ndarray) -> tuple[float, float, float]:
    """Population std, skew, excess kurtosis -- divide by n, no bias
    correction. This is the convention PV reports in."""
    m = x.mean()
    m2 = ((x - m) ** 2).mean()
    m3 = ((x - m) ** 3).mean()
    m4 = ((x - m) ** 4).mean()
    return float(np.sqrt(m2)), float(m3 / m2 ** 1.5), float(m4 / m2 ** 2 - 3)


def test_2_distribution(r: pd.Series) -> list[str]:
    """Recompute PV's summary stats from the monthly table it printed.

    Must be given FULL months only; see FIRST_FULL_MONTH.
    """
    fails = []
    x = r.values
    std, skew, exkurt = population_moments(x)
    got = dict(mean=float(x.mean()), std=std, minimum=float(x.min()),
               maximum=float(x.max()), pct_positive=float((x > 0).mean() * 100),
               skew=skew, excess_kurtosis=exkurt)
    for k, want in PV_STATS.items():
        tol = TOL_MOMENT if k in ("skew", "excess_kurtosis") else TOL_STAT
        if abs(got[k] - want) > tol:
            fails.append(f"{k}: got {got[k]:.4f}, PV says {want:.4f}")

    # Percentiles pin the SHAPE, not just the moments -- a reordering that
    # preserved mean and stdev would still have to match all seven of these.
    for q, want in PV_PCTILES.items():
        got_v = float(np.percentile(r.values, q))
        if abs(got_v - want) > 0.15:
            fails.append(f"p{q}: got {got_v:.4f}, PV says {want:.4f}")
    return fails


def grade(a: pd.Series, b: pd.Series) -> dict:
    """Tracking-error grading, scaled by the AVERAGE volatility of the pair."""
    j = pd.concat([a, b], axis=1).dropna()
    x, y = j.iloc[:, 0], j.iloc[:, 1]
    te = float((x - y).std() * np.sqrt(12) * 100)
    vol = float((x.std() + y.std()) / 2 * np.sqrt(12) * 100)
    return dict(n=len(j), corr=float(x.corr(y)), te=te, vol=vol,
                te_ratio=te / vol if vol > 0 else float("inf"),
                gap_pp=float((x.mean() - y.mean()) * 1200),
                cagr_a=float(((1 + x).prod() ** (12 / len(x)) - 1) * 100),
                cagr_b=float(((1 + y).prod() ** (12 / len(y)) - 1) * 100))


def years_for_t(t: float, te_pp: float, edge_pp: float) -> float:
    """Years of record needed for a t-stat of `t` on `edge_pp`, given TE."""
    return (t * te_pp / edge_pp) ** 2


def main() -> None:
    raw = load_dfus()
    df = raw[raw.index >= pd.Timestamp(FIRST_FULL_MONTH)]
    r = df["monthly_return"]
    print(f"DFUS: {raw.index.min():%Y-%m} .. {raw.index.max():%Y-%m}  "
          f"n={len(raw)} months as supplied")
    print(f"      dropping {len(raw) - len(df)} partial month(s) before "
          f"{FIRST_FULL_MONTH}; {len(df)} full months used\n")

    failed = False

    print("TEST 1  balance path reproduces the return column (all supplied)")
    f1 = test_1_balance(raw)
    print("  PASS" if not f1 else "  FAIL")
    for m in f1[:10]:
        print(f"    {m}")
    failed |= bool(f1)

    print("\nTEST 2  PV summary statistics recompute from the monthly table")
    f2 = test_2_distribution(r)
    print("  PASS" if not f2 else "  FAIL")
    for m in f2:
        print(f"    {m}")
    failed |= bool(f2)

    print("\nTEST 3  behaves like a US total-market fund (graded vs VTI)")
    g = grade(r / 100.0, load_vti())
    print(f"  n={g['n']}  corr={g['corr']:.4f}  TE={g['te']:.2f}%/yr  "
          f"vol={g['vol']:.2f}%/yr  TE/vol={g['te_ratio']:.4f}")
    print(f"  DFUS {g['cagr_a']:.2f}%/yr   VTI {g['cagr_b']:.2f}%/yr   "
          f"gap {g['cagr_a'] - g['cagr_b']:+.2f}pp/yr")
    ok3 = g["corr"] > 0.95 and g["te_ratio"] < 0.25
    print("  PASS" if ok3 else "  FAIL")
    failed |= not ok3

    print("\nTEST 4  power, at the MEASURED tracking error")
    te = g["te"]
    diff = (r / 100.0) - load_vti()
    diff = diff.dropna()
    t_obs = float(diff.mean() / diff.std() * np.sqrt(len(diff)))
    print(f"  observed gap {g['cagr_a'] - g['cagr_b']:+.2f}pp/yr, "
          f"t={t_obs:.2f} on {len(diff)} months "
          f"({len(diff) / 12:.1f} years)")
    print(f"  measured TE to VTI: {te:.2f}%/yr")
    print(f"  to resolve a {EDGE_CLAIM_PP:.2f}pp/yr edge at this TE:")
    for t in (1.96, 2.58):
        yrs = years_for_t(t, te, EDGE_CLAIM_PP)
        print(f"    t={t:.2f} -> {yrs:6.1f} years   "
              f"({yrs / (len(diff) / 12):.0f}x the record we have)")
    print(f"  smallest edge resolvable at t=1.96 on {len(diff) / 12:.1f} years:"
          f" {1.96 * te / np.sqrt(len(diff) / 12):.2f}pp/yr")

    print("\n" + ("REJECTED" if failed else "ACCEPTED"))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
