"""
build_aggregates.py -- offline, corrected asset-class return aggregation.

WHY THIS EXISTS
---------------
`pull_returns.py` built the asset-class aggregates while excluding only
`Sector-*` classes and single stocks. It did NOT exclude tickers whose
pct_change is not a return, even though docs/methodology.md and
docs/nuances_and_caveats.md both stated that yield series were excluded.
The documentation described an exclusion the code never implemented.

The consequence was not noise but inversion. Treasury yields move opposite to
bond prices, so averaging ^TNX/^FVX/^TYX percent changes into `US Treasuries`
produced a series that correlates -0.51 with a clean rebuild and understates
return by 289 bps/yr; 1985-02..1986-05 was pure artifact, since no total-return
Treasury fund exists in the data before VUSTX (1986-06).

This script rebuilds the aggregates OFFLINE from already-tracked outputs, so
the correction is attributable to the fix alone -- re-running `pull_returns.py`
would re-download and change ticker data as a side effect.

It also extends history. The monthly file started 1985-02 only because Yahoo's
*monthly-interval* history for these instruments begins there; the daily
archive reaches much further back, so compounding it recovers ~5 extra years
(1980-01 for the five long sleeves) with no new downloads.

MODES
-----
  (default)     rebuild from monthly_returns_by_ticker.csv        [fix only]
  --extended    rebuild from daily_returns_by_ticker.parquet      [fix + history]

Both write output/monthly_returns_by_asset_class.csv. --extended additionally
regenerates monthly_prices.csv (month-end LEVELS, needed by
risk_parity_seasons.py for the ^TNX inflation-regime signal) and writes a
coverage companion.

Usage:
    .venv/bin/python build_aggregates.py
    .venv/bin/python build_aggregates.py --extended
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

# pull_returns is import-safe as of the __main__ guard; importing it keeps the
# ticker universe and the return-series policy defined in exactly one place.
from pull_returns import (  # noqa: E402
    ALL_TICKERS,
    NON_RETURN_KINDS,
    NON_RETURN_TICKERS,
    is_return_series,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")

TICKER_CSV = os.path.join(OUT, "monthly_returns_by_ticker.csv")
DAILY_RETURNS_PQ = os.path.join(OUT, "daily_returns_by_ticker.parquet")
DAILY_PRICES_PQ = os.path.join(OUT, "daily_prices.parquet")
AC_CSV = os.path.join(OUT, "monthly_returns_by_asset_class.csv")
PRICES_CSV = os.path.join(OUT, "monthly_prices.csv")
COVERAGE_CSV = os.path.join(OUT, "coverage_asset_class_extended.csv")

REPRO_TOL = 1e-9


# --------------------------------------------------------------------------- #
# Grouping
# --------------------------------------------------------------------------- #

def aggregatable_groups(meta: dict, available, legacy: bool = False) -> dict:
    """asset_class -> [tickers] eligible for the equal-weighted return aggregate.

    `legacy=True` reproduces the pre-fix rule (yield/price-only levels included),
    which the reproduction gate needs in order to prove we are starting from the
    same inputs that produced the published file.
    """
    available = set(available)
    groups: dict[str, list[str]] = {}
    for ticker, m in meta.items():
        if ticker not in available:
            continue
        asset_class = m[1]
        if asset_class.startswith("Sector-") or asset_class == "Equity (single stock)":
            continue  # single stocks + sector ETFs are aggregated separately
        if not legacy and not is_return_series(ticker, m):
            continue  # yield/price-only levels are not returns
        groups.setdefault(asset_class, []).append(ticker)
    return groups


def equal_weight(wide: pd.DataFrame, groups: dict) -> pd.DataFrame:
    """Time-varying equal-weighted mean per asset class.

    Uses only the constituents with data in a given month, so coverage expands
    as tickers inception over time. A month with no constituent stays NaN.
    """
    out = pd.DataFrame(index=wide.index)
    for ac, tks in groups.items():
        cols = [t for t in tks if t in wide.columns]
        if not cols:
            continue
        out[ac] = wide[cols].mean(axis=1, skipna=True)
    return out.dropna(how="all").sort_index()


def restrict_universe(wide: pd.DataFrame, reference: set):
    """Drop columns absent from the reference universe.

    The daily archive carries 5 dead funds the monthly universe lacks
    (AUBAX, LOMMX, PADMX, PAGPX, PIGLX -- all 2019-2023). Including them would
    shift sleeve composition mid-sample for reasons unrelated to extending
    history, so the extended panel is restricted to the monthly universe.
    """
    dropped = sorted(c for c in wide.columns if c not in reference)
    kept = wide[[c for c in wide.columns if c in reference]]
    return kept, dropped


# --------------------------------------------------------------------------- #
# Daily -> monthly
# --------------------------------------------------------------------------- #

def daily_to_monthly_returns(daily: pd.DataFrame, complete_only: bool = True) -> pd.DataFrame:
    """Compound daily returns to month-end, one column per ticker.

    `complete_only` drops a ticker's first and last month when the archive does
    not cover the whole month. Without it a stub month (e.g. the archive ending
    2026-07-17) masquerades as a full-month return.
    """
    d = daily.dropna(subset=["daily_return"]).copy()
    d["month"] = d["date"].dt.to_period("M")

    grp = d.groupby(["ticker", "month"])["daily_return"]
    monthly = grp.apply(lambda s: float(np.prod(1.0 + s.values) - 1.0)).rename("r").reset_index()

    if complete_only:
        # A ticker's edge months are complete only if the archive itself has
        # trading days in that month at or before/after the ticker's own edge.
        span = d.groupby("month")["date"].agg(["min", "max"])
        edge = d.groupby("ticker")["date"].agg(["min", "max"])
        first_m = edge["min"].dt.to_period("M")
        last_m = edge["max"].dt.to_period("M")

        keep = []
        for row in monthly.itertuples(index=False):
            tk, m = row.ticker, row.month
            if m == first_m[tk] and edge["min"][tk] > span["min"][m]:
                keep.append(False)          # started mid-month
            elif m == last_m[tk] and edge["max"][tk] < span["max"][m]:
                keep.append(False)          # ended mid-month
            else:
                keep.append(True)
        monthly = monthly[pd.Series(keep, index=monthly.index)]

    wide = monthly.pivot(index="month", columns="ticker", values="r")
    wide.index = wide.index.to_timestamp("M")
    wide.index.name = "Date"
    wide.columns.name = None
    return wide.sort_index()


def month_end_levels(prices: pd.DataFrame) -> pd.DataFrame:
    """Month-end sample (last observation) of a wide daily price/level matrix.

    LEVELS ARE SAMPLED, NEVER COMPOUNDED. ^TNX is a yield level; compounding it
    is exactly the error this script exists to correct. Months with no
    observation are absent rather than forward-filled.
    """
    px = prices.copy()
    px.index = pd.to_datetime(px.index)
    out = px.groupby(px.index.to_period("M")).last()
    out.index = out.index.to_timestamp("M")
    out.index.name = "Date"
    return out.sort_index()


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_monthly_ticker_wide() -> pd.DataFrame:
    d = pd.read_csv(TICKER_CSV, parse_dates=["date"])
    wide = d.pivot_table(index="date", columns="ticker", values="monthly_return", dropna=False)
    wide.index.name = "Date"
    wide.columns.name = None
    return wide.sort_index()


def load_daily_long() -> pd.DataFrame:
    return pd.read_parquet(DAILY_RETURNS_PQ, columns=["date", "ticker", "daily_return"])


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #

def _max_abs_diff(a: pd.DataFrame, b: pd.DataFrame):
    """(max abs difference, note) between two aggregates, or (None, reason)."""
    if sorted(a.columns) != sorted(b.columns):
        return None, f"column sets differ (rebuild {len(a.columns)} vs file {len(b.columns)})"
    idx = a.index.intersection(b.index)
    if len(idx) != len(b.index):
        return None, f"index differs (overlap {len(idx)} of {len(b.index)} file months)"
    cols = sorted(a.columns)
    return float(np.nanmax((a.loc[idx, cols] - b.loc[idx, cols]).abs().values)), ""


def reproduction_gate(wide: pd.DataFrame) -> None:
    """Prove the tracked inputs still reproduce the file on disk.

    Before the fix is applied, the file on disk was produced by the OLD rule, so
    a legacy rebuild must match it -- that is what makes the resulting delta
    attributable to the fix alone. After the fix (or on any re-run) the file was
    produced by the NEW rule, so a clean rebuild matches instead; that is a
    successful idempotent re-run, not a failure.

    Only if NEITHER matches are the inputs not what produced the file, in which
    case any delta would be uninterpretable -- stop rather than guess.
    """
    if not os.path.exists(AC_CSV):
        print("  [gate] no published file to compare against — skipping (first build)")
        return
    published = pd.read_csv(AC_CSV, index_col=0, parse_dates=True)

    legacy = equal_weight(wide, aggregatable_groups(ALL_TICKERS, wide.columns, legacy=True))
    d_legacy, why_legacy = _max_abs_diff(legacy, published)
    if d_legacy is not None and d_legacy <= REPRO_TOL:
        print(f"  [gate] old-rule rebuild reproduces the file on disk "
              f"(max diff {d_legacy:.2e}) — pre-fix state confirmed OK")
        return

    clean = equal_weight(wide, aggregatable_groups(ALL_TICKERS, wide.columns))
    d_clean, why_clean = _max_abs_diff(clean, published)
    if d_clean is not None and d_clean <= REPRO_TOL:
        print(f"  [gate] file on disk already matches the CLEAN rule "
              f"(max diff {d_clean:.2e}) — idempotent re-run OK")
        return

    raise SystemExit(
        "REPRODUCTION GATE FAILED: the tracked ticker data reproduces the file on "
        "disk under neither the old nor the new rule.\n"
        f"  old-rule: {why_legacy or f'max diff {d_legacy:.3e}'}\n"
        f"  new-rule: {why_clean or f'max diff {d_clean:.3e}'}\n"
        "Refusing to proceed: any reported delta would be uninterpretable."
    )


EXPECTED_CHANGED = {"US Treasuries", "US Equity", "Volatility"}


def delta_gate(wide: pd.DataFrame, clean: pd.DataFrame) -> None:
    """Exactly three sleeves may change. A fourth means a bug in the policy."""
    legacy = equal_weight(wide, aggregatable_groups(ALL_TICKERS, wide.columns, legacy=True))
    changed = set()
    for c in sorted(set(legacy.columns) | set(clean.columns)):
        if c not in legacy.columns or c not in clean.columns:
            changed.add(c)
            continue
        idx = legacy.index.intersection(clean.index)
        d = (legacy.loc[idx, c] - clean.loc[idx, c]).abs()
        if float(np.nanmax(d.values)) > REPRO_TOL:
            changed.add(c)
    unexpected = changed - EXPECTED_CHANGED
    if unexpected:
        raise SystemExit(
            f"DELTA GATE FAILED: unexpected sleeves changed: {sorted(unexpected)}. "
            f"Expected only {sorted(EXPECTED_CHANGED)}."
        )
    print(f"  [gate] changed sleeves = {sorted(changed)} OK")


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def _summarize(name: str, s: pd.Series) -> str:
    s = s.dropna()
    if s.empty:
        return f"    {name:26s} EMPTY"
    return (f"    {name:26s} {str(s.index.min())[:7]} -> {str(s.index.max())[:7]}  "
            f"n={len(s):4d}  ann={s.mean()*1200:6.2f}%  vol={s.std()*np.sqrt(12)*100:6.2f}%")


def coverage_table(wide: pd.DataFrame, groups: dict) -> pd.DataFrame:
    rows = []
    for ac, tks in sorted(groups.items()):
        cols = [t for t in tks if t in wide.columns]
        sub = wide[cols]
        n_by_month = sub.notna().sum(axis=1)
        live = n_by_month[n_by_month > 0]
        rows.append({
            "asset_class": ac,
            "first_month": str(live.index.min())[:10] if len(live) else "",
            "last_month": str(live.index.max())[:10] if len(live) else "",
            "n_months": int(len(live)),
            "n_constituents_total": len(cols),
            "n_constituents_first_month": int(live.iloc[0]) if len(live) else 0,
            "n_constituents_last_month": int(live.iloc[-1]) if len(live) else 0,
            "constituents": ",".join(sorted(cols)),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extended", action="store_true",
                    help="Build from the daily archive to extend history before 1985.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute and report, but write nothing.")
    args = ap.parse_args(argv)

    print("=" * 78)
    print("build_aggregates.py — " + ("EXTENDED (fix + history)" if args.extended
                                      else "FIX ONLY (monthly source)"))
    print("=" * 78)

    monthly_wide = load_monthly_ticker_wide()
    print(f"\nMonthly ticker panel: {monthly_wide.shape[1]} tickers, "
          f"{str(monthly_wide.index.min())[:7]} -> {str(monthly_wide.index.max())[:7]}")

    print("\nGates:")
    reproduction_gate(monthly_wide)

    if args.extended:
        print("\nBuilding from the daily archive ...")
        daily = load_daily_long()
        print(f"  daily rows={len(daily):,}  "
              f"{str(daily['date'].min())[:10]} -> {str(daily['date'].max())[:10]}")
        src_wide = daily_to_monthly_returns(daily, complete_only=True)
        src_wide, dropped = restrict_universe(src_wide, set(monthly_wide.columns))
        if dropped:
            print(f"  universe reconciliation: dropped {len(dropped)} daily-only "
                  f"tickers {dropped}")
        print(f"  compounded panel: {src_wide.shape[1]} tickers, "
              f"{str(src_wide.index.min())[:7]} -> {str(src_wide.index.max())[:7]}")
    else:
        src_wide = monthly_wide

    groups = aggregatable_groups(ALL_TICKERS, src_wide.columns)
    clean = equal_weight(src_wide, groups)

    if not args.extended:
        delta_gate(monthly_wide, clean)

    print(f"\nClean aggregate: {clean.shape[0]} months x {clean.shape[1]} sleeves")
    for c in clean.columns:
        print(_summarize(c, clean[c]))

    dropped_sleeves = sorted(
        set(equal_weight(monthly_wide,
                         aggregatable_groups(ALL_TICKERS, monthly_wide.columns,
                                             legacy=True)).columns)
        - set(clean.columns))
    if dropped_sleeves:
        print(f"\nSleeves removed by the fix: {dropped_sleeves}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    clean.to_csv(AC_CSV)
    print(f"\nWrote {AC_CSV}  shape={clean.shape}")

    if args.extended:
        prices = pd.read_parquet(DAILY_PRICES_PQ)
        levels = month_end_levels(prices)
        levels, _ = restrict_universe(levels, set(ALL_TICKERS))
        levels.to_csv(PRICES_CSV)
        print(f"Wrote {PRICES_CSV}  shape={levels.shape} "
              f"({str(levels.index.min())[:7]} -> {str(levels.index.max())[:7]}) "
              "[month-end LEVELS, sampled not compounded]")

        cov = coverage_table(src_wide, groups)
        cov.to_csv(COVERAGE_CSV, index=False)
        print(f"Wrote {COVERAGE_CSV}  rows={len(cov)}")

    print("\n=== DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
