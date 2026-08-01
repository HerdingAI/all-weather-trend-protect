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
PRICES_EXT_CSV = os.path.join(OUT, "monthly_prices_extended.csv")
COVERAGE_CSV = os.path.join(OUT, "coverage_asset_class_extended.csv")
AC_SUMMARY_CSV = os.path.join(OUT, "asset_class_summary.csv")

REPRO_TOL = 1e-9

# A month is compounded only if the ticker traded on at least this share of the
# archive's trading days that month. Guards interior gaps (delist/relist, halts,
# vendor outages), which the first/last-month edge tests cannot see.
MIN_MONTH_COVERAGE = 0.5


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


def splice_tail(extended: pd.DataFrame, native: pd.DataFrame):
    """Carry TAIL months the extended panel lacks over from the native panel.

    The daily archive ends mid-month (2026-07-17), so its final month is dropped
    as a stub and the extended panel stops one month short of the monthly-native
    one. Losing that month would silently shorten every downstream window (the
    eval TEST end is 2026-07-31).

    Measured over 497 overlapping months the two constructions agree to <=0.9
    bps/month (corr >= 0.9998), so the seam is immaterial -- but only the TAIL is
    spliced, never earlier history, so the panel does not quietly mix
    constructions across its span.
    """
    if extended.empty:
        # An empty index has max() == NaT, and every `d > NaT` is False, so the
        # tail came back empty and the whole native panel was silently thrown
        # away -- writing a 0-row aggregate with no error.
        raise ValueError(
            "splice_tail: the extended panel is empty; refusing to splice "
            "(this would silently discard the entire panel)")
    tail = [d for d in native.index if d > extended.index.max()]
    if not tail:
        return extended, []
    out = pd.concat([extended, native.loc[tail].reindex(columns=extended.columns)])
    return out.sort_index(), list(tail)


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

def _first_bday(period) -> pd.Timestamp:
    """First business day (Mon-Fri) of a monthly Period."""
    return pd.offsets.BMonthBegin().rollforward(period.to_timestamp("s"))


def _last_bday(period) -> pd.Timestamp:
    """Last business day (Mon-Fri) of a monthly Period.

    Compared against the archive edge to decide calendar completeness: using the
    business-day end rather than the calendar end avoids declaring a month
    truncated merely because the 31st fell on a weekend.

    Do NOT reach for `pd.offsets.BDay(0)` here -- it rolls *forward*, which
    pushed the answer into the following month for the 29% of months that end on
    a weekend and silently dropped genuinely complete months. `BMonthEnd()`
    rolls back, which is what this needs.

    Holidays are not modelled, so a market holiday on the final business day
    still reads as truncated. That is deliberately conservative: dropping one
    real month is cheaper than publishing a partial month as a whole one.
    """
    return pd.offsets.BMonthEnd().rollback(period.to_timestamp("M"))


def daily_to_monthly_returns(daily: pd.DataFrame, prices: pd.DataFrame | None = None,
                             complete_only: bool = True) -> pd.DataFrame:
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
        # Two distinct incompleteness cases, both of which would otherwise
        # publish a stub as a full-month return:
        #
        #  (1) ARCHIVE-level. The archive's own edge months may be truncated --
        #      the real daily file ends 2026-07-17. Every ticker trades through
        #      that date, so a per-ticker test alone would call July "complete".
        #      Compare the archive edge against the CALENDAR month instead.
        #  (2) TICKER-level. A ticker that inceptions or dies mid-month has a
        #      partial first/last month even though the archive covers it fully.
        # The ticker's TRUE first month, captured before the truncation filter
        # below can remove earlier months. Using the post-filter value would let
        # a month inherit the first-observation allowance it is not entitled to
        # and silently re-admit a broken return chain.
        true_first_m = d.groupby("ticker")["date"].min().dt.to_period("M").to_dict()

        arch_min, arch_max = d["date"].min(), d["date"].max()
        truncated = set()
        first_m, last_m_arch = arch_min.to_period("M"), arch_max.to_period("M")
        if arch_max < _last_bday(last_m_arch):
            truncated.add(last_m_arch)
        if arch_min > _first_bday(first_m):
            truncated.add(first_m)
        if truncated:
            monthly = monthly[~monthly["month"].isin(truncated)]
            d = d[~d["month"].isin(truncated)]

        span = d.groupby("month")["date"].agg(["min", "max", "nunique"])
        tk_days = d.groupby(["ticker", "month"])["date"].nunique()
        edge = d.groupby("ticker")["date"].agg(["min", "max"])

        # Vectorized rather than a per-row loop: ~129k (ticker, month) pairs each
        # needing several scalar label lookups ran at Python speed and dominated
        # the function (~16s of ~24s). Same three conditions, same result.
        # Map through plain dicts: mapping an Arrow-backed string column with a
        # Period-valued Series raises "Cannot cast PeriodArray to dtype float64",
        # so the dtype of `ticker` would otherwise decide whether this works.
        tk, m = monthly["ticker"], monthly["month"]
        tk_first_m = edge["min"].dt.to_period("M").to_dict()
        tk_last_m = edge["max"].dt.to_period("M").to_dict()
        tk_min, tk_max = edge["min"].to_dict(), edge["max"].to_dict()
        started_mid = ((m == tk.map(tk_first_m))
                       & (tk.map(tk_min) > m.map(span["min"].to_dict())))
        ended_mid = ((m == tk.map(tk_last_m))
                     & (tk.map(tk_max) < m.map(span["max"].to_dict())))
        # (3) INTERIOR sparse month. The edge tests above only look at a ticker's
        # global first/last month, so a mid-history gap -- delist/relist, trading
        # halt, vendor outage -- was compounded from a stub and published as a
        # full-month return.
        pair = list(zip(tk, m))
        tk_days_d = tk_days.to_dict()
        sparse = (pd.Series([tk_days_d.get(k, 0) for k in pair], index=monthly.index)
                  < MIN_MONTH_COVERAGE * m.map(span["nunique"].to_dict()))

        # (4) BROKEN RETURN CHAIN. Coverage is not integrity. The archive stores
        # prices.pct_change(), so a missing PRICE also removes that day's return
        # row -- but the NEXT day's stored return is still measured against the
        # missing close. Compounding the survivors drops the move INTO the gap
        # while keeping the move OUT of it, which is unbounded error at high
        # coverage. Real case: ASA 2026-05 had 19 of 20 days (95%, far above
        # MIN_MONTH_COVERAGE) yet compounded to -4.35% against a true +0.38%,
        # publishing a 2026-05 row wrong by up to 427 bps across 17 sleeves.
        broken = pd.Series(False, index=monthly.index)
        if prices is not None:
            px_obs = (prices.notna().stack()
                        .rename("has_px").reset_index())
            px_obs.columns = ["date", "ticker", "has_px"]
            px_obs = px_obs[px_obs["has_px"]]
            px_obs["month"] = px_obs["date"].dt.to_period("M")
            px_days = px_obs.groupby(["ticker", "month"])["date"].nunique()
            px_days_d = px_days.to_dict()
            n_px = pd.Series([px_days_d.get(k, 0) for k in pair], index=monthly.index)
            n_ret = pd.Series([tk_days_d.get(k, 0) for k in pair], index=monthly.index)
            # One price legitimately has no return: a ticker's very first
            # observation. Anything beyond that is a hole in the chain.
            allowance = (m == tk.map(true_first_m)).astype(int)
            broken = n_px > (n_ret + allowance.values)

        monthly = monthly[~(started_mid | ended_mid | sparse)]
        broken = broken[monthly.index]

        if broken.any():
            # REPAIR rather than drop. The price panel is authoritative and its
            # month-over-month ratio is exactly what the monthly-native panel
            # measures, so recomputing is both correct and consistent -- whereas
            # dropping would lose the month for the whole panel (the archive is
            # missing 2026-05-26 returns for 335 of 336 tickers, so that single
            # date would otherwise delete a real month everywhere).
            mep = month_end_levels(prices)
            ratio = mep.pct_change()
            fixed = pd.Series(
                [ratio.at[mm.to_timestamp("M"), t]
                 if (t in ratio.columns and mm.to_timestamp("M") in ratio.index)
                 else np.nan
                 for t, mm in zip(monthly.loc[broken, "ticker"],
                                  monthly.loc[broken, "month"])],
                index=monthly.index[broken])
            monthly.loc[broken, "r"] = fixed
            n_bad = int(fixed.isna().sum())
            print(f"  repaired {int(broken.sum()):,} (ticker, month) pairs with a "
                  f"broken return chain from month-end prices"
                  + (f"; {n_bad} unrepairable and dropped" if n_bad else ""))
            monthly = monthly[monthly["r"].notna()]

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
    # Sort explicitly: .last() takes the last value in ROW order within a group,
    # not the latest by date, so an unsorted input would silently pick the wrong
    # month-end level.
    px = px.sort_index()
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
    """(max abs difference, note) between two aggregates, or (None, reason).

    Compares WHERE the data is as well as what it is. `a - b` is NaN wherever
    either side is NaN and `np.nanmax` ignores exactly those cells, so a naive
    value comparison reports a perfect match for a rebuild that dropped an
    entire sleeve. That is this script's own failure mode -- the fix works by
    removing constituents, which turns values into NaN -- so the presence mask
    is checked first and an all-NaN overlap is treated as equal, not as
    infinitely different.
    """
    if sorted(a.columns) != sorted(b.columns):
        return None, f"column sets differ (rebuild {len(a.columns)} vs file {len(b.columns)})"
    idx = a.index.intersection(b.index)
    if len(idx) != len(b.index):
        return None, f"index differs (overlap {len(idx)} of {len(b.index)} file months)"

    cols = sorted(a.columns)
    A, B = a.loc[idx, cols], b.loc[idx, cols]

    mask_a, mask_b = A.notna(), B.notna()
    if not mask_a.equals(mask_b):
        n = int((mask_a != mask_b).values.sum())
        lost = [c for c in cols if (mask_b[c] & ~mask_a[c]).any()]
        gained = [c for c in cols if (mask_a[c] & ~mask_b[c]).any()]
        detail = []
        if lost:
            detail.append(f"missing in rebuild: {lost[:4]}")
        if gained:
            detail.append(f"extra in rebuild: {gained[:4]}")
        return None, f"NaN positions differ in {n} cells ({'; '.join(detail)})"

    diff = (A - B).abs().values
    if not np.isfinite(diff).any():
        return 0.0, ""          # both all-NaN in the same places: equal
    return float(np.nanmax(diff)), ""


def describe_delta(rebuild: pd.DataFrame, published: pd.DataFrame) -> list[str]:
    """Per-sleeve summary of how a rebuild differs from the published file.

    Used when --accept-rebuild waives the reproduction gate: the operator is
    asserting that a change is expected, which is not the same as agreeing to
    an unexamined one. A sleeve moving that nobody intended shows up here.
    """
    lines = []
    idx = rebuild.index.intersection(published.index)
    only_new = [c for c in rebuild.columns if c not in published.columns]
    only_old = [c for c in published.columns if c not in rebuild.columns]
    if only_new:
        lines.append(f"sleeves ADDED: {sorted(only_new)}")
    if only_old:
        lines.append(f"sleeves REMOVED: {sorted(only_old)}")
    n_new = len(rebuild.index.difference(published.index))
    n_gone = len(published.index.difference(rebuild.index))
    if n_new or n_gone:
        lines.append(f"months: +{n_new} added, -{n_gone} removed "
                     f"({len(idx)} shared)")
    for c in sorted(set(rebuild.columns) & set(published.columns)):
        a, b = rebuild.loc[idx, c], published.loc[idx, c]
        mask_diff = int((a.notna() != b.notna()).sum())
        d = (a - b).abs().values
        worst = float(np.nanmax(d)) if np.isfinite(d).any() else 0.0
        n = int((pd.Series(d, index=idx) > REPRO_TOL).sum())
        if worst > REPRO_TOL or mask_diff:
            where = pd.Series(d, index=idx).idxmax()
            lines.append(f"{c}: {n} month(s) differ, worst {worst*1e4:.1f} bps "
                         f"at {str(where)[:7]}"
                         + (f", {mask_diff} presence change(s)" if mask_diff else ""))
    if not lines:
        lines.append("no per-sleeve differences over the shared span")
    return lines


def reproduction_gate(native: pd.DataFrame, legacy: pd.DataFrame,
                      extra: dict | None = None,
                      accept_rebuild: bool = False) -> None:
    """Prove the tracked inputs still reproduce the file on disk.

    The file may legitimately be in one of several states, and the gate must
    tell them apart rather than conflating "inputs changed" with "already built":

      pre-fix        old rule, monthly source  -- the state the delta is measured from
      fixed-only     new rule, monthly source  -- idempotent re-run of the fix
      extended       new rule, daily source    -- idempotent re-run of the extension

    Only if the inputs match NONE of these did something change underneath us,
    in which case any reported delta would be uninterpretable -- stop rather
    than guess.
    """
    if not os.path.exists(AC_CSV):
        print("  [gate] no published file to compare against — skipping (first build)")
        return
    published = pd.read_csv(AC_CSV, index_col=0, parse_dates=True)

    candidates = {
        "pre-fix (old rule, monthly source)": legacy,
        "fixed-only (new rule, monthly source)": native,
    }
    candidates.update(extra or {})

    reasons = []
    for label, cand in candidates.items():
        d, why = _max_abs_diff(cand, published)
        if d is not None and d <= REPRO_TOL:
            print(f"  [gate] file on disk matches: {label} (max diff {d:.2e}) OK")
            return
        reasons.append(f"    {label}: {why or f'max diff {d:.3e}'}")

    msg = ("the tracked ticker data reproduces the file on disk under none of the "
           "known constructions.\n" + "\n".join(reasons))
    if accept_rebuild:
        # The builder itself changed (e.g. a corrected compounding rule), so the
        # on-disk file was produced by superseded code and is EXPECTED to differ.
        # The operator asserts that intent -- but "I expect a change" must not
        # mean "show me nothing". Print WHAT changed, per sleeve, so an
        # unintended sleeve moving is visible in the run log instead of being
        # waved through with the intended one.
        print("  [gate] --accept-rebuild: proceeding despite a mismatch\n" + msg)
        best = max(candidates.items(),
                   key=lambda kv: len(kv[1].index.intersection(published.index)))
        print(f"\n  What changed vs the file on disk (closest construction: {best[0]}):")
        for line in describe_delta(best[1], published):
            print(f"    {line}")
        return
    raise SystemExit(
        "REPRODUCTION GATE FAILED: " + msg +
        "\nRefusing to proceed: any reported delta would be uninterpretable."
        "\n\nIf the BUILDER changed on purpose (a corrected rule), re-run with "
        "--accept-rebuild to record the change deliberately."
    )


# The two constructions are measuring the same thing over their shared months,
# so they must agree. Measured agreement is <=0.9 bps/month over 497 overlapping
# months; 10 bps leaves headroom for float noise without hiding a real defect.
OVERLAP_TOL = 10e-4


def overlap_gate(clean: pd.DataFrame, native: pd.DataFrame) -> None:
    """Extended vs monthly-native must agree where they overlap.

    This is the guard whose absence let a 427 bps error reach the published
    panel. In extended mode the reproduction gate only compares the rebuild
    against the file the same code just wrote, which cannot detect a systematic
    construction fault -- the two independent constructions can.
    """
    idx = clean.index.intersection(native.index)
    cols = sorted(set(clean.columns) & set(native.columns))
    if not len(idx) or not cols:
        print("  [gate] overlap: no shared months/sleeves to compare — skipped")
        return
    diff = (clean.loc[idx, cols] - native.loc[idx, cols]).abs()
    worst = float(np.nanmax(diff.values)) if np.isfinite(diff.values).any() else 0.0
    if worst > OVERLAP_TOL:
        where = diff.max(axis=1).idxmax()
        sleeves = diff.loc[where].sort_values(ascending=False).head(5)
        raise SystemExit(
            f"OVERLAP GATE FAILED: extended and monthly-native disagree by "
            f"{worst*1e4:.1f} bps (tolerance {OVERLAP_TOL*1e4:.0f} bps).\n"
            f"  worst month: {str(where)[:10]}\n"
            + "\n".join(f"    {s}: {v*1e4:.1f} bps" for s, v in sleeves.items())
            + "\nThe two constructions measure the same thing; a gap this large "
              "means one of them is wrong. Do not publish."
        )
    print(f"  [gate] extended vs monthly-native agree over {len(idx)} shared "
          f"months (max {worst*1e4:.2f} bps) OK")


EXPECTED_CHANGED = {"US Treasuries", "US Equity", "Volatility"}


def delta_gate(legacy: pd.DataFrame, clean: pd.DataFrame) -> None:
    """Exactly three sleeves may change. A fourth means a bug in the policy."""
    changed = set()
    for c in sorted(set(legacy.columns) | set(clean.columns)):
        if c not in legacy.columns or c not in clean.columns:
            changed.add(c)
            continue
        idx = legacy.index.intersection(clean.index)
        L, C = legacy.loc[idx, c], clean.loc[idx, c]
        # Presence first: a sleeve emptied by the fix differs even though every
        # value-wise difference is NaN and would be skipped by nanmax.
        if not L.notna().equals(C.notna()):
            changed.add(c)
            continue
        d = (L - C).abs().values
        if np.isfinite(d).any() and float(np.nanmax(d)) > REPRO_TOL:
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


def _atomic_to_csv(df: pd.DataFrame, path: str, **kw) -> None:
    """Write via a temp file + os.replace so a crash cannot truncate a published
    dataset. os.replace is atomic within a filesystem, so a reader sees either
    the old file or the new one, never a half-written panel."""
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        df.to_csv(tmp, **kw)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def asset_class_summary(clean: pd.DataFrame) -> pd.DataFrame:
    """Per-sleeve coverage/stat rows for `asset_class_summary.csv`.

    Mirrors the writer in `pull_returns.py` (arithmetic mean x 12, not CAGR --
    kept identical so the two producers stay interchangeable, even though the
    docs elsewhere loosely call it a CAGR).

    Regenerated here because this file is DERIVED from the panel and
    `docs/coverage.md` is a transcription of it. Rebuilding the panel without it
    left a published file advertising the contaminated 2.24% Treasuries sleeve
    and a `Volatility` row the panel no longer had.
    """
    rows = []
    for ac in clean.columns:
        s = clean[ac].dropna()
        if s.empty:
            continue
        rows.append({
            "asset_class": ac,
            "first_month": s.index.min(),
            "last_month": s.index.max(),
            "n_months": len(s),
            "ann_return_pct": (s.mean() * 12) * 100,
            "ann_vol_pct": (s.std() * (12 ** 0.5)) * 100,
            "min_month_pct": s.min() * 100,
            "max_month_pct": s.max() * 100,
        })
    return pd.DataFrame(rows)


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
    ap.add_argument("--accept-rebuild", action="store_true",
                    help="Proceed even if the rebuild differs from the file on "
                         "disk. Use ONLY when the builder itself changed on "
                         "purpose, so the on-disk file came from superseded code.")
    args = ap.parse_args(argv)

    print("=" * 78)
    print("build_aggregates.py — " + ("EXTENDED (fix + history)" if args.extended
                                      else "FIX ONLY (monthly source)"))
    print("=" * 78)

    monthly_wide = load_monthly_ticker_wide()
    print(f"\nMonthly ticker panel: {monthly_wide.shape[1]} tickers, "
          f"{str(monthly_wide.index.min())[:7]} -> {str(monthly_wide.index.max())[:7]}")

    # The two monthly-source aggregates are each needed in three places (gates,
    # the downgrade guard, the removed-sleeve report). Build them once so every
    # consumer compares against the same object and the call sites cannot drift.
    native = equal_weight(monthly_wide, aggregatable_groups(ALL_TICKERS, monthly_wide.columns))
    legacy = equal_weight(monthly_wide,
                          aggregatable_groups(ALL_TICKERS, monthly_wide.columns, legacy=True))

    if args.extended:
        print("\nBuilding from the daily archive ...")
        daily = load_daily_long()
        print(f"  daily rows={len(daily):,}  "
              f"{str(daily['date'].min())[:10]} -> {str(daily['date'].max())[:10]}")
        daily_px = pd.read_parquet(DAILY_PRICES_PQ)
        src_wide = daily_to_monthly_returns(daily, prices=daily_px, complete_only=True)
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

    if args.extended:
        clean, spliced = splice_tail(clean, native)
        if spliced:
            print(f"\n  tail splice: {[str(d)[:7] for d in spliced]} carried over from the "
                  "monthly-native panel (daily archive ends mid-month; the two "
                  "constructions agree to <1 bp/month)")

    # Default mode rebuilds from the monthly source, which cannot reach the
    # pre-1985 history. Running it over an extended panel would silently discard
    # ~140 months, so refuse with an instruction rather than a gate mismatch.
    if not args.extended and os.path.exists(AC_CSV):
        on_disk = pd.read_csv(AC_CSV, index_col=0, parse_dates=True)
        native_start = native.index.min()
        if len(on_disk) and on_disk.index.min() < native_start:
            raise SystemExit(
                f"The panel on disk starts {str(on_disk.index.min())[:7]}, before the "
                f"monthly source can reach ({str(native_start)[:7]}). It is the "
                "EXTENDED build.\nRebuilding in fix-only mode would discard that "
                "history. Re-run with --extended (or --dry-run to inspect)."
            )

    print("\nGates:")
    if args.extended:
        overlap_gate(clean, native)
    # The extended panel is a valid on-disk state too, so offer it as a
    # candidate -- otherwise re-running --extended would read as corruption.
    reproduction_gate(
        native, legacy,
        extra={"extended (new rule, daily source)": clean} if args.extended else None,
        accept_rebuild=args.accept_rebuild,
    )
    if not args.extended:
        delta_gate(legacy, clean)

    print(f"\nClean aggregate: {clean.shape[0]} months x {clean.shape[1]} sleeves")
    for c in clean.columns:
        print(_summarize(c, clean[c]))

    dropped_sleeves = sorted(set(legacy.columns) - set(clean.columns))
    if dropped_sleeves:
        print(f"\nSleeves removed by the fix: {dropped_sleeves}")

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    _atomic_to_csv(clean, AC_CSV)
    print(f"\nWrote {AC_CSV}  shape={clean.shape}")

    # Derived from the panel -- must be rewritten together with it, or it keeps
    # publishing the superseded numbers.
    summary = asset_class_summary(clean)
    _atomic_to_csv(summary, AC_SUMMARY_CSV, index=False)
    print(f"Wrote {AC_SUMMARY_CSV}  rows={len(summary)}")

    if args.extended:
        # NOTE: written to a SEPARATE file, never over monthly_prices.csv.
        # audit_integrity.py re-derives monthly returns from monthly_prices.csv
        # and cross-checks them against the daily panel; overwriting it with a
        # daily-derived sample would make that check compare the daily data
        # against itself, silently voiding the audit that is our control.
        levels = month_end_levels(daily_px)
        levels, _ = restrict_universe(levels, set(ALL_TICKERS))
        _atomic_to_csv(levels, PRICES_EXT_CSV)
        print(f"Wrote {PRICES_EXT_CSV}  shape={levels.shape} "
              f"({str(levels.index.min())[:7]} -> {str(levels.index.max())[:7]}) "
              "[month-end LEVELS, sampled not compounded]")

        # Reindex to the panel actually written, so first/last month and
        # n_months match the file rather than the pre-splice frame.
        cov = coverage_table(src_wide.reindex(clean.index), groups)
        _atomic_to_csv(cov, COVERAGE_CSV, index=False)
        print(f"Wrote {COVERAGE_CSV}  rows={len(cov)}")

    print("\n=== DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
