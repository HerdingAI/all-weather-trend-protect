#!/usr/bin/env python3
"""
risk_parity_seasons.py  (v3 — Bridgewater four-seasons, walk-forward CV, real returns)
===================================================================================
Re-thought approach after two sharp critiques:

  CRITIQUE 1 — "10y train / 8y test are two different regimes; big time crap."
  FIX: drop the single train/test split. Use WALK-FORWARD CROSS-VALIDATION across
  the FULL multi-regime history (2008-2026: GFC, ZIRP/QE, taper, hiking, COVID,
  2022 stagflation, 2023 bank stress). Expanding-window folds; the OOS equity
  curve is the concatenation of every fold's held-out test period — selection
  never sees the period it trades. Plus REGIME-STRATIFIED (four-seasons) scoring
  so a portfolio is judged on ALL economic seasons, not one window.

  CRITIQUE 2 — "inflation eats this puppy alive."
  FIX: (a) add a dedicated TIPS inflation-linked sleeve + keep gold/silver/
  commodities, so the optimizer CAN defend inflation; (b) score on the FOUR
  ECONOMIC SEASONS (growth x inflation) with the STAGFLATION corner (Growth down
  + Inflation up = the All-Weather weak spot) weighted 2x — this is Bridgewater's
  actual framework; (c) report REAL returns (CPI if provided via --cpi-csv; else a
  harsh gold/commodity-deflated purchasing-power stress) so inflation damage is
  visible, not hidden behind nominal numbers.

Regime signals (from data we have, no external macro feed needed):
  Growth   = sign of US Equity 12-month cumulative return.
  Inflation= sign of 12-month change in the 10y Treasury yield (^TNX) -- a market
             proxy for rising inflation expectations / nominal rates. (Labelled
             "rates/inflation up"; documented limitation: not literal CPI.)

All v2 rigor retained: 20% per-sleeve cap, Ledoit-Wolf shrinkage, 10 bps/side
transaction costs, 5 weighting schemes (EW/InvVol/InvVar/ERC/MinVar), Deflated
Sharpe, block-bootstrap CIs, diversification ratio, vs-reference correlations,
long-only / no leverage / ETF-investable, Volatility (^VIX) excluded.

Research / illustration only. Not investment advice.
"""

from __future__ import annotations

import argparse
import math
import os
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from risk_parity_backtest import (
    load_monthly_returns, ALL_WEATHER_WEIGHTS, SLEEVE_TO_ETF, MONTHS_PER_YEAR,
    EQUITY_SLEEVES, BOND_SLEEVES,
)
from risk_parity_eval import (
    SCHEMES, SCHEME_ORDER, cap_weights, ledoit_wolf_cov,
    precompute_refits, backtest, fixed_weight_backtest_costs,
    block_bootstrap_ci, deflated_sharpe, enumerate_combos, build_panel,
    available_sleeves, both_down_mask, EQUITY_REFERENCE, BOND_REFERENCE,
    fp, fn, _ann_sharpe, _ann_ret,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "output", "risk_parity_seasons")
PRICES_CSV = os.path.join(HERE, "output", "monthly_prices.csv")
PRICES_EXT_CSV = os.path.join(HERE, "output", "monthly_prices_extended.csv")
TICKER_CSV = os.path.join(HERE, "output", "monthly_returns_by_ticker.csv")

# Inflation-hedge sleeves (the All-Weather weak spot defenders)
INFLATION_HEDGES = ["TIPS", "Gold", "Silver", "Commodities"]
DIVERSIFIERS = ["Currency"]
SEARCH_SLEEVES = (EQUITY_SLEEVES + BOND_SLEEVES + INFLATION_HEDGES + DIVERSIFIERS)

SEASONS = {
    ("up", "up"):   "GrowthUp InfUp",     # reflation / inflationary boom
    ("up", "down"): "GrowthUp InfDown",   # goldilocks
    ("down", "up"): "GrowthDown InfUp",   # STAGFLATION (target / AW weak spot)
    ("down", "down"): "GrowthDown InfDown",  # deflation / recession
}
STAG = "GrowthDown InfUp"

# Long-history gold proxy (mutual-fund / futures index total return, pre-GLD)
SLEEVE_ETF_LONG = {
    "Gold/Precious Metals": "VGPMX / gold-futures TR index (pre-GLD proxy)",
    "World Equity": "ACWI / MSCI World TR index",
}

# Presets: modern = rich ETF-era universe (2008+); long1985 = investable-as-of-1985
# sleeves (equities + treasuries + corporates + munis + gold), ~41y of regimes.
PRESETS = {
    "modern": dict(
        window=("2008-01-31", "2026-07-31"),
        sleeves=list(SEARCH_SLEEVES),
        equity=list(EQUITY_SLEEVES), bonds=list(BOND_SLEEVES),
        inh=list(INFLATION_HEDGES), div=list(DIVERSIFIERS),
        min_train=8, test=3, step=3, max_sleeves=8, min_sleeves=5),
    "long1985": dict(
        window=("1985-02-28", "2026-07-31"),
        sleeves=["US Equity", "International Equity", "World Equity",
                 "US Treasuries", "US Corporate Bonds", "US Municipal Bonds",
                 "Gold/Precious Metals"],
        equity=["US Equity", "International Equity", "World Equity"],
        bonds=["US Treasuries", "US Corporate Bonds", "US Municipal Bonds"],
        inh=["Gold/Precious Metals"], div=[],
        min_train=10, test=4, step=4, max_sleeves=7, min_sleeves=5),
    # Both presets below require the EXTENDED asset-class panel
    # (build_aggregates.py --extended), which compounds the daily archive to
    # recover history Yahoo's monthly interval does not reach.
    #
    # long1986 exists because excluding the ^TNX/^FVX/^TYX yield levels moved
    # the US Treasuries sleeve's start from 1985-02 to 1986-06 (its first real
    # total-return fund, VUSTX). Sleeve availability is tested over the whole
    # window, so under long1985 Treasuries drops out of the search entirely.
    # Starting at 1986-06 keeps the full 7-sleeve universe.
    "long1986": dict(
        window=("1986-06-30", "2026-07-31"),
        sleeves=["US Equity", "International Equity", "World Equity",
                 "US Treasuries", "US Corporate Bonds", "US Municipal Bonds",
                 "Gold/Precious Metals"],
        equity=["US Equity", "International Equity", "World Equity"],
        bonds=["US Treasuries", "US Corporate Bonds", "US Municipal Bonds"],
        inh=["Gold/Precious Metals"], div=[],
        min_train=10, test=4, step=4, max_sleeves=7, min_sleeves=5),
    # long1980 trades sleeve breadth for ~5 more years of history -- crucially
    # the Volcker shock and the 1980-82 bond bear, the only high-inflation
    # stress in the record. Only five sleeves reach 1980, so min_sleeves drops
    # to 4 to leave the search something to choose between (6 combos, not 1).
    "long1980": dict(
        window=("1980-02-29", "2026-07-31"),
        sleeves=["US Equity", "World Equity", "US Corporate Bonds",
                 "US Municipal Bonds", "Gold/Precious Metals"],
        equity=["US Equity", "World Equity"],
        bonds=["US Corporate Bonds", "US Municipal Bonds"],
        inh=["Gold/Precious Metals"], div=[],
        min_train=10, test=4, step=4, max_sleeves=5, min_sleeves=4),
}


# --------------------------------------------------------------------------- #
# Augmented data: asset-class returns + a dedicated TIPS sleeve (from TIP ticker)
# --------------------------------------------------------------------------- #

def load_augmented_returns() -> pd.DataFrame:
    ret = load_monthly_returns()
    ret.index = ret.index.to_period("M").to_timestamp("M")
    # build TIPS sleeve from the TIP ETF (long-format per-ticker file)
    mt = pd.read_csv(TICKER_CSV, index_col=0, parse_dates=True)
    mt.index = mt.index.to_period("M").to_timestamp("M")
    wide = mt.pivot_table(index=mt.index, columns="ticker", values="monthly_return").sort_index()
    if "TIP" in wide.columns:
        ret["TIPS"] = wide["TIP"]
    return ret.sort_index()


def load_10y_yield() -> pd.Series:
    # Prefer the extended month-end LEVELS when present: ^TNX in
    # monthly_prices.csv starts 1985-01 (Yahoo's monthly limit), while the daily
    # archive reaches 1962, so the pre-1985 presets would otherwise have no
    # inflation-regime signal over their own window. Levels are month-end
    # SAMPLED, never compounded -- a yield level is not a return.
    path = PRICES_EXT_CSV if os.path.exists(PRICES_EXT_CSV) else PRICES_CSV
    px = pd.read_csv(path, index_col=0, parse_dates=True)
    px.index = px.index.to_period("M").to_timestamp("M")
    tnx = px["^TNX"].dropna().sort_index()
    return tnx


# --------------------------------------------------------------------------- #
# Four-seasons regime labels
# --------------------------------------------------------------------------- #

def regime_labels(ret: pd.DataFrame, tnx: pd.Series) -> pd.DataFrame:
    eq = ret["US Equity"].copy()
    growth_12m = eq.rolling(12).apply(lambda x: float(np.prod(1.0 + x) - 1.0), raw=True)
    growth = np.where(growth_12m > 0, "up", "down")
    inf_12m = tnx.diff(12)
    inf_aligned = inf_12m.reindex(ret.index)
    inflation = np.where(inf_aligned > 0, "up", "down")
    growth = pd.Series(growth, index=ret.index)
    inflation = pd.Series(inflation, index=ret.index)
    season = pd.Series(
        [SEASONS.get((g, i), "Unknown") for g, i in zip(growth, inflation)],
        index=ret.index)
    return pd.DataFrame({"growth": growth, "inflation": inflation, "season": season})


# --------------------------------------------------------------------------- #
# Metrics incl. per-season
# --------------------------------------------------------------------------- #

def _max_dd(wealth: np.ndarray) -> float:
    if len(wealth) == 0:
        return 0.0
    return float((wealth / np.maximum.accumulate(wealth) - 1.0).min())


def _sharpe(m: np.ndarray) -> float:
    if len(m) < 2 or np.std(m, ddof=1) == 0:
        return 0.0
    return float(np.mean(m) / np.std(m, ddof=1) * math.sqrt(12))


def per_season_means(net: np.ndarray, idx: pd.DatetimeIndex,
                     regimes: pd.DataFrame) -> Dict[str, float]:
    s = pd.Series(net, index=idx)
    out = {}
    r = regimes.reindex(idx)
    for name in SEASONS.values():
        mask = (r["season"] == name) & s.notna()
        vals = s[mask]
        out[name] = float(vals.mean()) if len(vals) else float("nan")
    out["Stagflation"] = out[STAG]
    return out


def compute_metrics_seasons(net: np.ndarray, gross: np.ndarray, turnover: np.ndarray,
                            idx: pd.DatetimeIndex, regimes: pd.DataFrame,
                            both_down: pd.Series, eq_ref: pd.Series, bd_ref: pd.Series,
                            div_ratio: float) -> Dict[str, float]:
    s = pd.Series(net, index=idx).dropna()
    if len(s) < 2:
        return {}
    wealth = np.cumprod(1.0 + s.values)
    m = {
        "ann_return_net": float(s.mean() * 12),
        "ann_return_gross": float(pd.Series(gross, index=idx).dropna().mean() * 12),
        "ann_vol": float(s.std(ddof=1) * math.sqrt(12)),
        "sharpe_net": _sharpe(s.values),
        "max_drawdown": _max_dd(wealth),
        "ann_turnover": float(np.mean(turnover) * 12) if len(turnover) else 0.0,
        "div_ratio": div_ratio,
        "corr_eq": float(s.corr(eq_ref.reindex(s.index))) if s.std() > 0 else 0.0,
        "corr_bd": float(s.corr(bd_ref.reindex(s.index))) if s.std() > 0 else 0.0,
    }
    bd_mask = both_down.reindex(s.index).fillna(False)
    bd = s[bd_mask]
    m["n_both_down"] = int(len(bd))
    m["both_down_annualized"] = float(bd.mean() * 12) if len(bd) else 0.0
    m["both_down_hit_rate"] = float((bd > 0).mean()) if len(bd) else 0.0
    # per-season
    psm = per_season_means(net, idx, regimes)
    for k, v in psm.items():
        m[f"season_{k.replace(' ', '_')}"] = v
    # stagflation sharpe (if enough months)
    r = regimes.reindex(idx)
    stag = s[(r["season"] == STAG) & s.notna()]
    m["stag_sharpe"] = _sharpe(stag.values) if len(stag) >= 6 else float("nan")
    m["stag_n"] = int(len(stag))
    return m


# --------------------------------------------------------------------------- #
# Four-seasons resilience score (stagflation weighted 2x)
# --------------------------------------------------------------------------- #

def seasons_score(df: pd.DataFrame) -> pd.Series:
    cols = {
        "GrowthDown_InfUp": "season_GrowthDown_InfUp",     # stagflation (2x)
        "GrowthUp_InfUp": "season_GrowthUp_InfUp",
        "GrowthUp_InfDown": "season_GrowthUp_InfDown",
        "GrowthDown_InfDown": "season_GrowthDown_InfDown",
    }
    pct = {}
    for k, c in cols.items():
        pct[k] = df[c].rank(pct=True) if c in df.columns else pd.Series(0.0, index=df.index)
    s_sharpe = df["sharpe_net"].rank(pct=True) if "sharpe_net" in df.columns else 0.0
    s_div = df["div_ratio"].rank(pct=True) if "div_ratio" in df.columns else 0.0
    score = 100.0 * (0.35 * pct["GrowthDown_InfUp"]        # stagflation 2x-ish
                     + 0.15 * pct["GrowthUp_InfUp"]
                     + 0.15 * pct["GrowthUp_InfDown"]
                     + 0.15 * pct["GrowthDown_InfDown"]
                     + 0.10 * s_sharpe
                     + 0.10 * s_div)
    return score.fillna(0.0)


def _quick_seasons_score(m: Dict[str, float]) -> float:
    def g(k): return m.get(k, 0.0) if not (isinstance(m.get(k), float) and math.isnan(m.get(k, float("nan")))) else 0.0
    return (0.35 * g("season_GrowthDown_InfUp") + 0.15 * g("season_GrowthUp_InfUp")
            + 0.15 * g("season_GrowthUp_InfDown") + 0.15 * g("season_GrowthDown_InfDown")
            + 0.10 * g("sharpe_net") + 0.10 * g("div_ratio"))


# --------------------------------------------------------------------------- #
# Real returns (CPI if provided, else harsh gold-deflated purchasing-power stress)
# --------------------------------------------------------------------------- #

def load_deflator(args, ret: pd.DataFrame) -> pd.Series | None:
    """Return a monthly inflation-rate series to deflate nominal returns, or None."""
    if args.cpi_csv and os.path.exists(args.cpi_csv):
        c = pd.read_csv(args.cpi_csv, index_col=0, parse_dates=True)
        c.index = c.index.to_period("M").to_timestamp("M")
        col = [x for x in c.columns if x.lower() in ("cpi", "cpiaucsl", "value")][0]
        cpi = c[col].sort_index()
        infl = cpi.pct_change()
        print(f"  Using CPI deflator from {args.cpi_csv} ({cpi.index.min().date()}..{cpi.index.max().date()})")
        return infl
    # harsh proxy: gold (GLD) total return as purchasing-power unit
    if "Gold" in ret.columns:
        gold = ret["Gold"]
        print("  No CPI provided (--cpi-csv). Using GOLD as a harsh purchasing-power"
              " deflator (inflation stress), NOT literal CPI real return.")
        return gold
    return None


def real_series(nominal: pd.Series, deflator: pd.Series) -> pd.Series:
    d = deflator.reindex(nominal.index).fillna(0.0)
    return (1.0 + nominal) / (1.0 + d) - 1.0


def cagr(m: pd.Series) -> float:
    m = m.dropna()
    if len(m) < 2:
        return float("nan")
    w = float((1.0 + m).prod())
    y = len(m) / 12.0
    return w ** (1.0 / y) - 1.0 if w > 0 and y > 0 else float("nan")


# --------------------------------------------------------------------------- #
# Fast search (seasons-flavoured) reusing the v2 engine
# --------------------------------------------------------------------------- #

def fast_search_seasons(panel: pd.DataFrame, ret_full: pd.DataFrame,
                        regimes: pd.DataFrame, both_down: pd.Series,
                        eq_ref: pd.Series, bd_ref: pd.Series,
                        combos: List[Tuple[str, ...]], schemes: Sequence[str],
                        cap: float, cost_bps: float, shrink: str, trailing: int,
                        label: str = "", progress_every: int = 5000) -> pd.DataFrame:
    sleeves_all = list(panel.columns)
    pos = {s: i for i, s in enumerate(sleeves_all)}
    precomp = precompute_refits(ret_full, sleeves_all, panel.index, trailing, shrink)
    rows = []
    t0 = time.time()
    n_total = len(combos) * len(schemes)
    done = 0
    for combo in combos:
        idxs = [pos[s] for s in combo]
        for sch in schemes:
            bt = backtest(panel, precomp, idxs, sch, cap, cost_bps)
            m = compute_metrics_seasons(bt["net"], bt["gross"], bt["turnover"],
                                        panel.index, regimes, both_down, eq_ref, bd_ref,
                                        bt["div_ratio"])
            row = {"combo": ",".join(combo), "scheme": sch, "n_sleeves": len(combo)}
            if bt["last_w"] is not None:
                row.update({f"w_{s}": float(bt["last_w"][i]) for i, s in enumerate(combo)})
            row.update(m)
            rows.append(row)
            done += 1
            if done % progress_every == 0 or done == n_total:
                dt = time.time() - t0
                print(f"  [{label} {done:>7}/{n_total}] {dt:6.1f}s "
                      f"({done/max(dt,1e-9):.1f}/s)", flush=True)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["resilience_score"] = seasons_score(df)
        df["rank"] = df["resilience_score"].rank(ascending=False, method="min").astype(int)
        df = df.sort_values("rank").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------- #
# Walk-forward CV folds
# --------------------------------------------------------------------------- #

def make_folds(window_idx: pd.DatetimeIndex, min_train_years: int,
               test_years: int, step_years: int) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    folds = []
    start = window_idx[0]
    end = window_idx[-1]
    train_end = start + pd.DateOffset(years=min_train_years) - pd.DateOffset(months=1)
    while True:
        test_start = train_end + pd.DateOffset(months=1)
        test_end = test_start + pd.DateOffset(years=test_years) - pd.DateOffset(months=1)
        if test_start > end:
            break
        if test_end > end:
            test_end = end
        tr = window_idx[(window_idx >= start) & (window_idx <= train_end)]
        te = window_idx[(window_idx >= test_start) & (window_idx <= test_end)]
        if len(tr) >= 24 and len(te) >= 6:
            folds.append((tr, te))
        if test_end >= end:
            break
        train_end = train_end + pd.DateOffset(years=step_years)
    return folds


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Four-seasons walk-forward risk-parity (v3).")
    ap.add_argument("--window-start", default="2008-01-31")
    ap.add_argument("--window-end", default="2026-07-31")
    ap.add_argument("--min-train-years", type=int, default=8)
    ap.add_argument("--test-years", type=int, default=3)
    ap.add_argument("--step-years", type=int, default=3)
    ap.add_argument("--trailing", type=int, default=36)
    ap.add_argument("--min-sleeves", type=int, default=5)
    ap.add_argument("--max-sleeves", type=int, default=8)
    ap.add_argument("--schemes", default=",".join(SCHEME_ORDER))
    ap.add_argument("--cap", type=float, default=0.20)
    ap.add_argument("--shrink", choices=["lw", "none"], default="lw")
    ap.add_argument("--cost-bps", type=float, default=10.0)
    ap.add_argument("--cpi-csv", default="", help="Monthly CPI CSV (date,cpi) for true real returns.")
    ap.add_argument("--bootstrap", type=int, default=3000)
    ap.add_argument("--preset", choices=list(PRESETS.keys()), default="modern",
                    help="modern=2008+ 13-sleeve ETF universe; long1985=1985+ "
                         "investable-as-of-1985 sleeves (~41y).")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    P = PRESETS[args.preset]
    args.window_start = P["window"][0]
    args.window_end = P["window"][1]
    args.min_train_years = P["min_train"]
    args.test_years = P["test"]
    args.step_years = P["step"]
    args.max_sleeves = P["max_sleeves"]
    args.min_sleeves = P["min_sleeves"]
    w_s, w_e = pd.Timestamp(args.window_start), pd.Timestamp(args.window_end)
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip() in SCHEMES]
    cost = args.cost_bps / 10000.0

    print("=" * 76)
    print(f"FOUR-SEASONS WALK-FORWARD RISK PARITY (v3)  preset={args.preset}")
    print("=" * 76)
    print(f"Window {w_s.date()} -> {w_e.date()} "
          f"({(w_e-w_s).days/365.25:.1f}y)  cap={args.cap}  shrink={args.shrink}  "
          f"cost={args.cost_bps}bps  schemes={schemes}")
    print("Volatility (^VIX) excluded; stagflation weighted 2x." +
          ("  [long1985: Gold via VGPMX/gold-futures TR proxy]" if args.preset=="long1985" else "  TIPS sleeve added."))

    ret = load_augmented_returns()
    tnx = load_10y_yield()
    regimes = regime_labels(ret, tnx)
    deflator = load_deflator(args, ret)

    sleeves = [s for s in P["sleeves"] if s in ret.columns]
    avail = available_sleeves(ret, sleeves, w_s, w_e)
    eq = [s for s in P["equity"] if s in avail]
    bd = [s for s in P["bonds"] if s in avail]
    inh = [s for s in P["inh"] if s in avail]
    print(f"Sleeves over window ({len(avail)}): {avail}")
    print(f"  equity: {eq}  bonds: {bd}  inflation-hedges: {inh}  diversifiers: "
          f"{[s for s in avail if s in DIVERSIFIERS]}")
    max_size = args.max_sleeves if args.max_sleeves > 0 else len(avail)
    combos = enumerate_combos(avail, eq, bd, args.min_sleeves, max_size)
    n_trials = len(combos) * len(schemes)
    print(f"Combinations: {len(combos)} x schemes {len(schemes)} = {n_trials} trials/fold")

    window_idx = ret.loc[w_s:w_e].index
    panel_full = build_panel(ret, avail, w_s, w_e)
    bd_full = both_down_mask(ret, w_s, w_e)
    eq_ref = ret.loc[w_s:w_e, [s for s in EQUITY_REFERENCE if s in ret.columns]].mean(axis=1)
    bd_ref = ret.loc[w_s:w_e, [s for s in BOND_REFERENCE if s in ret.columns]].mean(axis=1)
    regimes_win = regimes.loc[w_s:w_e]

    # sanity: both-down months cluster in stagflation?
    both_down_idx = bd_full[bd_full].index
    stag_idx = regimes_win[regimes_win["season"] == STAG].index
    overlap = len(set(both_down_idx) & set(stag_idx))
    print(f"\nBoth-down months: {len(both_down_idx)}; stagflation months: {len(stag_idx)}; "
          f"overlap {overlap} ({overlap/max(len(both_down_idx),1)*100:.0f}% of both-down are stagflation)")
    print("Season counts in window:")
    print(regimes_win["season"].value_counts().to_string())

    folds = make_folds(window_idx, args.min_train_years, args.test_years, args.step_years)
    print(f"\nWalk-forward folds: {len(folds)}")
    for i, (tr, te) in enumerate(folds, 1):
        print(f"  F{i}: TRAIN {tr[0].date()}..{tr[-1].date()} ({len(tr)}m) | "
              f"TEST {te[0].date()}..{te[-1].date()} ({len(te)}m)")

    # Walk-forward: per fold select on TRAIN (seasons score), eval on TEST
    oos_chunks, fold_log, per_fold_results, all_fold_weights = [], [], [], []
    all_train_results = []
    for i, (tr_idx, te_idx) in enumerate(folds, 1):
        print(f"\n-- Fold {i}: search on TRAIN {tr_idx[0].date()}..{tr_idx[-1].date()} --")
        panel_tr = build_panel(ret, avail, tr_idx[0], tr_idx[-1])
        bd_tr = both_down_mask(ret, tr_idx[0], tr_idx[-1])
        eqr_tr = ret.loc[tr_idx[0]:tr_idx[-1], [s for s in EQUITY_REFERENCE if s in ret.columns]].mean(axis=1)
        bdr_tr = ret.loc[tr_idx[0]:tr_idx[-1], [s for s in BOND_REFERENCE if s in ret.columns]].mean(axis=1)
        reg_tr = regimes.loc[tr_idx[0]:tr_idx[-1]]
        res = fast_search_seasons(panel_tr, ret, reg_tr, bd_tr, eqr_tr, bdr_tr, combos,
                                  schemes, args.cap, cost, args.shrink, args.trailing,
                                  label=f"F{i}")
        all_train_results.append(res)
        win = res.iloc[0]
        win_combo = win["combo"].split(",")
        win_sch = win["scheme"]
        # evaluate winner on TEST
        panel_te = build_panel(ret, avail, te_idx[0], te_idx[-1])
        idxs = [list(panel_te.columns).index(s) for s in win_combo]
        pre_te = precompute_refits(ret, list(panel_te.columns), panel_te.index, args.trailing, args.shrink)
        bt_te = backtest(panel_te, pre_te, idxs, win_sch, args.cap, cost)
        te_net = pd.Series(bt_te["net"], index=panel_te.index)
        oos_chunks.append(te_net)
        reg_te = regimes.loc[te_idx[0]:te_idx[-1]]
        bd_te = both_down_mask(ret, te_idx[0], te_idx[-1])
        eqr_te = ret.loc[te_idx[0]:te_idx[-1], [s for s in EQUITY_REFERENCE if s in ret.columns]].mean(axis=1)
        bdr_te = ret.loc[te_idx[0]:te_idx[-1], [s for s in BOND_REFERENCE if s in ret.columns]].mean(axis=1)
        te_m = compute_metrics_seasons(bt_te["net"], bt_te["gross"], bt_te["turnover"],
                                       panel_te.index, reg_te, bd_te, eqr_te, bdr_te, bt_te["div_ratio"])
        # capture this fold's winner weights (last realised target weights)
        wcols = [c for c in res.columns if c.startswith("w_")]
        win_w = {c[2:]: float(win[c]) for c in wcols if not pd.isna(win[c])}
        all_fold_weights.append(win_w)
        per_fold_results.append({"fold": i, "train": f"{tr_idx[0].date()}..{tr_idx[-1].date()}",
                                 "test": f"{te_idx[0].date()}..{te_idx[-1].date()}",
                                 "combo": win["combo"], "scheme": win_sch,
                                 "train_score": float(win["resilience_score"]),
                                 "test_sharpe": te_m.get("sharpe_net", float("nan")),
                                 "test_stag_sharpe": te_m.get("stag_sharpe", float("nan")),
                                 "test_both_down_ann": te_m.get("both_down_annualized", float("nan")),
                                 "test_maxdd": te_m.get("max_drawdown", float("nan")),
                                 "weights": win_w})
        fold_log.append({"fold": i, "combo": win["combo"], "scheme": win_sch,
                         "train_score": float(win["resilience_score"]),
                         "test_sharpe": te_m.get("sharpe_net", float("nan"))})
        print(f"  F{i} winner: {win['combo']} / {win_sch}  TEST Sharpe "
              f"{te_m.get('sharpe_net',float('nan')):.3f}  stag Sharpe "
              f"{te_m.get('stag_sharpe',float('nan')):.3f}")

    oos = pd.concat(oos_chunks).sort_index()
    oos.to_csv(os.path.join(args.out_dir, "oos_walkforward_returns.csv"))
    pd.DataFrame(per_fold_results).to_csv(os.path.join(args.out_dir, "per_fold.csv"), index=False)
    pd.concat(all_train_results, ignore_index=True).to_csv(
        os.path.join(args.out_dir, "train_results_all_folds.csv"), index=False)

    # OOS aggregate metrics
    reg_oos = regimes.loc[oos.index]
    bd_oos = both_down_mask(ret, oos.index[0], oos.index[-1])
    eqr_oos = ret.loc[oos.index[0]:oos.index[-1], [s for s in EQUITY_REFERENCE if s in ret.columns]].mean(axis=1)
    bdr_oos = ret.loc[oos.index[0]:oos.index[-1], [s for s in BOND_REFERENCE if s in ret.columns]].mean(axis=1)
    oos_m = compute_metrics_seasons(oos.values, oos.values, np.zeros(len(oos)), oos.index,
                                    reg_oos, bd_oos, eqr_oos, bdr_oos, float("nan"))

    # All-Weather benchmark over the OOS period, era-fair: use Gold/Precious Metals
    # when GLD is incomplete over the OOS window, drop sleeves absent in the era,
    # renormalize.
    cand = []
    for s, w in ALL_WEATHER_WEIGHTS.items():
        if s == "Gold":
            cand.append(("Gold", "Gold/Precious Metals", w))
        else:
            cand.append((s, None, w))
    cand_names = []
    for primary, alt, _ in cand:
        if primary in ret.columns:
            cand_names.append(primary)
        if alt and alt in ret.columns:
            cand_names.append(alt)
    panel_aw_full = build_panel(ret, cand_names, oos.index[0], oos.index[-1])
    complete = list(panel_aw_full.columns)
    aw_w = {}
    for primary, alt, w in cand:
        use = primary if primary in complete else (alt if alt and alt in complete else None)
        if use is not None:
            aw_w[use] = aw_w.get(use, 0.0) + w
    tot = sum(aw_w.values())
    aw_w = {s: w / tot for s, w in aw_w.items()} if tot > 0 else {}
    aw_sleeves = list(aw_w.keys())
    panel_aw = panel_aw_full[aw_sleeves] if aw_sleeves else panel_aw_full
    aw_bt = fixed_weight_backtest_costs(panel_aw, aw_w, cost)
    aw_oos = pd.Series(aw_bt["net"], index=panel_aw.index)
    aw_oos_m = compute_metrics_seasons(aw_bt["net"], aw_bt["gross"], aw_bt["turnover"],
                                       panel_aw.index, reg_oos, bd_oos, eqr_oos, bdr_oos, float("nan"))

    # Real returns
    real_oos = real_series(oos, deflator) if deflator is not None else None
    real_aw = real_series(aw_oos, deflator) if deflator is not None else None

    # DSR on the OOS walk-forward series
    dsr = deflated_sharpe(oos.values, n_trials * len(folds))

    # bootstrap CIs
    diag = {}
    if len(oos) >= 24:
        p, lo, hi = block_bootstrap_ci(oos.values, _ann_sharpe, args.bootstrap)
        diag["oos_sharpe"], diag["oos_sharpe_ci_lo"], diag["oos_sharpe_ci_hi"] = p, lo, hi
        stag_vals = oos[reg_oos["season"] == STAG].dropna().values
        if len(stag_vals) >= 8:
            ps, los, his = block_bootstrap_ci(stag_vals, _ann_ret, args.bootstrap)
            diag["oos_stag_ann"], diag["oos_stag_ci_lo"], diag["oos_stag_ci_hi"] = ps, los, his

    pd.DataFrame(list(diag.items()), columns=["metric", "value"]).to_csv(
        os.path.join(args.out_dir, "diagnostics.csv"), index=False)

    # average winner weights across folds (time-averaged allocation)
    all_sleeves_seen = sorted({k for d in all_fold_weights for k in d})
    avg_weights = {sk: float(np.nanmean([d.get(sk, np.nan) for d in all_fold_weights]))
                   for sk in all_sleeves_seen}
    latest_weights = all_fold_weights[-1] if all_fold_weights else {}

    write_report(args, oos, oos_m, aw_oos, aw_oos_m, real_oos, real_aw, deflator,
                 per_fold_results, reg_oos, dsr, diag, regimes_win, schemes, avail,
                 combos, n_trials, folds, overlap, avg_weights, latest_weights, inh)
    print(f"\nReport: {os.path.join(args.out_dir, 'report_seasons.md')}")
    print("Done.")
    return 0


def write_report(args, oos, oos_m, aw_oos, aw_oos_m, real_oos, real_aw, deflator,
                 per_fold_results, reg_oos, dsr, diag, regimes_win, schemes, avail,
                 combos, n_trials, folds, overlap, avg_weights, latest_weights, inh):
    L = []; a = L.append
    a("# Four-Seasons Walk-Forward Risk Parity — Canonical Report (v3)")
    a("")
    a("*Research / illustration only. Not investment advice.*")
    a("")
    long_run = args.preset == "long1985"
    if long_run:
        a("> **Long-history preset (1985–2026, ~41y).** Uses the asset-class series that")
        a("> exist back to 1985 (equities, treasuries, corporates, munis, gold via the")
        a("> VGPMX/gold-futures TR proxy) — the investable-as-of-1985 universe — and walks")
        a("> forward across ~41 years of regimes (1987 crash, 1994 bond crash, 1998 LTCM,")
        a("> 2000 dot-com, 2008 GFC, ZIRP, 2013 taper, 2020 COVID, 2022 stagflation).")
    else:
        a("> Re-thought after two critiques. (1) **No more single 10y/8y split:** this")
        a("> uses **walk-forward cross-validation** across the full 2008–2026 multi-regime")
        a("> history (GFC, ZIRP, taper, hiking, COVID, 2022 stagflation, 2023 bank stress),")
        a("> with **four-seasons (growth × inflation) regime scoring** — Bridgewater's actual")
        a("> framework — with **stagflation weighted 2x** (the All-Weather weak spot).")
    a("> **Inflation made visible:** inflation-hedge sleeves are in the universe "
      + ("(TIPS, gold, silver, commodities)" if not long_run else "(gold via the long proxy)") + ",")
    a(f"> and **real returns** are reported ({'CPI-deflated' if args.cpi_csv else 'gold-deflated purchasing-power stress — NOT literal CPI; provide --cpi-csv for true real'}).")
    a("")
    a("## 1. Setup")
    a("")
    a(f"- Window: {args.window_start} → {args.window_end} "
      f"({(pd.Timestamp(args.window_end)-pd.Timestamp(args.window_start)).days/365.25:.1f} years, "
      f"{len(regimes_win)} months).")
    a(f"- Sleeves ({len(avail)}): {', '.join(avail)}. Inflation hedges: {', '.join(inh) if inh else 'none'}.")
    a(f"- Walk-forward folds: {len(folds)} (expanding train min {args.min_train_years}y, "
      f"test {args.test_years}y, step {args.step_years}y). Trials/fold = {n_trials}.")
    a("- Regimes: Growth = sign(US Equity 12m return); Inflation = sign(10y yield 12m Δ).")
    a(f"- {overlap}/{len(regimes_win[regimes_win['season']=='GrowthDown InfUp'])} "
      f"both-down months are stagflation (confirms stagflation = the AW weak spot).")
    a(f"- Constraints: long-only, no leverage, 20% cap, 10 bps/side, Ledoit-Wolf, "
      f"trailing {args.trailing}m, schemes {schemes}.")
    a("- Score = 0.35·stagflation + 0.15·each other season + 0.10·overall Sharpe + 0.10·div ratio.")
    a("")
    a("## 2. Walk-forward OOS aggregate (concatenated held-out test periods)")
    a("")
    a(f"OOS spans **{oos.index[0].date()} → {oos.index[-1].date()}** ({len(oos)} months, "
      f"{len(oos)/12:.1f}y) — every month is out-of-sample (selected on prior data only).")
    a("")
    a("| Metric | All-Weather (OOS) | Winner process (OOS) |")
    a("|---|---:|---:|")
    for lab, key, f in [("CAGR (nominal)", None, None)]:
        a(f"| CAGR (nominal) | {fp(cagr(aw_oos))} | **{fp(cagr(oos))}** |")
    a(f"| Ann return (net) | {fp(aw_oos_m.get('ann_return_net'))} | **{fp(oos_m.get('ann_return_net'))}** |")
    a(f"| Ann vol | {fp(aw_oos_m.get('ann_vol'))} | **{fp(oos_m.get('ann_vol'))}** |")
    a(f"| Net Sharpe | {fn(aw_oos_m.get('sharpe_net'))} | **{fn(oos_m.get('sharpe_net'))}** |")
    a(f"| Max drawdown | {fp(aw_oos_m.get('max_drawdown'))} | **{fp(oos_m.get('max_drawdown'))}** |")
    a(f"| Both-down ann ret | {fp(aw_oos_m.get('both_down_annualized'))} | **{fp(oos_m.get('both_down_annualized'))}** |")
    a(f"| Diversification ratio | n/a | **{fn(oos_m.get('div_ratio'))}** |")
    a(f"| Corr w/ equity | {fn(aw_oos_m.get('corr_eq'))} | **{fn(oos_m.get('corr_eq'))}** |")
    if real_oos is not None:
        real_label = "CPI" if args.cpi_csv else "gold-deflated stress"
        a(f"| **CAGR (real, {real_label})** | "
          f"{fp(cagr(real_aw))} | **{fp(cagr(real_oos))}** |")
    a("")
    if "oos_sharpe" in diag:
        a(f"- Block-bootstrap 95% CI on OOS Sharpe: "
          f"[{diag['oos_sharpe_ci_lo']:.3f}, {diag['oos_sharpe_ci_hi']:.3f}]")
    a(f"- **Deflated Sharpe = {dsr['deflated_sr_ann']:.3f}** (P>0 = {dsr['dsr_prob']:.2f}; "
      f"trials = {int(dsr['n_trials'])}, incl. {len(folds)} folds).")
    a("")
    a("## 2b. What is the portfolio? (time-averaged winner weights across folds)")
    a("")
    a("The walk-forward winner is re-selected each fold, so there is no single static")
    a("portfolio. Below is the **time-averaged allocation** across folds (and the latest")
    a("fold), with investable proxies:")
    a("")
    a("| Sleeve | Avg weight | Latest fold | Investable proxy |")
    a("|---|---:|---:|---|")
    from risk_parity_backtest import SLEEVE_TO_ETF as _ETF
    for sk in sorted(avg_weights, key=lambda k: -avg_weights[k]):
        aw_ = avg_weights[sk]
        lw_ = latest_weights.get(sk, float("nan"))
        etf = _ETF.get(sk, SLEEVE_ETF_LONG.get(sk, "?"))
        lw_str = f"{lw_*100:5.2f}%" if not math.isnan(lw_) else "  n/a "
        a(f"| {sk} | {aw_*100:5.2f}% | {lw_str} | {etf} |")
    a("")
    a("## 3. The four seasons — per-regime OOS performance (the whole point)")
    a("")
    a("Average monthly net return in each economic season (OOS):")
    a("")
    a("| Season | All-Weather | Winner | Winner Sharpe |")
    a("|---|---:|---:|---:|")
    seasons_order = ["GrowthUp InfUp", "GrowthUp InfDown", "GrowthDown InfDown", "GrowthDown InfUp"]
    for sn in seasons_order:
        key = f"season_{sn.replace(' ', '_')}"
        aw_v = aw_oos_m.get(key, float("nan")); w_v = oos_m.get(key, float("nan"))
        tag = " *(stagflation / AW weak spot)*" if sn == STAG else ""
        a(f"| {sn}{tag} | {fp(aw_v)} | **{fp(w_v)}** | {fn(oos_m.get('stag_sharpe') if sn==STAG else float('nan')) if sn==STAG else '—'} |")
    a("")
    a("> A truly resilient portfolio is **positive (or flat) in all four seasons**,")
    a("> especially stagflation. If it leans on any one season, that's a hidden regime bet.")
    a("")
    a("## 4. Inflation stress — does inflation eat it alive?")
    a("")
    if real_oos is not None:
        a(f"- Nominal CAGR (OOS): **{fp(cagr(oos))}**  →  "
          f"{'CPI-real' if args.cpi_csv else 'gold-deflated real'} CAGR: **{fp(cagr(real_oos))}**")
        a(f"- All-Weather nominal {fp(cagr(aw_oos))} → real {fp(cagr(real_aw))}")
        a("")
        if args.cpi_csv:
            a("Inflation haircut to CAGR: "
              f"{(cagr(oos)-cagr(real_oos))*100:.2f} pp (winner) vs "
              f"{(cagr(aw_oos)-cagr(real_aw))*100:.2f} pp (All-Weather).")
        else:
            a("> **Gold-deflated is a HARSH stress** (gold rises with inflation, so")
            a("> deflating by gold measures return in *purchasing-power-of-gold* units).")
            a("> A near-zero/negative number means inflation (as priced by gold) ate the")
            a("> nominal return. For literal CPI real returns, re-run with `--cpi-csv`.")
    a("")
    a("## 5. Per-fold selections (walk-forward, fully OOS)")
    a("")
    a("| Fold | TRAIN | TEST | Combo | Scheme | Train score | TEST Sharpe | TEST stag Sharpe | TEST both-down ann | TEST maxDD |")
    a("|---:|---|---|---|---|---:|---:|---:|---:|---:|")
    for r in per_fold_results:
        a(f"| {r['fold']} | {r['train']} | {r['test']} | {r['combo']} | {r['scheme']} | "
          f"{r['train_score']:.1f} | {fn(r['test_sharpe'])} | {fn(r['test_stag_sharpe'])} | "
          f"{fp(r['test_both_down_ann'])} | {fp(r['test_maxdd'])} |")
    a("")
    a("## 6. Caveats")
    a("")
    a("- **Inflation proxy:** the four-seasons inflation signal is the 10y yield 12m Δ")
    a("  (market inflation-expectations/rates proxy), NOT literal CPI. Real returns use")
    a("  CPI only if `--cpi-csv` is supplied; otherwise a harsh gold-deflated stress.")
    a("  **Add a CPI series for true real-return accounting** — this is the single biggest")
    a("  remaining gap.")
    if long_run:
        a("- **History length:** the long1985 preset uses the asset-class series that exist")
        a("  back to 1985 (~41y) — the investable-as-of-1985 set. Sleeves that only start in")
        a("  the ETF era (TIPS 2004, GLD 2004, DBC 2006, UUP 2007, EM bonds 2008) are NOT in")
        a("  this preset; run `--preset modern` for the richer 2008+ universe. 1871 is not")
        a("  available for these sleeves.")
    else:
        a("- **History length:** modern preset uses the full ETF-era multi-sleeve set from")
        a("  ~2008 (18.6y). For the ~41y investable-as-of-1985 view, run `--preset long1985`.")
    a("- **One inflation spike in-sample (2021-22):** the stagflation corner is still")
    a("  thinly sampled; per-season Sharpe is noisy. Read the bootstrap CI.")
    a("- No vol target; no regime-conditioned/trend overlay yet (item 10).")
    a("")
    with open(os.path.join(args.out_dir, "report_seasons.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
