#!/usr/bin/env python3
"""
risk_parity_backtest.py
=======================
Risk-Parity portfolio search across asset-class "sleeves".

Goal
----
The Bridgewater All-Weather portfolio is risk-parity-ish but has a known weak
spot: when *equities AND bonds fall together* (e.g. 2022, Q4'18, parts of 2008,
the 1994 / 2013 / 2021 bond routs) the portfolio suffers because its two big
risk sleeves are long equities + long duration.

This system:
  1. Enumerates ALL combinations of asset-class sleeves (from the pre-built
     `output/monthly_returns_by_asset_class.csv`) that contain at least one
     equity sleeve and one bond sleeve.
  2. For each combination, solves a long-only, no-leverage Equal-Risk-
     Contribution (ERC) risk-parity weight vector (Maillard-Roncalli-Teiletche
     convex formulation via cyclical coordinate descent -- pure NumPy, no scipy).
  3. Walk-forward backtests each combination with monthly rebalance to the
     ERC target weights (refit cadence configurable; default annual for the
     broad search, monthly for the final winner + benchmark).
  4. Scores every combination on a "resilience" composite that rewards ordinary
     risk-adjusted return AND performance during *both-down* months (months
     where the broad equity reference AND the broad bond reference are both
     negative) plus named historical crisis windows.
  5. Ranks combinations, picks the winner, and benchmarks it head-to-head vs
     the classic All-Weather allocation on the same stress episodes.
  6. Writes CSV results + a written Markdown report.

Scope decisions (confirmed w/ user):
  * Combination unit      = asset-class buckets (not individual ETFs).
  * Stress definition     = conditional both-down months + historical windows.
  * Constraints           = long-only, no leverage, ETF-investable, monthly
                            rebalance to ERC target weights.
  * Deliverable           = backtest script + written report (All-Weather as
                            the explicit benchmark to beat on the both-down
                            scenario).

Usage
-----
    .venv/bin/python risk_parity_backtest.py            # full search (default)
    .venv/bin/python risk_parity_backtest.py --help

Outputs go to output/risk_parity/ :
  combinations_results.csv   every searched combo + metrics + rank
  top_portfolios.csv         top-N by resilience score
  winning_portfolio.csv      winner weights + ETF mapping + metrics
  benchmark_allweather.csv   All-Weather metrics
  stress_drilldown.csv       winner vs All-Weather per both-down month + window
  equity_curves.csv          winner & All-Weather monthly cumulative wealth
  report.md                  written report

Research/illustration only. Not investment advice.
"""

from __future__ import annotations

import argparse
import itertools
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = os.path.join(HERE, "output", "monthly_returns_by_asset_class.csv")
OUT_DIR = os.path.join(HERE, "output", "risk_parity")

# Sleeve taxonomy. Built from the 19 asset-class buckets in the data file.
# We curate a *distinct* set of macro sleeves to avoid collinear duplicates:
#   - drop "World Equity"        ( ~= US Equity + International Equity )
#   - drop "Gold/Precious Metals" ( ~= Gold + Silver )
#   - drop "US Bonds" from the SEARCH universe (it is the aggregate of
#     Treasuries+Corp+Muni and would be collinear with its own components);
#     we still use it as part of the bond *reference* for both-down detection.
EQUITY_SLEEVES = ["US Equity", "International Equity", "US REIT", "Preferred Stock"]
BOND_SLEEVES = ["US Treasuries", "US Corporate Bonds", "US Municipal Bonds", "EM Bonds",
                "International Bonds"]
DIVERSIFIER_SLEEVES = ["Gold", "Silver", "Commodities", "Currency"]
CRISIS_SLEEVES = ["Volatility"]          # tail-hedge / crisis-alpha sleeve
DIGITAL_SLEEVES = ["Digital Assets"]     # only in the modern (short-window) pass

SEARCH_SLEEVES_DEFAULT = (EQUITY_SLEEVES + BOND_SLEEVES + DIVERSIFIER_SLEEVES
                          + CRISIS_SLEEVES)

# ETF mapping for the report (investable proxies for each sleeve).
SLEEVE_TO_ETF = {
    "US Equity": "VTI (or SPY)",
    "International Equity": "VXUS (or VEA)",
    "US REIT": "VNQ",
    "Preferred Stock": "PFF",
    "US Treasuries": "IEF / TLT blend",
    "US Corporate Bonds": "LQD",
    "US Municipal Bonds": "MUB",
    "EM Bonds": "EMB",
    "International Bonds": "BNDX",
    "Gold": "GLD",
    "Silver": "SLV",
    "Commodities": "DBC",
    "Currency": "UUP",
    "Volatility": "VXX (high carry cost -- see caveats)",
    "Digital Assets": "BTC / IBIT",
}

# Classic All-Weather (Bridgewater / "Tony Robbins" ETF version) mapped to our
# sleeves. 30% equities, 55% treasuries (long + intermediate), 7.5% gold,
# 7.5% commodities. This is the benchmark we try to beat on the both-down
# scenario.
ALL_WEATHER_WEIGHTS = {
    "US Equity": 0.30,
    "US Treasuries": 0.55,
    "Gold": 0.075,
    "Commodities": 0.075,
}

# Broad references used to define "both-down" months (independent of any one
# portfolio's holdings, so the regime is consistent across all combos).
EQUITY_REFERENCE = ["US Equity", "International Equity", "US REIT", "World Equity"]
BOND_REFERENCE = ["US Bonds", "US Treasuries", "US Corporate Bonds",
                  "US Municipal Bonds", "EM Bonds", "International Bonds"]

# Named historical crisis / stress windows (inclusive, month-end dates).
CRISIS_WINDOWS = {
    "GFC 2008-09": ("2008-08-31", "2009-03-31"),
    "COVID 2020-02": ("2020-01-31", "2020-03-31"),
    "Stocks+Bonds rout 2022": ("2021-12-31", "2022-10-31"),
    "Q4 2018": ("2018-09-30", "2018-12-31"),
    "Taper tantrum 2013": ("2013-04-30", "2013-08-31"),
    "Bond crash 1994": ("1994-01-31", "1994-11-30"),
    "Bond rout 2021": ("2021-01-31", "2021-03-31"),
    "SVB / bank stress 2023": ("2023-02-28", "2023-05-31"),
}

MONTHS_PER_YEAR = 12
RF_MONTHLY = 0.0  # risk-free rate; report assumes rf=0 for Sharpe (documented)


# --------------------------------------------------------------------------- #
# ERC risk-parity solver (pure NumPy, cyclical coordinate descent)
# --------------------------------------------------------------------------- #

def erc_weights(cov: np.ndarray, n_iter: int = 1000, tol: float = 1e-10,
                w_init: np.ndarray | None = None) -> np.ndarray:
    """
    Long-only Equal-Risk-Contribution weights via the Maillard-Roncalli-Teiletche
    (2010) convex formulation:

        minimize  0.5 * w' S w  -  (1/n) * sum_i ln(w_i) ,   w_i > 0

    whose minimizer, once normalised to sum to 1, is the ERC portfolio. Solved
    by cyclical coordinate descent (Griveau-Billion / Richard / Roncalli 2013):

        for coordinate i, with a = S_ii and b = sum_{j!=i} S_ij w_j,
            a w_i^2 + b w_i - 1/n = 0
            w_i = (-b + sqrt(b^2 + 4 a / n)) / (2 a)

    Returns weights summing to 1 (long-only, strictly positive).
    """
    cov = np.asarray(cov, dtype=float)
    n = cov.shape[0]
    if n == 1:
        return np.array([1.0])
    # init: inverse-volatility (a good starting point -> fast convergence)
    vol = np.sqrt(np.diag(cov))
    vol = np.where(vol > 0, vol, 1.0)
    w = (1.0 / vol) if w_init is None else w_init.copy()
    w = w / w.sum()
    inv_n = 1.0 / n
    for _ in range(n_iter):
        w_old = w.copy()
        for i in range(n):
            a = cov[i, i]
            if a <= 0:
                continue
            b = float(cov[i, :] @ w - cov[i, i] * w[i])
            disc = b * b + 4.0 * a * inv_n
            w[i] = (-b + math.sqrt(disc)) / (2.0 * a)
        if np.max(np.abs(w - w_old)) < tol:
            break
    w = w / w.sum()
    return w


def risk_contributions(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Absolute risk contribution of each asset: w_i * (S w)_i."""
    return w * (cov @ w)


# --------------------------------------------------------------------------- #
# Data loading & panel construction
# --------------------------------------------------------------------------- #

def load_monthly_returns() -> pd.DataFrame:
    df = pd.read_csv(DATA_CSV, index_col=0, parse_dates=True)
    df.index = df.index.to_period("M").to_timestamp("M")  # month-end normalize
    return df.sort_index()


def build_panel(ret: pd.DataFrame, sleeves: Sequence[str],
                start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return sub-panel of `sleeves` restricted to [start, end], requiring every
    selected sleeve to have NO missing values inside the window."""
    sub = ret.loc[start:end, list(sleeves)].copy()
    # keep only sleeves complete over the window
    complete = sub.columns[sub.notna().all()].tolist()
    return sub[complete]


def available_sleeves_over_window(ret: pd.DataFrame, sleeves: Sequence[str],
                                  start: pd.Timestamp, end: pd.Timestamp) -> List[str]:
    sub = ret.loc[start:end, list(sleeves)]
    return [s for s in sub.columns if sub[s].notna().all()]


# --------------------------------------------------------------------------- #
# Reference regime: "both-down" months
# --------------------------------------------------------------------------- #

def both_down_mask(ret: pd.DataFrame, start: pd.Timestamp,
                   end: pd.Timestamp) -> pd.Series:
    """Boolean Series (indexed by month) True where the broad equity reference
    AND the broad bond reference are both negative in that month."""
    eq = ret.loc[start:end, [s for s in EQUITY_REFERENCE if s in ret.columns]]
    bd = ret.loc[start:end, [s for s in BOND_REFERENCE if s in ret.columns]]
    eq = eq.dropna(axis=1, how="all").mean(axis=1)
    bd = bd.dropna(axis=1, how="all").mean(axis=1)
    mask = (eq < 0) & (bd < 0)
    return mask.fillna(False)


# --------------------------------------------------------------------------- #
# Walk-forward backtest
# --------------------------------------------------------------------------- #

@dataclass
class BacktestResult:
    monthly_returns: pd.Series
    weights_history: Dict[pd.Timestamp, Dict[str, float]] = field(default_factory=dict)


def _refit_dates(index: pd.DatetimeIndex, cadence: str) -> List[pd.Timestamp]:
    if cadence == "M":
        return list(index)
    # annual: first month-end of each calendar year present in the window
    if cadence == "A":
        out = []
        seen = set()
        for d in index:
            if d.year not in seen:
                seen.add(d.year)
                out.append(d)
        return out
    raise ValueError(f"unknown cadence {cadence}")


def walk_forward_backtest(panel: pd.DataFrame, trailing: int = 36,
                          cadence: str = "A") -> BacktestResult:
    """
    Walk-forward ERC risk-parity backtest with monthly rebalance to target
    weights. Target weights are re-solved on `cadence` ('A' annual or 'M'
    monthly) from a trailing `trailing`-month covariance using ONLY data prior
    to the rebalance date (no lookahead). Between refits the portfolio is
    rebalanced monthly back to the most recent target weights.

    `panel` must be a DataFrame of monthly returns for the combo's sleeves
    over the backtest window (rows = month-end dates).
    """
    sleeves = list(panel.columns)
    idx = panel.index
    R = panel.values
    refits = _refit_dates(idx, cadence)
    # We also need pre-window history for the first trailing covariance. The
    # caller passes `panel` already restricted to the window, so for the first
    # refit we may have < trailing months of pre-refit data. We solve this by
    # accepting whatever is available (min 12) -- documented in the report.
    port_rets = np.full(len(idx), np.nan)
    weights_history: Dict[pd.Timestamp, Dict[str, float]] = {}
    current_w = None
    for pos, d in enumerate(idx):
        if d in refits:
            # trailing window strictly before d
            past = panel.loc[:d].iloc[:-1]            # everything before d
            if len(past) >= 12:
                past_use = past.tail(trailing)
                cov = past_use.cov().values
                # guard: replace any tiny-negative diag from numerical noise
                di = np.diag(cov)
                if np.any(di <= 0):
                    cov = cov.copy()
                    np.fill_diagonal(cov, np.where(di <= 0, 1e-12, di))
                w = erc_weights(cov)
            else:
                # not enough history -> start equal-weight until enough data
                w = np.ones(len(sleeves)) / len(sleeves)
            current_w = w
            weights_history[d] = dict(zip(sleeves, w))
        if current_w is None:
            continue
        port_rets[pos] = float(current_w @ R[pos])
    s = pd.Series(port_rets, index=idx, name="port")
    return BacktestResult(monthly_returns=s, weights_history=weights_history)


# --------------------------------------------------------------------------- #
# Performance metrics
# --------------------------------------------------------------------------- #

def _max_drawdown(wealth: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
    running = wealth.cummax()
    dd = wealth / running - 1.0
    if dd.empty or dd.min() >= 0:
        return 0.0, wealth.index[0], wealth.index[0]
    trough = dd.idxmin()
    peak = wealth.loc[:trough].idxmax()
    return float(dd.min()), peak, trough


def compute_metrics(monthly: pd.Series, both_down: pd.Series,
                    crisis_windows: Dict[str, Tuple[str, str]],
                    rf_monthly: float = RF_MONTHLY) -> Dict[str, float]:
    m = monthly.dropna()
    if len(m) == 0:
        return {}
    wealth = (1.0 + m).cumprod()
    ann_ret = float(m.mean() * MONTHS_PER_YEAR)
    ann_vol = float(m.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR))
    sharpe = float((m.mean() - rf_monthly) / m.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR)) if m.std(ddof=1) > 0 else 0.0
    downside = m[m < 0]
    sortino = float((m.mean() - rf_monthly) / downside.std(ddof=1) * math.sqrt(MONTHS_PER_YEAR)) if len(downside) > 1 and downside.std(ddof=1) > 0 else 0.0
    maxdd, peak, trough = _max_drawdown(wealth)
    # ulcer index = sqrt(mean(dd^2))
    running = wealth.cummax()
    dd_series = wealth / running - 1.0
    ulcer = float(np.sqrt((dd_series ** 2).mean())) if len(dd_series) else 0.0
    calmar = ann_ret / abs(maxdd) if maxdd < 0 else float("inf")

    # both-down stats
    bd = m.reindex(both_down.index).loc[both_down]
    bd = bd.dropna()
    n_both_down = int(len(bd))
    bd_avg = float(bd.mean()) if n_both_down else 0.0
    bd_worst = float(bd.min()) if n_both_down else 0.0
    bd_hit_rate = float((bd > 0).mean()) if n_both_down else 0.0
    # portfolio drawdown *during* both-down months (worst point reached within
    # the subset of the wealth curve at both-down months)
    if n_both_down:
        bd_wealth = (1.0 + m.reindex(both_down.index).loc[both_down].fillna(0.0)).cumprod()
        bd_maxdd = _max_drawdown(bd_wealth)[0]
    else:
        bd_maxdd = 0.0

    # crisis windows
    crisis_stats = {}
    crisis_rets = []
    for name, (s, e) in crisis_windows.items():
        seg = m.loc[pd.Timestamp(s):pd.Timestamp(e)]
        if len(seg) == 0:
            continue
        seg_wealth = (1.0 + seg).cumprod()
        seg_ret = float(seg_wealth.iloc[-1] - 1.0)
        seg_maxdd = _max_drawdown(seg_wealth)[0]
        crisis_stats[f"crisis_{name}_ret"] = seg_ret
        crisis_stats[f"crisis_{name}_maxdd"] = seg_maxdd
        crisis_rets.append(seg_ret)
    crisis_avg = float(np.mean(crisis_rets)) if crisis_rets else 0.0

    return {
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": maxdd,
        "ulcer": ulcer,
        "calmar": calmar,
        "n_both_down": n_both_down,
        "both_down_avg_monthly": bd_avg,
        "both_down_annualized": bd_avg * MONTHS_PER_YEAR,
        "both_down_worst_monthly": bd_worst,
        "both_down_hit_rate": bd_hit_rate,
        "both_down_maxdd": bd_maxdd,
        "crisis_avg_ret": crisis_avg,
        **crisis_stats,
    }


# --------------------------------------------------------------------------- #
# Combinatorial search
# --------------------------------------------------------------------------- #

def enumerate_combos(sleeves_avail: List[str], equity_avail: List[str],
                     bonds_avail: List[str], min_size: int, max_size: int
                     ) -> List[Tuple[str, ...]]:
    other = [s for s in sleeves_avail if s not in equity_avail and s not in bonds_avail]
    combos = []
    eq_nonempty = list(itertools.chain.from_iterable(
        itertools.combinations(equity_avail, r) for r in range(1, len(equity_avail) + 1)))
    bd_nonempty = list(itertools.chain.from_iterable(
        itertools.combinations(bonds_avail, r) for r in range(1, len(bonds_avail) + 1)))
    other_any = list(itertools.chain.from_iterable(
        itertools.combinations(other, r) for r in range(0, len(other) + 1)))
    for e in eq_nonempty:
        for b in bd_nonempty:
            for o in other_any:
                combo = tuple(dict.fromkeys(e + b + o))  # dedupe, keep order
                if min_size <= len(combo) <= max_size:
                    combos.append(combo)
    # dedupe (in case of overlap between groups)
    seen = set()
    uniq = []
    for c in combos:
        key = frozenset(c)
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def resilience_score(df: pd.DataFrame) -> pd.Series:
    """Percentile-composite resilience score in [0,100].

    40% Sharpe, 40% annualised both-down avg return, 20% -max_drawdown.
    Using percentile ranks makes the three components comparable & robust.
    """
    s_sharpe = df["sharpe"].rank(pct=True)
    s_bd = df["both_down_annualized"].rank(pct=True)
    s_dd = (-df["max_drawdown"]).rank(pct=True)
    score = 100.0 * (0.40 * s_sharpe + 0.40 * s_bd + 0.20 * s_dd)
    return score.fillna(0.0)


def run_search(panel_full_window: pd.DataFrame, both_down: pd.Series,
               combos: List[Tuple[str, ...]], cadence: str, trailing: int,
               progress_every: int = 500) -> pd.DataFrame:
    rows = []
    t0 = time.time()
    for i, combo in enumerate(combos):
        sub = panel_full_window[list(combo)]
        bt = walk_forward_backtest(sub, trailing=trailing, cadence=cadence)
        metrics = compute_metrics(bt.monthly_returns, both_down, CRISIS_WINDOWS)
        # average realised weights (over refit dates) for reporting
        if bt.weights_history:
            wh = pd.DataFrame(bt.weights_history).T
            avg_w = wh.mean().to_dict()
        else:
            avg_w = {s: float("nan") for s in combo}
        row = {"combo": ",".join(combo), "n_sleeves": len(combo)}
        row.update({f"w_{s}": avg_w.get(s, float("nan")) for s in combo})
        row.update(metrics)
        rows.append(row)
        if (i + 1) % progress_every == 0 or (i + 1) == len(combos):
            dt = time.time() - t0
            print(f"  [{i+1:>6}/{len(combos)}] {dt:6.1f}s "
                  f"({(i+1)/max(dt,1e-9):.1f} combos/s)", flush=True)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["resilience_score"] = resilience_score(df)
        df["rank"] = df["resilience_score"].rank(ascending=False, method="min").astype(int)
        df = df.sort_values("rank").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------- #
# Reporting helpers
# --------------------------------------------------------------------------- #

def weights_from_row(row: pd.Series, sleeves: Sequence[str]) -> Dict[str, float]:
    return {s: float(row.get(f"w_{s}", float("nan"))) for s in sleeves
            if not pd.isna(row.get(f"w_{s}", float("nan")))}


def fixed_weight_backtest(panel: pd.DataFrame, weights: Dict[str, float],
                          trailing: int = 36, cadence: str = "M") -> BacktestResult:
    """Backtest a FIXED target-weight portfolio (e.g. All-Weather) with monthly
    rebalance back to those static weights. (Static weights -> no ERC solve;
    used for the benchmark and for sanity checks.)"""
    sleeves = [s for s in panel.columns if s in weights]
    w = np.array([weights[s] for s in sleeves])
    w = w / w.sum()
    idx = panel.index
    R = panel[sleeves].values
    port = (R * w).sum(axis=1)
    wh = {idx[0]: dict(zip(sleeves, w))}
    return BacktestResult(monthly_returns=pd.Series(port, index=idx, name="port"),
                          weights_history=wh)


def fmt_pct(x: float, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x*100:.{digits}f}%"


def fmt_num(x: float, digits: int = 3) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x:.{digits}f}"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def run_digital_pass(ret: pd.DataFrame, args, base_aw_metrics: Dict[str,float]) -> None:
    """Second, modern-era search that adds Digital Assets (BTC-style) over a
    shorter window. Writes its own CSVs and appends an addendum to report.md."""
    start = pd.Timestamp("2015-06-30")
    end = pd.Timestamp(args.window_end)
    sleeves = list(SEARCH_SLEEVES_DEFAULT) + list(DIGITAL_SLEEVES)
    if args.include_volatility:
        args.exclude_volatility = False
    if args.exclude_volatility and "Volatility" in sleeves:
        sleeves.remove("Volatility")

    missing = [x for x in sleeves if x not in ret.columns]
    if missing:
        raise SystemExit(
            f"Requested sleeve(s) not in the asset-class panel: {missing}. "
            "The Volatility sleeve was removed because ^VIX is a level, not a "
            "return series (docs/methodology.md \u00a74); drop --include-volatility."
        )
    avail = available_sleeves_over_window(ret, sleeves, start, end)
    eq_avail = [s for s in EQUITY_SLEEVES if s in avail]
    bd_avail = [s for s in BOND_SLEEVES if s in avail]
    print(f"\n-- Digital pass: window {start.date()} -> {end.date()} --")
    print(f"  sleeves available ({len(avail)}): {avail}")
    max_size = args.max_sleeves if args.max_sleeves > 0 else len(avail)
    combos = enumerate_combos(avail, eq_avail, bd_avail, args.min_sleeves, max_size)
    print(f"  combinations: {len(combos)}")
    panel = build_panel(ret, avail, start, end)
    both_down = both_down_mask(ret, start, end)
    results = run_search(panel, both_down, combos, args.refit, args.trailing)
    results.to_csv(os.path.join(args.out_dir, "combinations_results_digital.csv"),
                   index=False)
    results.head(args.top_n).to_csv(
        os.path.join(args.out_dir, "top_portfolios_digital.csv"), index=False)
    if results.empty:
        return
    wrow = results.iloc[0]
    wcombo = wrow["combo"].split(",")
    wweights = weights_from_row(wrow, wcombo)
    wbt = walk_forward_backtest(panel[wcombo], trailing=args.trailing, cadence="M")
    wmet = compute_metrics(wbt.monthly_returns, both_down, CRISIS_WINDOWS)
    aw_sleeves = [s for s in ALL_WEATHER_WEIGHTS if s in panel.columns]
    aw_bt = fixed_weight_backtest(panel[aw_sleeves],
                                  {s: ALL_WEATHER_WEIGHTS[s] for s in aw_sleeves},
                                  cadence="M")
    awmet = compute_metrics(aw_bt.monthly_returns, both_down, CRISIS_WINDOWS)
    pd.DataFrame([{"portfolio": "Winner (digital pass, ERC)", **wmet},
                  {"portfolio": "All-Weather (static, same window)", **awmet}]
                 ).to_csv(os.path.join(args.out_dir,
                                       "benchmark_allweather_digital.csv"),
                          index=False)
    # addendum
    lines = []
    A = lines.append
    A("")
    A("## 8. Addendum — modern-era pass with Digital Assets (`--include-digital`)")
    A("")
    A(f"Window {start.date()} -> {end.date()} (digital assets only available from "
      f"2015-06). {len(results)} combinations backtested with Digital Assets added "
      f"to the sleeve universe.")
    A("")
    A("### Winning portfolio (digital pass)")
    A("")
    A("| Sleeve | Weight | ETF proxy |")
    A("|---|---:|---|")
    for s_, w_ in sorted(wweights.items(), key=lambda kv: -kv[1]):
        A(f"| {s_} | {w_*100:.2f}% | {SLEEVE_TO_ETF.get(s_,'?')} |")
    A("")
    A("| Metric | All-Weather | Winner (digital) |")
    A("|---|---:|---:|")
    for lab, key, f in [("Ann. return","ann_return",fmt_pct),
                        ("Ann. vol","ann_vol",fmt_pct),
                        ("Sharpe","sharpe",fmt_num),
                        ("Max DD","max_drawdown",fmt_pct),
                        ("Both-down ann ret","both_down_annualized",fmt_pct),
                        ("Both-down hit rate","both_down_hit_rate",fmt_pct),
                        ("Crisis avg ret","crisis_avg_ret",fmt_pct)]:
        A(f"| {lab} | {f(awmet.get(key))} | **{f(wmet.get(key))}** |")
    A("")
    A("### Top-10 (digital pass)")
    A("")
    A("| # | Sleeves | n | Sharpe | AnnRet | MaxDD | BothDn ann | Score |")
    A("|---:|---|---:|---:|---:|---:|---:|---:|")
    for _, r in results.head(10).iterrows():
        A(f"| {int(r['rank'])} | {r['combo']} | {int(r['n_sleeves'])} | "
          f"{fmt_num(r['sharpe'])} | {fmt_pct(r['ann_return'])} | "
          f"{fmt_pct(r['max_drawdown'])} | {fmt_pct(r['both_down_annualized'])} | "
          f"{r['resilience_score']:.1f} |")
    A("")
    A("Digital assets are highly volatile and only span one regime (post-2015,")
    A("no 2008/1994-style bond rout in-sample); treat this pass as indicative of")
    A("the *diversification role* of crypto, not a robust out-of-sample allocation.")
    with open(os.path.join(args.out_dir, "report.md"), "a") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  digital-pass winner: {wcombo}")
    print(f"  digital winner Sharpe {wmet['sharpe']:.3f}  "
          f"both_down_ann {wmet['both_down_annualized']*100:.2f}%  "
          f"maxDD {wmet['max_drawdown']*100:.2f}%")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Risk-parity asset-class combination search.")
    ap.add_argument("--window-start", default="2008-01-31",
                    help="Backtest window start (month-end). Default 2008-01-31.")
    ap.add_argument("--window-end", default="2026-07-31",
                    help="Backtest window end (month-end). Default 2026-07-31.")
    ap.add_argument("--refit", choices=["A", "M"], default="A",
                    help="ERC refit cadence for the broad search: A=annual "
                         "(default, fast), M=monthly.")
    ap.add_argument("--trailing", type=int, default=36,
                    help="Trailing months for covariance estimation. Default 36.")
    ap.add_argument("--min-sleeves", type=int, default=2)
    ap.add_argument("--max-sleeves", type=int, default=8,
                    help="Cap on sleeves per combo (keeps portfolios "
                         "interpretable; 0 = no cap). Default 8.")
    ap.add_argument("--exclude-volatility", action="store_true", default=True,
                    help="Drop the Volatility sleeve. DEFAULT TRUE: ^VIX spot is "
                         "non-tradable, so Volatility is excluded unless "
                         "--include-volatility is passed (illustration only).")
    ap.add_argument("--include-volatility", action="store_true",
                    help="Opt IN to the ^VIX spot Volatility sleeve (non-tradable; "
                         "illustrative only). Overrides --exclude-volatility.")
    ap.add_argument("--include-digital", action="store_true",
                    help="Add Digital Assets and run a second modern-era pass "
                         "(shorter window 2015-06 -> end).")
    ap.add_argument("--top-n", type=int, default=25)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    start = pd.Timestamp(args.window_start)
    end = pd.Timestamp(args.window_end)

    print("=" * 70)
    print("RISK-PARITY ASSET-CLASS COMBINATION SEARCH")
    print("=" * 70)
    print(f"Window: {start.date()} -> {end.date()}   refit={args.refit}   "
          f"trailing={args.trailing}m")
    ret = load_monthly_returns()
    print(f"Loaded monthly returns: {ret.shape[0]} months x {ret.shape[1]} sleeves")

    # --- search universe over the window ---
    sleeves = list(SEARCH_SLEEVES_DEFAULT)
    if args.include_volatility:
        args.exclude_volatility = False
    if args.exclude_volatility and "Volatility" in sleeves:
        sleeves.remove("Volatility")
    avail = available_sleeves_over_window(ret, sleeves, start, end)
    eq_avail = [s for s in EQUITY_SLEEVES if s in avail]
    bd_avail = [s for s in BOND_SLEEVES if s in avail]
    print(f"Sleeves available over window ({len(avail)}): {avail}")
    print(f"  equity:  {eq_avail}")
    print(f"  bonds:   {bd_avail}")
    div_avail = [s for s in avail if s not in eq_avail and s not in bd_avail]
    print(f"  diversifiers / hedges: {div_avail}")

    max_size = args.max_sleeves if args.max_sleeves > 0 else len(avail)
    combos = enumerate_combos(avail, eq_avail, bd_avail,
                              args.min_sleeves, max_size)
    print(f"Combinations to backtest: {len(combos)}")

    panel = build_panel(ret, avail, start, end)
    both_down = both_down_mask(ret, start, end)
    n_bd = int(both_down.sum())
    print(f"Both-down months in window: {n_bd} / {len(both_down)} "
          f"({n_bd/len(both_down)*100:.1f}%)")

    print("\n-- Running broad search "
          f"(refit={args.refit}) --")
    results = run_search(panel, both_down, combos, args.refit, args.trailing)
    results.to_csv(os.path.join(args.out_dir, "combinations_results.csv"), index=False)
    print(f"Wrote combinations_results.csv ({len(results)} rows)")

    if results.empty:
        print("No results -- exiting.")
        return 1

    # --- top portfolios ---
    top = results.head(args.top_n).copy()
    top.to_csv(os.path.join(args.out_dir, "top_portfolios.csv"), index=False)

    # --- winner ---
    winner_row = results.iloc[0]
    winner_combo = [s for s in winner_row["combo"].split(",")]
    winner_weights = weights_from_row(winner_row, winner_combo)
    print("\n" + "=" * 70)
    print("WINNER (highest resilience score)")
    print("=" * 70)
    for s, w in sorted(winner_weights.items(), key=lambda kv: -kv[1]):
        print(f"  {s:24s} {w*100:6.2f}%   -> ETF: {SLEEVE_TO_ETF.get(s,'?')}")
    print(f"  Resilience score: {winner_row['resilience_score']:.1f}")
    print(f"  Sharpe {winner_row['sharpe']:.3f}  ann_ret {fmt_pct(winner_row['ann_return'])}  "
          f"maxDD {fmt_pct(winner_row['max_drawdown'])}  "
          f"both_down_ann {fmt_pct(winner_row['both_down_annualized'])}")

    # --- re-run winner & All-Weather at monthly refit for the report ---
    print("\n-- Re-running winner & All-Weather at monthly refit for report --")
    winner_panel = panel[winner_combo]
    winner_bt = walk_forward_backtest(winner_panel, trailing=args.trailing, cadence="M")
    # All-Weather: only sleeves present in our panel
    aw_sleeves = [s for s in ALL_WEATHER_WEIGHTS if s in panel.columns]
    aw_weights = {s: ALL_WEATHER_WEIGHTS[s] for s in aw_sleeves}
    aw_panel = panel[aw_sleeves]
    aw_bt = fixed_weight_backtest(aw_panel, aw_weights, cadence="M")

    win_metrics = compute_metrics(winner_bt.monthly_returns, both_down, CRISIS_WINDOWS)
    aw_metrics = compute_metrics(aw_bt.monthly_returns, both_down, CRISIS_WINDOWS)

    # also: an ERC version of All-Weather's sleeve set, for fairness (same
    # sleeves but risk-parity weighted) -> isolates "allocation scheme" effect
    aw_erc_bt = walk_forward_backtest(aw_panel, trailing=args.trailing, cadence="M")
    aw_erc_metrics = compute_metrics(aw_erc_bt.monthly_returns, both_down, CRISIS_WINDOWS)

    # --- write CSVs ---
    pd.DataFrame([{
        **{f"w_{s}": winner_weights.get(s, float("nan")) for s in winner_combo},
        **win_metrics,
        "resilience_score": float(winner_row["resilience_score"]),
        "combo": winner_row["combo"],
    }]).to_csv(os.path.join(args.out_dir, "winning_portfolio.csv"), index=False)

    pd.DataFrame([
        {"portfolio": "All-Weather (static weights)", **aw_metrics},
        {"portfolio": "All-Weather sleeves (ERC, risk parity)", **aw_erc_metrics},
        {"portfolio": "Winner (ERC risk parity)", **win_metrics},
    ]).to_csv(os.path.join(args.out_dir, "benchmark_allweather.csv"), index=False)

    # stress drilldown: per both-down month + per crisis window, winner vs AW
    drill_rows = []
    bd_months = both_down[both_down].index
    for d in bd_months:
        wr = float(winner_bt.monthly_returns.reindex([d]).iloc[0])
        ar = float(aw_bt.monthly_returns.reindex([d]).iloc[0])
        drill_rows.append({"type": "both_down_month", "period": str(d.date()),
                           "winner_ret": wr, "allweather_ret": ar,
                           "diff": wr - ar})
    for name, (s, e) in CRISIS_WINDOWS.items():
        wseg = winner_bt.monthly_returns.loc[pd.Timestamp(s):pd.Timestamp(e)]
        aseg = aw_bt.monthly_returns.loc[pd.Timestamp(s):pd.Timestamp(e)]
        if len(wseg) == 0 or len(aseg) == 0:
            continue
        wseg_ret = float((1.0 + wseg).cumprod().iloc[-1] - 1.0)
        aseg_ret = float((1.0 + aseg).cumprod().iloc[-1] - 1.0)
        drill_rows.append({"type": "crisis_window", "period": name,
                           "winner_ret": wseg_ret, "allweather_ret": aseg_ret,
                           "diff": wseg_ret - aseg_ret})
    pd.DataFrame(drill_rows).to_csv(
        os.path.join(args.out_dir, "stress_drilldown.csv"), index=False)

    # equity curves
    curves = pd.DataFrame({
        "winner": (1.0 + winner_bt.monthly_returns).cumprod(),
        "all_weather": (1.0 + aw_bt.monthly_returns).cumprod(),
    })
    curves.index.name = "month"
    curves.to_csv(os.path.join(args.out_dir, "equity_curves.csv"))

    # --- ERC correctness self-check on winner's full-window covariance ---
    full_cov = panel[winner_combo].cov().values
    w_check = erc_weights(full_cov)
    rc = risk_contributions(w_check, full_cov)
    rel_rc = rc / rc.sum()
    erc_max_err = float(np.max(np.abs(rel_rc - 1.0 / len(winner_combo))))
    print(f"\nERC self-check: max |relative RC - 1/n| = {erc_max_err:.2e} "
          f"(should be ~0)")

    # --- write report ---
    write_report(args.out_dir, winner_combo, winner_weights, win_metrics,
                 aw_metrics, aw_erc_metrics, both_down, winner_bt, aw_bt,
                 results, erc_max_err, args, avail)
    if args.include_digital:
        run_digital_pass(ret, args, aw_metrics)
    print(f"\nReport written to {os.path.join(args.out_dir, 'report.md')}")
    print("Done.")
    return 0


def write_report(out_dir, winner_combo, winner_weights, win_metrics,
                 aw_metrics, aw_erc_metrics, both_down, winner_bt, aw_bt,
                 results, erc_max_err, args, avail) -> None:
    n_bd = int(both_down.sum())
    bd_months_list = [str(d.date()) for d in both_down[both_down].index]
    lines = []
    L = lines.append
    L("# Risk-Parity Asset-Class Combination Search — Report (IN-SAMPLE / method appendix)")
    L("")
    L("*Research/illustration only. Not investment advice.*")
    L("")
    L("> ⚠️ **This is an IN-SAMPLE composition search and is NOT the headline.** The")
    L("> canonical, out-of-sample, net-of-cost, multiple-comparison-adjusted report is")
    L("> [`output/risk_parity_eval/report_eval.md`](../output/risk_parity_eval/report_eval.md)")
    L("> (generated by `risk_parity_eval.py`). The numbers below are produced on the SAME")
    L("> window they are ranked on and will overstate performance; treat them as a method")
    L("> appendix only. Volatility (^VIX, non-tradable) is excluded by default.")
    L("")
    L("")
    L("## 1. Problem & method")
    L("")
    L("Bridgewater's All-Weather portfolio is risk-parity-ish but has a known weak")
    L("spot: when **equities AND bonds fall together** — 2022, Q4'18, parts of")
    L("2008, the 1994 / 2013 / 2021 bond routs — the portfolio suffers because its")
    L("two big risk sleeves are long equities + long duration. This system searches")
    L("for a long-only, no-leverage, ETF-investable **Equal-Risk-Contribution** risk-")
    L("parity portfolio that is more resilient to that both-down scenario.")
    L("")
    L(f"- **Combination unit:** asset-class buckets (curated distinct sleeves).")
    L(f"- **Backtest window:** {args.window_start} → {args.window_end} "
      f"({len(winner_bt.monthly_returns)} months).")
    L(f"- **Risk parity:** long-only ERC (Maillard-Roncalli-Teiletche), solved by")
    L(f"  cyclical coordinate descent (pure NumPy, no scipy). Monthly rebalance to")
    L(f"  ERC target weights; broad search refit cadence = `{args.refit}`; winner &")
    L(f"  benchmark re-run at monthly refit. Trailing covariance = {args.trailing}m.")
    L(f"- **Stress test:** (a) conditional *both-down* months — months where the")
    L(f"  broad equity reference AND broad bond reference are both negative")
    L(f"  ({n_bd} such months in window: {', '.join(bd_months_list)}); plus (b) named")
    L(f"  historical crisis windows (see §4).")
    L(f"- **Sleeves searched ({len(avail)}):** {', '.join(avail)}.")
    L(f"- **Combinations backtested:** {len(results)} (every subset with ≥1 equity")
    L(f"  and ≥1 bond sleeve, {args.min_sleeves}–{args.max_sleeves} sleeves).")
    L(f"- **Resilience score:** 100 × (0.40·pct(Sharpe) + 0.40·pct(both-down ann.")
    L(f"  return) + 0.20·pct(−max drawdown)). Higher = better.")
    L("")
    L("## 2. Winning portfolio")
    L("")
    L("| Sleeve | Weight | Investable ETF proxy |")
    L("|---|---:|---|")
    for s, w in sorted(winner_weights.items(), key=lambda kv: -kv[1]):
        L(f"| {s} | {w*100:.2f}% | {SLEEVE_TO_ETF.get(s,'?')} |")
    L("")
    L(f"Resilience score: **{results.iloc[0]['resilience_score']:.1f}**  ")
    L(f"ERC self-check max |relative RC − 1/n| = {erc_max_err:.2e} (≈0 ⇒ true equal")
    L(f"risk contribution).")
    L("")
    L("## 3. Winner vs All-Weather — head to head")
    L("")
    L("All-Weather (classic ETF version): "
      + ", ".join(f"{s} {w*100:.0f}%" for s, w in ALL_WEATHER_WEIGHTS.items()) + ".")
    L("")
    L("| Metric | All-Weather (static) | AW sleeves + ERC | **Winner (ERC)** |")
    L("|---|---:|---:|---:|")
    def row(label, key, fmt=fmt_pct):
        L(f"| {label} | {fmt(aw_metrics.get(key))} | {fmt(aw_erc_metrics.get(key))} "
          f"| **{fmt(win_metrics.get(key))}** |")
    row("Ann. return", "ann_return")
    row("Ann. volatility", "ann_vol")
    row("Sharpe (rf=0)", "sharpe", fmt_num)
    row("Sortino", "sortino", fmt_num)
    row("Max drawdown", "max_drawdown")
    row("Ulcer index", "ulcer", fmt_num)
    row("Calmar", "calmar", fmt_num)
    row("Both-down months (count)", "n_both_down", lambda x: f"{int(x)}" if not pd.isna(x) else "n/a")
    row("Both-down avg monthly ret", "both_down_avg_monthly", fmt_pct)
    row("Both-down annualised ret", "both_down_annualized", fmt_pct)
    row("Both-down worst month", "both_down_worst_monthly", fmt_pct)
    row("Both-down hit rate (>0)", "both_down_hit_rate", fmt_pct)
    row("Both-down max drawdown", "both_down_maxdd", fmt_pct)
    row("Crisis windows avg ret", "crisis_avg_ret", fmt_pct)
    L("")
    L("The **AW sleeves + ERC** column isolates the *allocation-scheme* effect: same")
    L("sleeves as All-Weather but risk-parity weighted instead of the static 30/55/")
    L("7.5/7.5. The difference between AW-static and AW-ERC shows how much risk parity")
    L("(vs. capital-weighting) buys you; the difference between AW-ERC and the Winner")
    L("shows how much the *sleeve selection* buys you.")
    L("")
    L("## 4. Stress drill-down")
    L("")
    L("### 4a. Both-down months (winner vs All-Weather, monthly return)")
    L("")
    L("| Month | Winner | All-Weather | Diff |")
    L("|---|---:|---:|---:|")
    bd = both_down[both_down].index
    for d in bd:
        wr = float(winner_bt.monthly_returns.reindex([d]).iloc[0])
        ar = float(aw_bt.monthly_returns.reindex([d]).iloc[0])
        L(f"| {d.date()} | {fmt_pct(wr)} | {fmt_pct(ar)} | {fmt_pct(wr-ar)} |")
    L("")
    L("### 4b. Named crisis windows (cumulative return)")
    L("")
    L("| Window | Winner | All-Weather | Diff |")
    L("|---|---:|---:|---:|")
    for name, (s, e) in CRISIS_WINDOWS.items():
        wseg = winner_bt.monthly_returns.loc[pd.Timestamp(s):pd.Timestamp(e)]
        aseg = aw_bt.monthly_returns.loc[pd.Timestamp(s):pd.Timestamp(e)]
        if len(wseg) == 0 or len(aseg) == 0:
            L(f"| {name} | n/a | n/a | n/a |")
            continue
        wr = float((1.0 + wseg).cumprod().iloc[-1] - 1.0)
        ar = float((1.0 + aseg).cumprod().iloc[-1] - 1.0)
        L(f"| {name} | {fmt_pct(wr)} | {fmt_pct(ar)} | {fmt_pct(wr-ar)} |")
    L("")
    L("## 5. Top-10 by resilience score")
    L("")
    L("| # | Sleeves | n | Sharpe | AnnRet | MaxDD | BothDn ann | Score |")
    L("|---:|---|---:|---:|---:|---:|---:|---:|")
    for _, r in results.head(10).iterrows():
        L(f"| {int(r['rank'])} | {r['combo']} | {int(r['n_sleeves'])} | "
          f"{fmt_num(r['sharpe'])} | {fmt_pct(r['ann_return'])} | "
          f"{fmt_pct(r['max_drawdown'])} | {fmt_pct(r['both_down_annualized'])} | "
          f"{r['resilience_score']:.1f} |")
    L("")
    L("## 6. Caveats & limitations")
    L("")
    L("- **Lookahead / refit:** ERC target weights are re-solved from a trailing")
    L(f"  {args.trailing}-month covariance using only data prior to the rebalance")
    L("  date (no lookahead). The first ~12 months of the window use equal-weight")
    L("  until enough history accumulates.")
    L("- **Volatility sleeve:** represented by ^VIX-based returns in the data. A")
    L("  long-vol position is *not* cheaply buy-and-hold-able (VXX carries a heavy")
    L("  roll cost). Treat any winner that loads on Volatility as illustrative of")
    L("  the *crisis-alpha / tail-hedge* role, not a literal ETF hold. Re-run with")
    L("  `--exclude-volatility` for a strictly buy-and-hold-able universe.")
    L("- **Digital assets** only begin 2015; run `--include-digital` for a modern-")
    L("  era pass that adds BTC-style exposure (shorter window, different regime).")
    L("- **Returns, not total-return accounting for the sleeve aggregates:** the")
    L("  monthly asset-class series are Yahoo-derived; bond sleeves include")
    L("  distributions where Yahoo provides them but see `docs/nuances_and_caveats.md`.")
    L("- **Sharpe uses rf=0** for cross-portfolio comparability; absolute levels are")
    L("  optimistic but rankings are unaffected.")
    L("- **Collinear sleeves removed** from the search universe (World Equity,")
    L("  Gold/Precious Metals, US Bonds aggregate) to keep ERC well-conditioned;")
    L("  they remain in the data file and are used in the stress references.")
    L("- **No leverage, long-only:** fully invested (weights sum to 1). Achieved")
    L("  portfolio volatility is whatever ERC produces; do not expect a fixed vol.")
    L("- **One regime, one window:** resilience is measured in-sample over")
    L(f"  {args.window_start}–{args.window_end}. Out-of-sample stability should be")
    L("  checked with a rolling walk-forward before any real use.")
    L("")
    L("## 7. Reproduce")
    L("")
    L("```bash")
    L(f".venv/bin/python risk_parity_backtest.py          # defaults (this report)")
    L(f".venv/bin/python risk_parity_backtest.py --refit M   # monthly refit (slower)")
    L(f".venv/bin/python risk_parity_backtest.py --exclude-volatility   # no VXX-style")
    L(f".venv/bin/python risk_parity_backtest.py --include-digital      # + crypto pass")
    L("```")
    L("")
    L("Outputs in `output/risk_parity/`: `combinations_results.csv`,")
    L("`top_portfolios.csv`, `winning_portfolio.csv`, `benchmark_allweather.csv`,")
    L("`stress_drilldown.csv`, `equity_curves.csv`, `report.md`.")
    L("")
    with open(os.path.join(out_dir, "report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
