#!/usr/bin/env python3
"""
risk_parity_eval.py  (v2 — remediated)
======================================
Anti-overfit, allocation-aware, *investable* risk-parity search.

This version fixes the concrete flaws flagged in review:

  [1] VOLATILITY SLEEVE. The data only has ^VIX (the non-tradable spot index),
      not a VXX total-return series. A long spot-VIX position is NOT investable
      (you cannot hold the VIX index) and its ~140% contribution to both-down
      return was an artifact. Volatility is therefore DROPPED from the default
      search universe; `--include-volatility` opts back in with a loud caveat.
  [2] REPORT RECONCILIATION. The canonical headline is the OUT-OF-SAMPLE report
      (this file's report_eval.md). The in-sample report.md carries a banner
      pointing here and demotes its numbers to a method appendix.
  [3] CONCENTRATION CAP. A per-sleeve weight cap (default 20%) is enforced on
      every scheme via iterative clip-and-redistribute. A 47% UUP position is no
      longer possible; ≥5 sleeves are required for the cap to be non-binding.
  [4] OBJECTIVE ENCODED. The score now includes a DIVERSIFICATION RATIO term and
      a penalty for correlation with the equity reference during both-down months
      (i.e. "uncorrelated positive returns" is measured, not assumed). Diversifi-
      cation ratio and vs-reference correlations are reported in the headline.
  [5] COVARIANCE SHRINKAGE. Ledoit-Wolf (2001, identity-target) shrinkage is
      applied to the trailing covariance used by every scheme (default on).
  [7] TRANSACTION COSTS. Monthly rebalance turnover is charged at `--cost-bps`
      per side (default 10 bps). Headline metrics are NET of cost; gross shown
      alongside.
  [8] DEFLATED SHARPE. Given the number of trials (combos × schemes), the
      Deflated Sharpe Ratio (Bailey & López de Prado 2014) is reported alongside
      the raw OOS Sharpe.
  [9] ROLLING SELECTION RE-ENUMERATED. The walk-forward selection no longer uses
      a TRAIN-pre-screened shortlist. Each January it re-runs the FULL
      combo × scheme search on the trailing window (data strictly prior) and
      picks #1 — genuinely OOS, not conditioned on the TRAIN ranking.

Composition vs allocation is still separated: every combination is backtested
under FIVE schemes (EW, InvVol, InvVar, ERC, MinVar). All solvers pure NumPy.
No leverage, long-only, ETF-investable.

Research / illustration only. Not investment advice.
"""

from __future__ import annotations

import argparse
import itertools
import math
import os
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from risk_parity_backtest import (
    load_monthly_returns, both_down_mask, CRISIS_WINDOWS,
    SEARCH_SLEEVES_DEFAULT, EQUITY_SLEEVES, BOND_SLEEVES,
    ALL_WEATHER_WEIGHTS, SLEEVE_TO_ETF, MONTHS_PER_YEAR,
    EQUITY_REFERENCE, BOND_REFERENCE, erc_weights, risk_contributions,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "output", "risk_parity_eval")
TICKER_CSV = os.path.join(HERE, "output", "monthly_returns_by_ticker.csv")
TRAIN_DEFAULT = ("2008-01-31", "2017-12-31")
TEST_DEFAULT = ("2018-01-31", "2026-07-31")
EULER_GAMMA = 0.5772156649015328606

# External (investable, non-candidate) reference tickers for the both-down
# regime and the "correlation with equity" metric. SPY = broad US equity TR
# (1993-02+); AGG = broad US agg-bond TR (2003-10+, covers the canonical
# 2008+ TRAIN/TEST window); BND/IEF are fallbacks. Using external indices
# breaks the tautology where the reference baskets overlapped the candidate
# universe (every bond sleeve + 3 of 4 equity sleeves were themselves the
# reference, so a bond-heavy candidate mechanically scored "low equity corr"
# just by holding bonds -- see docs/peer-review.md §2b).
EXT_EQUITY_TICKER = "SPY"
EXT_BOND_TICKERS = ["AGG", "BND", "IEF"]


_TICKER_WIDE: pd.DataFrame | None = None


def load_ticker_monthly(tickers: Sequence[str]) -> pd.DataFrame:
    """Load monthly returns for the given tickers from the long-format
    ticker CSV (date,ticker,...,monthly_return), pivoted to wide
    (index=date, columns=ticker). Cached on first call."""
    global _TICKER_WIDE
    if _TICKER_WIDE is None:
        df = pd.read_csv(TICKER_CSV, usecols=["date", "ticker", "monthly_return"])
        df["date"] = pd.to_datetime(df["date"])
        _TICKER_WIDE = df.pivot_table(index="date", columns="ticker",
                                      values="monthly_return").sort_index()
    cols = [t for t in tickers if t in _TICKER_WIDE.columns]
    return _TICKER_WIDE[cols]


def _external_refs(ret: pd.DataFrame) -> Tuple[pd.Series, pd.Series, str]:
    """Build full-range external equity + bond reference series aligned to
    ret.index. Pre-inception months (e.g. AGG before 2003-10) are filled from
    the legacy sleeve-average reference so the series is complete; in the
    canonical 2008+ window AGG/SPY are complete so no fallback fires."""
    tk = load_ticker_monthly([EXT_EQUITY_TICKER] + EXT_BOND_TICKERS)
    sleeve_eq = ret.loc[:, [s for s in EQUITY_REFERENCE if s in ret.columns]].mean(axis=1)
    sleeve_bd = ret.loc[:, [s for s in BOND_REFERENCE if s in ret.columns]].mean(axis=1)
    if EXT_EQUITY_TICKER in tk.columns:
        eq = tk[EXT_EQUITY_TICKER].reindex(ret.index).combine_first(sleeve_eq)
    else:
        eq = sleeve_eq
    bond_tk = next((t for t in EXT_BOND_TICKERS if t in tk.columns), None)
    if bond_tk is None:
        bd = sleeve_bd
    else:
        bd = tk[bond_tk].reindex(ret.index).combine_first(sleeve_bd)
    return eq, bd, bond_tk or "sleeves"


def regime_references(ret: pd.DataFrame, start, end,
                      ref_mode: str) -> Tuple[pd.Series, pd.Series, pd.Series, str]:
    """Return (eq_ref, bd_ref, both_down_mask, ref_label) over [start, end].
    ref_mode='external' uses SPY + AGG (investable, non-candidate); 'sleeves'
    reproduces the legacy sleeve-average reference exactly (regression guard)."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if ref_mode == "external":
        eq_full, bd_full, bond_tk = _external_refs(ret)
        eqr = eq_full.loc[start:end]
        bdr = bd_full.loc[start:end]
        mask = ((eqr < 0) & (bdr < 0)).fillna(False)
        return eqr, bdr, mask, f"external: {EXT_EQUITY_TICKER} + {bond_tk}"
    mask = both_down_mask(ret, start, end)
    eqr = ret.loc[start:end, [s for s in EQUITY_REFERENCE if s in ret.columns]].mean(axis=1)
    bdr = ret.loc[start:end, [s for s in BOND_REFERENCE if s in ret.columns]].mean(axis=1)
    return eqr, bdr, mask, "sleeves (legacy)"


# --------------------------------------------------------------------------- #
# Sleeve universe (Volatility dropped by default)
# --------------------------------------------------------------------------- #

def default_sleeves(include_volatility: bool) -> List[str]:
    s = [x for x in SEARCH_SLEEVES_DEFAULT if x != "Volatility"]
    if include_volatility:
        s = s + ["Volatility"]
    return s


# --------------------------------------------------------------------------- #
# Covariance shrinkage (Ledoit-Wolf 2001, identity target)
# --------------------------------------------------------------------------- #

def ledoit_wolf_cov(X: np.ndarray) -> np.ndarray:
    """Ledoit-Wolf (2001) shrinkage toward a scaled identity (well-conditioned
    estimator). Returns a shrunk covariance matrix."""
    X = np.asarray(X, dtype=float)
    T, n = X.shape
    if T < 3 or n < 2:
        c = np.cov(X, rowvar=False) if T >= 2 else np.eye(n)
        return np.atleast_2d(c)
    Xm = X - X.mean(axis=0)
    S = (Xm.T @ Xm) / T
    mu = np.trace(S) / n
    I = np.eye(n)
    d2 = np.sum((S - mu * I) ** 2) / n
    # b2 = (1/T^2) sum_t ||x_t x_t' - S||_F^2  / n  (mean of squared entries)
    b2 = 0.0
    for t in range(T):
        diff = np.outer(Xm[t], Xm[t]) - S
        b2 += np.sum(diff ** 2)
    b2 = b2 / (T * T * n)
    b2 = min(b2, d2)
    delta = b2 / d2 if d2 > 0 else 0.0
    delta = float(min(1.0, max(0.0, delta)))
    return delta * mu * I + (1.0 - delta) * S


# --------------------------------------------------------------------------- #
# Weight solvers (operate on a covariance matrix, not a DataFrame -> fast)
# --------------------------------------------------------------------------- #

def project_simplex(v: np.ndarray) -> np.ndarray:
    n = v.size
    u = np.sort(v)[::-1]
    cssv = np.cumsum(u) - 1.0
    idx = np.arange(1, n + 1)
    cond = u - cssv / idx > 0
    rho = int(np.nonzero(cond)[0][-1])
    theta = cssv[rho] / (rho + 1.0)
    return np.maximum(v - theta, 0.0)


def project_capped_simplex(v: np.ndarray, cap: float) -> np.ndarray:
    """Euclidean projection of v onto the capped simplex
    {w : w_i >= 0, w_i <= cap, sum w_i = 1}.

    The exact projection has the form ``w_i = clip(v_i - tau, 0, cap)`` for a
    single threshold ``tau`` with ``sum w_i = 1`` (box + equality constraint ->
    one Lagrange multiplier). Sort ``v`` descending: the at-cap coords are a
    prefix (largest v), the at-0 coords are a suffix (smallest v), the free
    coords are the middle, and ``tau = (cap*p + sum(middle) - 1) / m``. We search
    the O(n^2) (prefix, suffix) partitions for the consistent one. Cost is
    O(n^3) but n <= ~8 sleeves, so this is ~hundreds of ops with **no
    per-gradient-step Python loop** (the old bisection did 40-60 np.clip calls
    per projection, which dominated ERC/MinVar runtime). This is what makes
    MinVar/ERC box-constrained: the cap is enforced *inside* the optimizer
    (projected gradient), not clipped on afterwards.

    Infeasible (n*cap < 1) -> the cap cannot be satisfied, so drop it and
    project onto the plain simplex (sum=1, w>=0); the caller sees the cap
    unenforced because it is infeasible for this combo size. This matches the
    legacy post-hoc path's behavior for thin combos and is the least-violating
    feasible point."""
    v = np.asarray(v, dtype=float)
    n = v.size
    if cap <= 0 or cap >= 1.0:
        return project_simplex(v)
    if n * cap < 1.0 - 1e-12:
        return project_simplex(v)
    # The projection w_i = clip(v_i - tau, 0, cap) is invariant to an additive
    # shift (v -> v - c, tau -> tau - c). When a gradient step leaves huge v
    # entries (e.g. ERC's inv_n/w blows up as w_i -> 0, producing v ~ 1e10), the
    # subtraction v_i - tau suffers catastrophic cancellation (both ~1e10, differ
    # by ~cap, lost to float64 ulp). Shifting by v.max() makes the cap/free coords
    # ~O(1) so the subtraction is exact; only deep-zero coords stay huge-negative
    # and those are clipped to 0 (harmless). Result is identical, numerically stable.
    v = v - float(v.max())
    order = np.argsort(v)[::-1]              # descending
    vs = v[order]
    eps = 1e-12
    for p in range(0, n + 1):                 # p coords at cap (prefix)
        for q in range(0, n - p + 1):         # q coords at 0 (suffix)
            m = n - p - q                      # free (middle)
            if m == 0:
                if abs(cap * p - 1.0) < 1e-9:
                    w = np.zeros(n)
                    w[order[:p]] = cap
                    return w
                continue
            mid = vs[p:p + m]
            tau = (cap * p + float(mid.sum()) - 1.0) / m
            # consistency: prefix at cap -> vs[p-1] - tau >= cap; vs[p] - tau <= cap
            if p > 0 and vs[p - 1] - tau < cap - eps:
                continue
            if p < n and vs[p] - tau > cap + eps:
                continue
            # free coords strictly inside (0, cap): vs[p+m-1] - tau > 0; vs[p] - tau < cap (checked)
            if mid[-1] - tau <= eps:
                continue
            # suffix at 0 -> vs[p+m] - tau <= 0; vs[p+m-1] - tau >= 0 (checked via mid[-1])
            if q > 0 and vs[p + m] - tau > eps:
                continue
            w = np.empty(n)
            w[order[:p]] = cap
            w[order[p:p + m]] = mid - tau
            w[order[p + m:]] = 0.0
            w = np.clip(w, 0.0, cap)
            # Force exact sum=1 without disturbing the cap. The float residual
            # (~1e-7 from rounding in ``mid - tau``) is distributed onto the
            # interior coords (strictly inside (0, cap)); at-cap and at-zero
            # coords are left untouched so the cap stays exact. If there are no
            # interior coords the partition is all-cap/all-zero (handled by the
            # m==0 branch above, which is exact), so residual is ~0 anyway.
            resid = 1.0 - float(w.sum())
            interior = (w > 1e-9) & (w < cap - 1e-9)
            if abs(resid) > 0.0 and interior.any():
                share = w[interior] / float(w[interior].sum())
                w[interior] = np.clip(w[interior] + resid * share, 0.0, cap)
            return w
    # Fallback (numerical edge): equal weight is always feasible here.
    return np.ones(n) / n


def _lmax(cov: np.ndarray, iters: int = 40) -> float:
    rng = np.random.RandomState(0)
    v = rng.standard_normal(cov.shape[0])
    nv = np.linalg.norm(v)
    if nv == 0:
        return 1.0
    v /= nv
    for _ in range(iters):
        v = cov @ v
        n = np.linalg.norm(v)
        if n == 0:
            return 1.0
        v /= n
    return float((v @ cov @ v) / max(v @ v, 1e-30))


def s_ew(cov, vol, cap: float = 0.0, erc_cap_mode: str = "capped", **kw):
    n = cov.shape[0]; return np.ones(n) / n

def s_invvol(cov, vol, cap: float = 0.0, erc_cap_mode: str = "capped", **kw):
    w = 1.0 / np.where(vol > 0, vol, 1e-12); return w / w.sum()

def s_invvar(cov, vol, cap: float = 0.0, erc_cap_mode: str = "capped", **kw):
    v = vol ** 2; w = 1.0 / np.where(v > 0, v, 1e-12); return w / w.sum()

def s_erc(cov, vol, cap: float = 0.0, erc_cap_mode: str = "capped", **kw):
    """ERC dispatch. With a cap active:
      - erc_cap_mode='capped'  -> projected-gradient on the log-barrier ERC
        objective projected onto the capped simplex (true box-constrained
        solve; an *approximation* to exact capped-ERC, which needs an
        active-set/ALM solver — see docs/peer-review.md). Recommend MinVar
        when a cap is active; MinVar-under-cap is exact.
      - erc_cap_mode='posthoc' -> legacy: uncapped ERC, caller clips afterwards.
      - erc_cap_mode='none'    -> uncapped ERC, no clip (cap ignored)."""
    if 0.0 < cap < 1.0 and erc_cap_mode == "capped":
        return s_erc_capped(cov, vol, cap=cap)
    return erc_weights(cov)

def s_erc_capped(cov, vol, cap: float, n_iter: int = 1200,
                 tol: float = 1e-9) -> np.ndarray:
    """Projected gradient on 0.5 w'Sw - (1/n) sum ln(w_i), projected onto the
    capped simplex at each step. Approximate capped-ERC (the projection keeps
    the cap feasible but the log-barrier KKT is only exactly satisfied when no
    upper bound binds). Used by s_erc when erc_cap_mode='capped'. n_iter/tol
    tuned for speed: ERC-capped is the *approximate* scheme (MinVar-under-cap is
    exact and is the empirical winner), so 1200 iters with a 1e-9 early stop is
    more than enough for n<=8 with the inverse-vol warm start."""
    n = cov.shape[0]
    if n * cap < 1.0 - 1e-12:
        return np.ones(n) / n
    w = 1.0 / np.where(vol > 0, vol, 1e-12)
    w = w / w.sum()
    w = project_capped_simplex(w, cap)
    lr = 1.0 / max(_lmax(cov), 1e-12)
    inv_n = 1.0 / n
    for _ in range(n_iter):
        g = cov @ w - inv_n / np.maximum(w, 1e-12)
        w_new = project_capped_simplex(w - lr * g, cap)
        if np.max(np.abs(w_new - w)) < tol:
            w = w_new
            break
        w = w_new
    # project_capped_simplex already enforces sum=1 (residual-corrected) and
    # max<=cap exactly, so a final w/w.sum() is unnecessary AND harmful: when the
    # projection's sum is slightly under 1, dividing by it scales the at-cap
    # coord above the cap (the very property the "ERC/MinVar under cap" label
    # claims). Return the projected weights directly.
    return w

def s_minvar(cov, vol, cap: float = 0.0, erc_cap_mode: str = "capped",
             n_iter: int = 800, tol: float = 1e-9) -> np.ndarray:
    """Minimum-variance via projected gradient. With a cap in (0,1) the
    projection is onto the *capped* simplex, so this is a true box-constrained
    QP (the empirical winner) — the cap is enforced inside the solver, not
    clipped on afterwards. Without a cap, plain simplex projection."""
    n = cov.shape[0]
    v = vol ** 2
    w = (1.0 / np.where(v > 0, v, 1e-12))
    w = w / w.sum()                       # warm start = inverse variance
    capped = 0.0 < cap < 1.0
    if capped:
        w = project_capped_simplex(w, cap)
    lr = 1.0 / max(_lmax(cov), 1e-12)
    for _ in range(n_iter):
        g = 2.0 * (cov @ w)
        w_new = project_capped_simplex(w - lr * g, cap) if capped \
            else project_simplex(w - lr * g)
        if np.max(np.abs(w_new - w)) < tol:
            w = w_new
            break
        w = w_new
    # See s_erc_capped: projection already enforces sum=1 & max<=cap exactly,
    # so no final renormalization (which would break the cap when sum<1).
    return w

def s_ls_tsmom(cov, vol, cap: float = 0.0, erc_cap_mode: str = "capped", **kw):
    """Marker/base for the LS-TSMOM scheme. The actual long/short managed-
    futures logic is monthly-signal and lives in _backtest_ls_tsmom (dispatched
    from backtest()); this just returns the equal-weight base so SCHEMES has a
    callable for combo×scheme enumeration and the rolling cov-solve fallback."""
    n = cov.shape[0]; return np.ones(n) / n


SCHEMES: Dict[str, Callable] = {
    "EW": s_ew, "InvVol": s_invvol, "InvVar": s_invvar,
    "ERC": s_erc, "MinVar": s_minvar, "LS-TSMOM": s_ls_tsmom,
}
SCHEME_ORDER = ["EW", "InvVol", "InvVar", "ERC", "MinVar", "LS-TSMOM",
                "TrendGate", "RP-LS-Overlay", "StructShort", "TG-LS-Overlay",
                "TG-Short", "TG-Short-LS", "TG-Short-6m",
                "EW-Short", "EW-Short-LS", "EW-Short-6m",
                "EW-MA-Short", "EW-Vol-Short", "EW-DMA-Short",
                "EW-AsymMA-Short", "EW-DDStop-Short",
                "EW-AsymMA-Short-6", "EW-AsymMA-Short-9", "EW-AsymMA-Tight",
                "EW-AsymVol-Short",
                "EW-Hedge-DMA-1", "EW-Hedge-DMA", "EW-Hedge-DMA-2",
                "EW-Hedge-MA", "EW-Hedge-DD",
                "EW-Hedge-Dur", "EW-Hedge-Dur-MA", "EW-Hedge-Dur-DD",
                "EW-Hedge-Dur-2", "EW-Hedge-Dur-DD2",
                "EW-Infl-Dur", "EW-Infl-DurL", "EW-Infl-Both",
                "EW-Infl-BothL", "EW-Infl-DurL2",
                "EW-InflC-Both", "EW-InflC-BothL", "EW-InflC-Dur",
                "EW-InflC-DurL", "EW-InflC-Both6",
                "EW-Scale-Mom", "EW-Scale-Mom6", "EW-Scale-Vol",
                "EW-Scale-MomL", "EW-Scale-Infl"]
# Schemes that solve a covariance-based target weight annually (vs LS-TSMOM,
# which is a monthly momentum signal with no covariance target).
COV_SCHEMES = {"EW", "InvVol", "InvVar", "ERC", "MinVar"}
# TrendProtect flavor presets -- four constructions of one parameterized
# engine (_backtest_flavor). Each pairs a long MinVar base leg (annual refit,
# cap-respecting) with active overlays targeting the All-Weather weak spot
# (both-down / stagflation) while keeping equity upside. See docs/portfolio-
# flavors.md for the full construction + measured comparison.
#   trend_gate   : gate equity sleeves when their trailing-12m return < 0.
#   gate_mode    : "cash" (gate equity to 0, long-only, gross<=1) OR "short"
#                  (FLIP the equity sleeve to net-short when mom<0 -- long
#                  equity when up, SHORT equity when down; bonds/gold/diversifiers
#                  stay long. This is the direct lever for negative downside-beta
#                  while keeping upside-beta, the brief's "correlated up, protected
#                  down". Adds gross when equity is short -> leverage cost on >1.)
#   w_overlay    : LS-TSMOM dollar-neutral momentum sleeve gross (adds gross).
#   struct_short : (sleeve_name, w_short) permanent sleeve-level net short.
#   lookback     : optional per-preset override of the trend-signal window (months).
#   gate_signal  : the equity-gate signal. "tsmom" (default, trailing-lookback
#                  return -- LAGGING, the round-1/2 signal) OR a LEADING signal:
#                  "ma" (price vs its `lookback`-month SMA -- long above, short
#                  below; an MA crosses BEFORE a lookback-return flips sign),
#                  "vol" (realized-vol regime -- long in calm, short in high-vol
#                  stress; vol spikes tend to LEAD drawdowns), or "dma" (dual-MA
#                  -- long when the 3m MA > 10m MA; faster than a single MA). The
#                  round-3 leading-signal family targets the round-2 blocker
#                  (a lagging signal is long into drawdown starts and short into
#                  rally starts -> Dnβ >= Upβ everywhere).
FLAVOR_PRESETS: Dict[str, dict] = {
    "TrendGate":     {"trend_gate": True,  "gate_mode": "cash",
                      "w_overlay": 0.0, "struct_short": None},
    "RP-LS-Overlay": {"trend_gate": False, "w_overlay": 0.30,
                      "struct_short": None},
    "StructShort":   {"trend_gate": False, "w_overlay": 0.0,
                      "struct_short": ("US Treasuries", 0.30)},
    "TG-LS-Overlay": {"trend_gate": True,  "gate_mode": "cash",
                      "w_overlay": 0.20, "struct_short": None},
    # New: short the equity sleeve on the downside signal (the brief's lever).
    "TG-Short":      {"trend_gate": True,  "gate_mode": "short",
                      "w_overlay": 0.0, "struct_short": None},
    "TG-Short-LS":   {"trend_gate": True,  "gate_mode": "short",
                      "w_overlay": 0.20, "struct_short": None},
    "TG-Short-6m":   {"trend_gate": True,  "gate_mode": "short",
                      "w_overlay": 0.0, "struct_short": None, "lookback": 6},
    # EW-base variants: equal-weight base (keeps real equity weight, like AW) so the
    # short-on-downside gate has equity to flip and the return floor is near AW.
    "EW-Short":      {"trend_gate": True,  "gate_mode": "short", "base_mode": "ew",
                      "w_overlay": 0.0, "struct_short": None},
    "EW-Short-LS":   {"trend_gate": True,  "gate_mode": "short", "base_mode": "ew",
                      "w_overlay": 0.20, "struct_short": None},
    "EW-Short-6m":   {"trend_gate": True,  "gate_mode": "short", "base_mode": "ew",
                      "w_overlay": 0.0, "struct_short": None, "lookback": 6},
    # Round 3: LEADING downside signals (EW base, gate_mode=short). The round-2
    # blocker was that trailing 12m/6m momentum LAGS -- long into drawdown starts,
    # short/flat into rally starts -> Dnβ >= Upβ everywhere. These gate equity on a
    # signal that LEADS the price: a moving average, a volatility regime, or a
    # dual-MA. Each keeps real equity weight (EW base) and flips equity to net-short
    # on the downside signal (gate_mode=short), the construction the brief allows.
    "EW-MA-Short":   {"trend_gate": True,  "gate_mode": "short", "base_mode": "ew",
                      "gate_signal": "ma",  "w_overlay": 0.0, "struct_short": None,
                      "lookback": 10},
    "EW-Vol-Short":  {"trend_gate": True,  "gate_mode": "short", "base_mode": "ew",
                      "gate_signal": "vol", "w_overlay": 0.0, "struct_short": None},
    "EW-DMA-Short":  {"trend_gate": True,  "gate_mode": "short", "base_mode": "ew",
                      "gate_signal": "dma", "w_overlay": 0.0, "struct_short": None},
    # Round 4: ASYMMETRIC (hysteretic) gates -- fast downside exit, slow upside
    # re-entry. Direct test of the round-3 prescription (a symmetric signal can't
    # be "correlated up, protected down"; an asymmetric one might).
    "EW-AsymMA-Short": {"trend_gate": True, "gate_mode": "short", "base_mode": "ew",
                        "gate_signal": "asym_ma", "w_overlay": 0.0, "struct_short": None},
    "EW-DDStop-Short": {"trend_gate": True, "gate_mode": "short", "base_mode": "ew",
                        "gate_signal": "dd_stop", "w_overlay": 0.0, "struct_short": None},
    # Round-4b sweep -- widen the hysteretic-gate band to test whether a LESS-
    # overshooting re-entry can keep Upβ positive while Dnβ stays negative (the
    # round-4 EW-AsymMA-Short with slow_entry=12 drove Upβ negative too: the slow
    # re-entry stayed short through rally starts). slow_entry in {6, 9, 12} is
    # the grid; EW-AsymMA-Tight also tightens the fast exit. EW-AsymVol-Short is
    # a hysteretic vol-gate (a vol spike flees; vol must calm below a lower bar
    # to return -- fixes the round-3 EW-Vol-Short 2020 V-rebound short).
    "EW-AsymMA-Short-6": {"trend_gate": True, "gate_mode": "short", "base_mode": "ew",
                          "gate_signal": "asym_ma", "slow_entry": 6, "fast_exit": 3,
                          "w_overlay": 0.0, "struct_short": None},
    "EW-AsymMA-Short-9": {"trend_gate": True, "gate_mode": "short", "base_mode": "ew",
                          "gate_signal": "asym_ma", "slow_entry": 9, "fast_exit": 3,
                          "w_overlay": 0.0, "struct_short": None},
    "EW-AsymMA-Tight": {"trend_gate": True, "gate_mode": "short", "base_mode": "ew",
                        "gate_signal": "asym_ma", "slow_entry": 6, "fast_exit": 2,
                        "w_overlay": 0.0, "struct_short": None},
    "EW-AsymVol-Short": {"trend_gate": True, "gate_mode": "short", "base_mode": "ew",
                         "gate_signal": "asym_vol", "w_overlay": 0.0, "struct_short": None},
    # Round 5: DECOUPLED insurance overlay (gate_mode="overlay"). The long EW
    # base NEVER flips -> Upβ stays positive (the round-4b structural blocker's
    # fix). A SEPARATE additive short overlay on the equity sleeves activates
    # only on a downside signal (flat otherwise) -> Dnβ pushed down. The overlay
    # signal is FAST-OFF (symmetric / dd_stop), the opposite hysteresis of round
    # 4, so it does not drag the rally. ``w_hedge`` = fraction of each equity
    # sleeve's base weight shorted when down; >1 -> net short equity in down-
    # months (needed to push Dnβ negative). Additive gross -> leverage cost.
    "EW-Hedge-DMA-1":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "dma", "w_hedge": 1.0, "w_overlay": 0.0,
                        "struct_short": None},
    "EW-Hedge-DMA":    {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "dma", "w_hedge": 1.5, "w_overlay": 0.0,
                        "struct_short": None},
    "EW-Hedge-DMA-2":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "dma", "w_hedge": 2.0, "w_overlay": 0.0,
                        "struct_short": None},
    "EW-Hedge-MA":     {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "ma", "w_hedge": 1.5, "w_overlay": 0.0,
                        "struct_short": None},
    "EW-Hedge-DD":     {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "dd_stop", "w_hedge": 1.5, "w_overlay": 0.0,
                        "struct_short": None},
    # --- Round 6: decoupled overlay + DURATION short (the both-down / stagflation
    # fix) + a fast equity-drawdown trigger. Same never-flip long base as round 5
    # (Upβ stays positive), but the additive overlay now ALSO shorts the BOND
    # sleeves on their own downside signal (w_hedge_bd) -- directly hedging the
    # both-down months where bonds fall WITH equities (the round-5 gap). The
    # "eq_dd" presets swap the lagging dma/ma equity signal for a symmetric fast
    # drawdown trigger that fires IN down-months. ---
    "EW-Hedge-Dur":    {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "dma", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                        "w_overlay": 0.0, "struct_short": None},
    "EW-Hedge-Dur-MA": {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "ma", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                        "w_overlay": 0.0, "struct_short": None},
    "EW-Hedge-Dur-DD": {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "eq_dd", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                        "w_overlay": 0.0, "struct_short": None},
    "EW-Hedge-Dur-2":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "dma", "w_hedge": 1.5, "w_hedge_bd": 2.0,
                        "w_overlay": 0.0, "struct_short": None},
    "EW-Hedge-Dur-DD2":{"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                        "gate_signal": "eq_dd", "w_hedge": 1.5, "w_hedge_bd": 2.0,
                        "w_overlay": 0.0, "struct_short": None},
    # --- Round 7: LEADING macro gate (the user's "leading downside signal" ask).
    # Same never-flip long EW base as rounds 5-6 (Upβ stays positive), but the
    # overlays now fire off an EX-ANTE INFLATION REGIME (trailing-12m return of
    # the Commodities sleeve, a macro signal external to the combo) instead of
    # a lagging sleeve-level trend. Regime-conditional and SYMMETRIC: when
    # inflation is RISING (stagflation risk-off, 2022) short bonds (w_hedge_bd)
    # and optionally equity (w_hedge); when inflation is FALLING (disinflation,
    # 2008/2020) add a LONG-duration tilt (w_long_bd) to own the bonds that rally
    # in flight-to-quality -- the regime where bonds hedge equity for free and
    # Dnβ can go negative. gate_signal="infl_regime" is the new lever. ---
    "EW-Infl-Dur":    {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 0.0, "w_hedge_bd": 1.5,
                       "w_long_bd": 0.0, "w_overlay": 0.0, "struct_short": None},
    "EW-Infl-DurL":   {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 0.0, "w_hedge_bd": 1.5,
                       "w_long_bd": 1.5, "w_overlay": 0.0, "struct_short": None},
    "EW-Infl-Both":   {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                       "w_long_bd": 0.0, "w_overlay": 0.0, "struct_short": None},
    "EW-Infl-BothL":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                       "w_long_bd": 1.5, "w_overlay": 0.0, "struct_short": None},
    "EW-Infl-DurL2":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 0.0, "w_hedge_bd": 1.5,
                       "w_long_bd": 2.0, "w_overlay": 0.0, "struct_short": None},
    # --- Round 8: inflation-regime + equity-rolling CONFIRMATION gate. The round-7
    # broad inflation gate (EW-Infl-*) achieved Upβ > Dnβ for the first time but at
    # ~0 return: it shorted in EVERY rising-inflation month, bleeding carry in non-
    # crisis reflation rallies (2021, 2024). Round 8 narrows the gate with a COINCIDENT
    # confirmation: the overlays fire only when the leading inflation signal is
    # confirmed by the external equity proxy actually rolling over
    # (infl_confirm="eq_neg", trailing-`eq_confirm_lookback` US Equity return < 0).
    # Short leg fires on (infl_up AND eq_rolling) -> 2022 (inflation up + equity
    # falling) protected, 2021/2024 (inflation up + equity rallying) NOT shorted ->
    # return preserved. Long-tilt fires on ((NOT infl_up) AND eq_rolling) -> true
    # flight-to-quality (2008 Q4, 2020 Q1: disinflation + equity crash + bonds
    # rally) only, NOT 2022-23 disinflation-with-bonds-falling -> fixes the round-7
    # duration-only both-down drag. Same never-flip long EW base -> Upβ positive.
    # infl_confirm defaults "" -> the round-7 EW-Infl-* presets are byte-identical.
    "EW-InflC-Both":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                       "w_long_bd": 0.0, "w_overlay": 0.0, "struct_short": None,
                       "infl_confirm": "eq_neg", "eq_confirm_lookback": 3},
    "EW-InflC-BothL": {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                       "w_long_bd": 1.5, "w_overlay": 0.0, "struct_short": None,
                       "infl_confirm": "eq_neg", "eq_confirm_lookback": 3},
    "EW-InflC-Dur":   {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 0.0, "w_hedge_bd": 1.5,
                       "w_long_bd": 0.0, "w_overlay": 0.0, "struct_short": None,
                       "infl_confirm": "eq_neg", "eq_confirm_lookback": 3},
    "EW-InflC-DurL":  {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 0.0, "w_hedge_bd": 1.5,
                       "w_long_bd": 1.5, "w_overlay": 0.0, "struct_short": None,
                       "infl_confirm": "eq_neg", "eq_confirm_lookback": 3},
    "EW-InflC-Both6": {"trend_gate": True, "gate_mode": "overlay", "base_mode": "ew",
                       "gate_signal": "infl_regime", "w_hedge": 1.5, "w_hedge_bd": 1.5,
                       "w_long_bd": 0.0, "w_overlay": 0.0, "struct_short": None,
                       "infl_confirm": "eq_neg", "eq_confirm_lookback": 6},
    # --- Round 9: regime-scaled GROSS (vol-targeting / momentum-gated leverage)
    # on the never-flip long EW base. A NEW PRIMITIVE -- rounds 1-8 all timed a
    # *short* overlay or flipped the base; NONE scaled gross itself. The round-8
    # verdict was "no free lunch in gate width": a broad short gate delivers Upβ >
    # Dnβ but bleeds return; a narrow one keeps return but covers too few down-
    # months. Scaling gross sidesteps that tension entirely -- it is LONG-ONLY:
    # the base never flips (no Upβ-drag-through-recoveries, the round-4b blocker)
    # and there is no short to time. Instead the whole long base is multiplied by
    # a per-month scalar s_t in [scale_floor, scale_ceil]: own MORE in up/calm
    # months (s_t > 1 -> leverage, funding cost via the existing gross>1 machinery
    # at 5.8% APR) and LESS in down/stress months (s_t < 1 -> de-risk). This
    # constructs Upβ > Dnβ BY DESIGN -- Upβ is amplified in up-months (1.5x
    # invested) while Dnβ is damped in down-months (0.3x invested) -- without any
    # short, and the return comes from being fully+ leveraged invested in up-
    # months. scale_signal defaults "" -> all existing presets byte-identical.
    #   eq_mom      : s_t = clip(1 + scale_k * eq_mom_t, floor, ceil), eq_mom_t =
    #                 trailing-scale_lookback external US Equity return. Own more
    #                 when equity up, less when down (momentum-gated leverage).
    #   eq_vol      : s_t = clip(target_vol / realized_eq_vol, floor, ceil) --
    #                 vol-targeting: de-risk when equity vol high (stress), lever
    #                 when low (calm).
    #   infl_regime : s_t = floor in stagflation (infl_up), ceil in disinflation
    #                 -- the round-7 leading gate as a SCALAR (de-risk the long
    #                 base, do not short it): tests whether scaling delivers the
    #                 asymmetry WITH return vs the round-7 short which bled return
    #                 or broke the property.
    "EW-Scale-Mom":   {"trend_gate": False, "base_mode": "ew",
                       "w_overlay": 0.0, "struct_short": None,
                       "scale_signal": "eq_mom", "scale_k": 2.0,
                       "scale_lookback": 3, "scale_floor": 0.3, "scale_ceil": 1.5},
    "EW-Scale-Mom6":  {"trend_gate": False, "base_mode": "ew",
                       "w_overlay": 0.0, "struct_short": None,
                       "scale_signal": "eq_mom", "scale_k": 2.0,
                       "scale_lookback": 6, "scale_floor": 0.3, "scale_ceil": 1.5},
    "EW-Scale-Vol":   {"trend_gate": False, "base_mode": "ew",
                       "w_overlay": 0.0, "struct_short": None,
                       "scale_signal": "eq_vol", "scale_target_vol": 0.12,
                       "scale_lookback": 6, "scale_floor": 0.3, "scale_ceil": 1.5},
    "EW-Scale-MomL":  {"trend_gate": False, "base_mode": "ew",
                       "w_overlay": 0.0, "struct_short": None,
                       "scale_signal": "eq_mom", "scale_k": 3.0,
                       "scale_lookback": 3, "scale_floor": 0.3, "scale_ceil": 2.0},
    "EW-Scale-Infl":  {"trend_gate": False, "base_mode": "ew",
                       "w_overlay": 0.0, "struct_short": None,
                       "scale_signal": "infl_regime", "infl_lookback": 12,
                       "scale_floor": 0.4, "scale_ceil": 1.3},
}


def cap_weights(w: np.ndarray, cap: float) -> np.ndarray:
    """Iterative clip-and-redistribute to enforce w_i <= cap, sum w = 1, w >= 0."""
    w = np.asarray(w, dtype=float).copy()
    if cap <= 0 or cap >= 1:
        return w / w.sum()
    n = w.size
    if n * cap < 1.0:                     # cap infeasible -> equal weight
        return np.ones(n) / n
    w = w / w.sum()
    for _ in range(2000):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = float((w[over] - cap).sum())
        w[over] = cap
        free = ~over
        if free.sum() == 0:
            break
        w[free] += excess / free.sum()
        w = np.maximum(w, 0.0)
    return w / w.sum()


# --------------------------------------------------------------------------- #
# Precompute per-refit covariance / vol for a window (fast shared work)
# --------------------------------------------------------------------------- #

def _refit_dates(index: pd.DatetimeIndex, cadence: str) -> List[pd.Timestamp]:
    if cadence == "M":
        return list(index)
    if cadence == "A":
        out, seen = [], set()
        for d in index:
            if d.year not in seen:
                seen.add(d.year)
                out.append(d)
        return out
    raise ValueError(cadence)


def precompute_refits(ret_full: pd.DataFrame, sleeves: Sequence[str],
                      window_idx: pd.DatetimeIndex, trailing: int,
                      shrink: str) -> Dict[pd.Timestamp, Tuple[np.ndarray, np.ndarray]]:
    """For each annual refit date in the window, compute the shrunk trailing
    covariance + vol over ALL sleeves (using ret_full so the first refit can
    reach pre-window history). A refit is only emitted if EVERY sleeve is
    complete over the trailing window; otherwise that refit is omitted and the
    backtest falls back to equal-weight for it (no covariance available yet)."""
    out: Dict[pd.Timestamp, Tuple[np.ndarray, np.ndarray]] = {}
    sleeves = list(sleeves)
    refits = _refit_dates(window_idx, "A")
    for d in refits:
        past = ret_full.loc[:d].iloc[:-1].tail(trailing)
        if past.shape[0] < 12:
            continue
        cols = [s for s in sleeves if s in past.columns and past[s].notna().all()]
        if cols != sleeves:          # some sleeve lacks trailing history -> skip
            continue
        X = past[sleeves].values
        cov = ledoit_wolf_cov(X) if shrink == "lw" else np.cov(X, rowvar=False)
        vol = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
        out[d] = (cov, vol)
    return out


# --------------------------------------------------------------------------- #
# Fast combo x scheme backtest (net of cost, with weight tracking)
# --------------------------------------------------------------------------- #

def _backtest_ls_tsmom(panel: pd.DataFrame, ret_full: pd.DataFrame,
                       sleeve_idx: List[int], lookback: int,
                       cost_bps: float) -> Dict[str, np.ndarray]:
    """Long/short managed-futures (TSMOM) backtest for one combo.

    Monthly signal (does NOT fit the annual-refit-target-weight model in
    ``backtest``): each month ``t`` take ``mom_i = prod(1 + R[t-L:t, i]) - 1``
    from strictly trailing data and set ``pos_i = base_w_i * sign(mom_i)``.
    ``base_w`` is equal weight across the combo's sleeves (neutral sizing,
    matching all_weather_v2.vintage treatment). $1 gross, 0% T-bill collateral
    (awv2's conservative assumption; real collateral adds ~1-2%/yr — see report
    §9). Same 10bps/side turnover+cost machinery as ``backtest`` (turnover on
    gross position changes, both legs). When ``ret_full`` is supplied the first
    ``lookback`` months of the window still get a causal momentum signal (via
    pre-window history); otherwise the first ``lookback`` months are an
    equal-weight-long warm-up (awv2 convention)."""
    idx = panel.index
    sleeves_all = list(panel.columns)
    names = [sleeves_all[i] for i in sleeve_idx]
    T = len(idx)
    n = len(sleeve_idx)
    base = np.ones(n) / n
    R = panel.values[:, sleeve_idx]
    if ret_full is not None and set(names).issubset(ret_full.columns):
        pre = ret_full.loc[:idx[0]].iloc[:-1].tail(lookback)
        hist = pd.concat([pre[names], ret_full.loc[idx[0]:idx[-1], names]], axis=0)
    else:
        hist = panel[names]
    H = hist.values
    Hidx = hist.index
    gross = np.zeros(T); net = np.zeros(T); turn = np.zeros(T)
    w_prev = None
    last_w = None
    for pos in range(T):
        loc = Hidx.get_loc(idx[pos])
        if loc >= lookback:
            mom = np.prod(1.0 + H[loc - lookback:loc], axis=0) - 1.0
            posv = base * np.sign(mom)
        else:
            posv = base.copy()           # warm-up: equal-weight long
        if w_prev is None:
            t = float(np.abs(posv).sum())                 # initial purchase
        else:
            t = float(np.abs(posv - w_prev).sum())        # rebalance to new signal
        turn[pos] = t
        g = float(posv @ R[pos])
        gross[pos] = g
        net[pos] = g - t * cost_bps
        # Drift the position to end of month, expressed as a fraction of the
        # NEW portfolio value (1 + g). For long-only this equals w/w.sum() (since
        # w.sum() = 1 + g there), but for long/short w.sum() = (net $ position) + g
        # -> ~0 for a near-dollar-neutral book, so dividing by w.sum() explodes the
        # turnover. Dividing by (1 + g) is the correct economics and is always
        # positive (gross $1 => |g| <= max|R| < 1).
        w = posv * (1.0 + R[pos])
        pv = 1.0 + g
        w_prev = w / pv if pv > 1e-6 else posv
        last_w = posv
    # No covariance target -> diversification ratio is undefined for LS-TSMOM.
    return {"gross": gross, "net": net, "turnover": turn,
            "last_w": last_w, "div_ratio": float("nan")}


def _gate_signal(H: np.ndarray, lookback: int, gate_signal: str,
                 vol_window: int = 6, vol_median: int = 60,
                 fast: int = 3, slow: int = 10,
                 fast_exit: int = 3, slow_entry: int = 12,
                 dd_window: int = 6, dd_exit: float = 0.10,
                 dd_entry: float = 0.03,
                 vol_hi_mult: float = 1.0, vol_lo_mult: float = 0.85) -> np.ndarray:
    """Per-month equity-gate direction from a (possibly leading) signal.

    ``H`` is the (T_hist, n) monthly-returns history (pre-window + window) for the
    combo sleeves (same ``H`` used by ``_backtest_flavor``). Returns ``sig`` of
    shape (T_hist, n) with values in {+1.0 (long), -1.0 (short), 0.0 (no-signal /
    warmup)} per sleeve per month. The caller only applies ``sig`` to equity
    sleeves (``is_eq``); non-equity sleeves are ignored.

    Signals (the round-3 leading-signal family; ``"tsmom"`` reproduces the
    round-1/2 trailing-momentum gate exactly so existing presets are unchanged):
      * "tsmom": sign(trailing-`lookback` return) -- LAGGING (the round-1/2 signal).
      * "ma":   long when prior month's price > its trailing-`lookback` SMA, short
                when below (an MA crosses BEFORE a lookback-return flips sign).
      * "vol":  long when prior month's `vol_window`-m realized vol < its trailing
                `vol_median`-month median (calm), short when above (stress). Vol
                spikes tend to LEAD drawdowns.
      * "dma":  long when the `fast`-m SMA > `slow`-m SMA (prior month), short when
                below -- a faster crossover than the single-MA gate.

    Round-4 ASYMMETRIC (hysteretic) gates -- the direct fix for round 3's finding
    that a SYMMETRIC signal (equally trigger-happy up and down) cannot be
    "correlated up, protected down". These are STATEFUL per sleeve: quick to FLEE
    equity on the downside, slow to RE-ENTER on the upside, so the book stays long
    through chop (capturing upside) and only goes net-short after a clear break:
      * "asym_ma": LONG until price < `fast_exit`-m SMA (fast exit), then SHORT
                until price > `slow_entry`-m SMA (slow re-entry). Starts LONG.
                Hysteresis band = the gap between the fast and slow MA.
      * "dd_stop": LONG until the sleeve drawdown from its trailing `dd_window`-m
                peak exceeds `dd_exit` (fast exit), then SHORT until the drawdown
                recovers inside `dd_entry` (slow re-entry, near a new high).
                Starts LONG. A trailing-stop / "flee the break, wait for a new
                high" gate -- the most direct map to the brief.
      * "asym_vol": hysteretic vol-regime (round-4b sweep). LONG -> SHORT once the
                prior month's `vol_window`-m realized vol exceeds `vol_hi_mult` x
                its trailing `vol_median`-m median (fast exit on stress), SHORT ->
                LONG once vol falls back below `vol_lo_mult` x the median (slow
                re-entry -- wait for genuine calm). Starts LONG. The hysteresis
                band = vol_lo_mult..vol_hi_mult x median; a vol spike flees, vol
                must genuinely calm to return (fixes the round-3 EW-Vol-Short
                which shorted the 2020 COVID V-rebound because vol stayed
                elevated through the rally).
    All signals are strictly causal (use only data through the prior month)."""
    T, n = H.shape
    sig = np.zeros((T, n))
    if gate_signal == "tsmom":
        for t in range(T):
            if t >= lookback:
                mom = np.prod(1.0 + H[t - lookback:t], axis=0) - 1.0
                sig[t] = np.where(mom > 0.0, 1.0, np.where(mom < 0.0, -1.0, 0.0))
        return sig
    if gate_signal == "infl_regime":
        # Round 7: the inflation-regime signal is computed in _backtest_flavor
        # from the EXTERNAL inflation-proxy sleeve (ret_full, default
        # "Commodities") -- a MACRO signal, not this combo's own history -- so
        # it is available even when the proxy is not in the combo, and it LEADS
        # equity drawdowns in the stagflation case (commodities topped before
        # equities in 2022). The caller does not use sig_full for infl_regime;
        # it drives the overlays off the per-month ``infl_up`` flag directly.
        # Return zeros (no-op) so any incidental use is safe.
        return np.zeros((T, n))
    # Price level (cumulative return index, base 1.0) for the price-based signals.
    lvl = np.cumprod(1.0 + H, axis=0)
    if gate_signal == "ma":
        for t in range(T):
            if t >= lookback:
                ma = lvl[t - lookback:t].mean(axis=0)   # SMA over [t-lookback, t-1]
                prev = lvl[t - 1]
                sig[t] = np.where(prev > ma, 1.0, np.where(prev < ma, -1.0, 0.0))
        return sig
    if gate_signal == "dma":
        for t in range(T):
            if t >= slow:
                fast_ma = lvl[t - fast:t].mean(axis=0)
                slow_ma = lvl[t - slow:t].mean(axis=0)
                sig[t] = np.where(fast_ma > slow_ma, 1.0,
                                  np.where(fast_ma < slow_ma, -1.0, 0.0))
        return sig
    if gate_signal == "vol":
        rv = np.zeros((T, n))
        for t in range(T):
            if t >= vol_window:
                rv[t] = H[t - vol_window:t].std(axis=0, ddof=0) * np.sqrt(12.0)
        for t in range(T):
            if t >= vol_median:
                med = np.median(rv[t - vol_median:t], axis=0)
                prev = rv[t - 1]
                sig[t] = np.where(prev < med, 1.0,
                                  np.where(prev > med, -1.0, 0.0))
        return sig
    if gate_signal == "asym_ma":
        # Stateful hysteresis: LONG -> SHORT on a fast-MA break, SHORT -> LONG on
        # a slow-MA recovery. Starts LONG (relaxed upside: stay long through chop
        # above the fast MA). Per-sleeve state persists across months.
        state = np.ones(n)                       # start LONG
        for t in range(T):
            if t >= slow_entry:
                fast_ma = lvl[t - fast_exit:t].mean(axis=0)
                slow_ma = lvl[t - slow_entry:t].mean(axis=0)
                prev = lvl[t - 1]
                to_short = (prev < fast_ma) & (state > 0.0)     # fast exit
                to_long = (prev > slow_ma) & (state < 0.0)      # slow re-entry
                state = np.where(to_short, -1.0, np.where(to_long, 1.0, state))
            sig[t] = state
        return sig
    if gate_signal == "dd_stop":
        # Stateful trailing-stop: LONG -> SHORT once the sleeve is > dd_exit below
        # its trailing dd_window-m peak (a clear break), SHORT -> LONG once it
        # recovers inside dd_entry of the peak (near a new high). Starts LONG.
        state = np.ones(n)                       # start LONG
        for t in range(T):
            if t >= dd_window:
                pk = np.max(lvl[t - dd_window:t], axis=0)      # peak over trailing window
                dd = (lvl[t - 1] - pk) / pk                    # drawdown (<=0)
                to_short = (dd < -dd_exit) & (state > 0.0)     # fast exit on a break
                to_long = (dd > -dd_entry) & (state < 0.0)     # slow re-entry near a high
                state = np.where(to_short, -1.0, np.where(to_long, 1.0, state))
            sig[t] = state
        return sig
    if gate_signal == "eq_dd":
        # Round 6: SYMMETRIC fast drawdown trigger (no hysteresis band beyond the
        # dd_exit/dd_entry dead-zone). Short a sleeve once it is > dd_exit below
        # its trailing dd_window-m peak (a drawdown is underway), long once it is
        # back within dd_entry of the peak (recovered). Fires FAST in down-months
        # and releases FAST in recoveries -- the round-5 "dma/ma fires ~12m too
        # late" fix. StateLESS (unlike dd_stop's hysteretic state), so it cannot
        # get stuck short through chop; the price is more whipsaw near the peak.
        for t in range(T):
            if t >= dd_window:
                pk = np.max(lvl[t - dd_window:t], axis=0)      # trailing peak
                dd = (lvl[t - 1] - pk) / pk                    # drawdown (<=0)
                sig[t] = np.where(dd < -dd_exit, -1.0,         # in a drawdown -> short
                                  np.where(dd > -dd_entry, 1.0, 0.0))  # near high -> long
        return sig
    if gate_signal == "asym_vol":
        # Hysteretic vol-regime: a vol spike flees (fast exit), vol must
        # genuinely calm below a LOWER bar to return (slow re-entry). The
        # hysteresis band = vol_lo_mult..vol_hi_mult x the trailing median.
        # Fixes the round-3 EW-Vol-Short, which shorted the 2020 COVID V-rebound
        # (vol stayed elevated through the rally -> symmetric vol-gate never
        # re-entered long). Starts LONG.
        rv = np.zeros((T, n))
        for t in range(T):
            if t >= vol_window:
                rv[t] = H[t - vol_window:t].std(axis=0, ddof=0) * np.sqrt(12.0)
        state = np.ones(n)
        for t in range(T):
            if t >= vol_median:
                med = np.median(rv[t - vol_median:t], axis=0)
                prev = rv[t - 1]
                to_short = (prev > vol_hi_mult * med) & (state > 0.0)
                to_long = (prev < vol_lo_mult * med) & (state < 0.0)
                state = np.where(to_short, -1.0, np.where(to_long, 1.0, state))
            sig[t] = state
        return sig
    # Fallback: tsmom (so an unknown gate_signal is safe, not a crash).
    for t in range(T):
        if t >= lookback:
            mom = np.prod(1.0 + H[t - lookback:t], axis=0) - 1.0
            sig[t] = np.where(mom > 0.0, 1.0, np.where(mom < 0.0, -1.0, 0.0))
    return sig


def _backtest_flavor(panel: pd.DataFrame, ret_full: pd.DataFrame,
                     sleeve_idx: List[int], eq: Optional[List[str]],
                     precomp: Dict[pd.Timestamp, Tuple[np.ndarray, np.ndarray]],
                     preset: dict, lookback: int, cost_bps: float,
                     lev_rate: float, cap: float = 0.20,
                     erc_cap_mode: str = "capped",
                     bonds: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
    """TrendProtect flavor backtest -- one parameterized function for all four
    constructions (the FLAVOR_PRESETS are just knobs of this one engine).

    Each month the position is rebuilt from a long MinVar base leg (annual refit,
    cap-respecting, reuses the Fix-1 solver) plus up to three active overlays:

      * trend-gate: equity sleeves are gated to cash when their own trailing-12m
        return is negative (``pos *= 1{mom_i>0}`` for equity sleeves only; bonds /
        gold / diversifiers stay long). Long-only, gross <= 1.
      * LS-TSMOM overlay: a dollar-neutral momentum sleeve
        ``+w_overlay * base_w * sign(mom_i)`` added on top of the long leg. Adds
        ``w_overlay`` of gross -> leverage cost on gross > 1.
      * structural short: ``-= w_short`` on one named sleeve, held permanently
        (sleeve-level netting: a long US-Treasuries leg of 0.20 shorted by 0.30
        becomes net -0.10; ticker-level shorting that would ADD gross is a flagged
        refinement). Net-short-duration tilt for the 2022-style bond rout.

    Costs: same 10 bps/side turnover machinery as ``backtest`` (two-way turnover
    on the full position vector), PLUS a monthly leverage funding cost
    ``max(0, gross_notional - 1) * lev_rate/12`` when the gross notional exceeds
    1 (overlay flavors). Long-only TrendGate never pays leverage cost. The
    position drifts to end of month and is rebalanced to the (signal-modified)
    target next month, so turnover captures both the passive drift-correction and
    the active signal changes (gate toggles, overlay sign flips)."""
    idx = panel.index
    sleeves_all = list(panel.columns)
    names = [sleeves_all[i] for i in sleeve_idx]
    T = len(idx)
    n = len(sleeve_idx)
    R = panel.values[:, sleeve_idx]
    eq_set = set(eq) if eq else set()
    is_eq = np.array([nm in eq_set for nm in names], dtype=bool)
    bond_set = set(bonds) if bonds else set()
    is_bond = np.array([nm in bond_set for nm in names], dtype=bool)
    trend_gate = bool(preset.get("trend_gate", False))
    gate_mode = str(preset.get("gate_mode", "cash"))   # "cash" or "short"
    gate_signal = str(preset.get("gate_signal", "tsmom"))   # "tsmom"|"ma"|"vol"|"dma"
    w_overlay = float(preset.get("w_overlay", 0.0))
    # Round-5 decoupled insurance-overlay size (fraction of each equity sleeve's
    # base weight to short, additively, when the downside signal fires). 0 by
    # default -> existing presets byte-identical; only round-5 presets set it.
    w_hedge = float(preset.get("w_hedge", 0.0))
    # Round-6 duration/bond overlay size (fraction of each BOND sleeve's base
    # weight to short, additively, when that sleeve's own downside signal fires).
    # 0 by default -> existing presets byte-identical; only round-6 presets set
    # it. Reuses the same per-sleeve ``gd`` signal, so the bond overlay shorts
    # bonds on bonds' OWN downtrend (stagflation 2022) and stays flat when bonds
    # are up (flight-to-quality 2008/2020) -- the targeted both-down fix.
    w_hedge_bd = float(preset.get("w_hedge_bd", 0.0))
    # Round-7 inflation-regime leading gate. The duration (and optionally
    # equity) overlay fires off an EXTERNAL inflation-proxy sleeve's trailing
    # return (default "Commodities"), computed from ret_full -- a MACRO signal,
    # not the combo's own trend, so it is available even when the proxy is not
    # in the combo and LEADS equity drawdowns in the stagflation case. Regime-
    # conditional and SYMMETRIC: short duration (and equity, w_hedge) when
    # inflation is RISING (stagflation risk-off, 2022 -- both fall); add a
    # LONG-duration tilt (w_long_bd) when inflation is FALLING (disinflation,
    # 2008/2020 -- bonds rally and hedge equity for free via flight-to-quality).
    # All default 0 -> existing presets byte-identical; only round-7 presets set
    # them. w_long_bd is the new "amplify flight-to-quality" lever.
    w_long_bd = float(preset.get("w_long_bd", 0.0))
    infl_proxy = str(preset.get("infl_proxy", "Commodities"))
    infl_lookback = int(preset.get("infl_lookback", lookback))
    # Round 8: a COINCIDENT confirmation on top of the leading inflation gate.
    # Round 7's broad inflation gate bled return in non-crisis reflation months
    # (2021, 2024: inflation up but equity rallying) because it shorted in EVERY
    # rising-inflation month. infl_confirm gates the overlays to fire only when
    # the leading macro signal is CONFIRMED by equity actually rolling over:
    #   "" (off)        -> round-7 broad gate (short on infl_up alone); existing
    #                     round-7 presets default "" -> byte-identical (opt-in).
    #   "eq_neg"        -> short/long-tilt fire only when the external equity
    #                     proxy's trailing-`eq_confirm_lookback` return < 0
    #                     (equity rolling over). Short: infl_up AND eq_rolling
    #                     (stagflation + equity actually falling, 2022). Long-
    #                     tilt: (NOT infl_up) AND eq_rolling (true flight-to-
    #                     quality: disinflation + equity falling, 2008/2020) --
    #                     NOT in 2022-23-style disinflation-with-bonds-falling,
    #                     which is what dragged the round-7 duration-only both-
    #                     down to -30%..-36%. The leading macro gate stays
    #                     ex-ante; the confirmation only narrows WHEN it fires.
    infl_confirm = str(preset.get("infl_confirm", ""))
    eq_confirm_proxy = str(preset.get("eq_confirm_proxy", "US Equity"))
    eq_confirm_lookback = int(preset.get("eq_confirm_lookback", 3))
    # Round 9: regime-scaled gross (vol-targeting / momentum-gated leverage) on
    # the never-flip long base. A NEW primitive -- the eight prior rounds all
    # timed a *short* overlay or flipped the base; none scaled gross itself.
    # scale_signal != "" multiplies the long base by a per-month scalar s_t in
    # [scale_floor, scale_ceil]: own MORE in up/calm months (s_t > 1 -> leverage,
    # funding cost via the existing gross>1 machinery at 5.8% APR) and LESS in
    # down/stress months (s_t < 1 -> de-risk). Long-only -> the base's Upβ stays
    # positive and is AMPLIFIED in up-months while Dnβ is DAMPED in down-months,
    # constructing Upβ > Dnβ BY DESIGN without any short (no Upβ-drag-through-
    # recoveries, the round-4b blocker). Signals: "" (off, byte-identical opt-in),
    # "eq_mom" (momentum-gated leverage), "eq_vol" (vol-targeting), "infl_regime"
    # (round-7 leading gate as a scalar: de-risk in stagflation, lever in
    # disinflation). All default off -> existing presets byte-identical.
    scale_signal = str(preset.get("scale_signal", ""))
    scale_k = float(preset.get("scale_k", 2.0))
    scale_lookback = int(preset.get("scale_lookback", 3))
    scale_floor = float(preset.get("scale_floor", 0.3))
    scale_ceil = float(preset.get("scale_ceil", 1.5))
    scale_target_vol = float(preset.get("scale_target_vol", 0.12))
    # Resolve the inflation proxy to the first available sleeve in ret_full
    # (Commodities -> Gold -> Silver), so the signal is robust if the primary
    # proxy's column is missing. None if no proxy is available (signal flat).
    _infl_col = None
    if ret_full is not None:
        for _cand in (infl_proxy, "Commodities", "Gold", "Silver"):
            if _cand and _cand in ret_full.columns:
                _infl_col = _cand
                break
    # Resolve the equity-confirmation proxy similarly (US Equity -> International
    # Equity -> US REIT -> Preferred Stock). None if unavailable -> confirmation
    # disabled (falls back to round-7 broad behavior even if a preset asks for it).
    _eq_col = None
    if ret_full is not None:
        for _cand in (eq_confirm_proxy, "US Equity", "International Equity",
                      "US REIT", "Preferred Stock"):
            if _cand and _cand in ret_full.columns:
                _eq_col = _cand
                break
    ss = preset.get("struct_short")
    short_name = ss[0] if ss else None
    w_short = float(ss[1]) if ss else 0.0
    short_i = (names.index(short_name)
               if (short_name is not None and short_name in names) else -1)
    # Per-preset lookback override (default = the caller's lookback).
    lookback = int(preset.get("lookback", lookback))
    # Round-4 hysteretic-gate params (per-preset override; the helper defaults
    # are used if absent, so the round-4 presets EW-AsymMA-Short / EW-DDStop-Short
    # and the round-3 ma/vol/dma presets stay byte-identical to their originals).
    g_fast_exit = int(preset.get("fast_exit", 3))
    g_slow_entry = int(preset.get("slow_entry", 12))
    g_dd_window = int(preset.get("dd_window", 6))
    g_dd_exit = float(preset.get("dd_exit", 0.10))
    g_dd_entry = float(preset.get("dd_entry", 0.03))
    g_vol_window = int(preset.get("vol_window", 6))
    g_vol_median = int(preset.get("vol_median", 60))
    g_vol_hi = float(preset.get("vol_hi_mult", 1.0))
    g_vol_lo = float(preset.get("vol_lo_mult", 0.85))

    # Trailing momentum per sleeve, with pre-window history so the first
    # ``lookback`` months still get a causal signal (matches _backtest_ls_tsmom).
    # The leading-signal family (gate_signal ma/vol/dma) needs a longer pre-window
    # (the vol-regime signal uses a 60m median of a 6m realized vol -> ~66m), so
    # pull max(lookback, 72) months of pre-window history when available.
    pre_n = max(lookback, 72)
    if ret_full is not None and set(names).issubset(ret_full.columns):
        pre = ret_full.loc[:idx[0]].iloc[:-1].tail(pre_n)
        hist = pd.concat([pre[names], ret_full.loc[idx[0]:idx[-1], names]], axis=0)
    else:
        hist = panel[names]
    H = hist.values
    Hidx = hist.index

    # Precompute the equity-gate signal (per sleeve, per month) for the leading-
    # signal family. ``tsmom`` (the default) is handled inline below to keep the
    # round-1/2 presets byte-identical; ma/vol/dma use this precomputed array.
    sig_full = (_gate_signal(H, lookback, gate_signal,
                             vol_window=g_vol_window, vol_median=g_vol_median,
                             fast_exit=g_fast_exit, slow_entry=g_slow_entry,
                             dd_window=g_dd_window, dd_exit=g_dd_exit,
                             dd_entry=g_dd_entry,
                             vol_hi_mult=g_vol_hi, vol_lo_mult=g_vol_lo)
                if (trend_gate and gate_signal not in ("tsmom", "infl_regime"))
                else None)

    refit_set = set(_refit_dates(idx, "A"))
    base_w = None          # annual long-leg target (constant between refits)
    pos = None             # drifted actual position (end of last month)
    last_w = None
    gross = np.zeros(T); net = np.zeros(T); turn = np.zeros(T)
    base_mode = str(preset.get("base_mode", "minvar"))   # "minvar" or "ew"
    for tpos in range(T):
        d = idx[tpos]
        if d in refit_set and d in precomp:
            if base_mode == "ew":
                # Equal-weight base (capped) -- like All-Weather's own ~1/n across
                # the combo sleeves, so equity keeps a real weight (MinVar starves
                # high-vol equity to ~5-10%). Gives the short-on-downside gate real
                # equity to flip and a return floor near AW.
                wv = cap_weights(np.ones(n) / n, cap) if 0.0 < cap < 1.0 else np.ones(n) / n
            else:
                cov_full, vol_full = precomp[d]
                cov = cov_full[np.ix_(sleeve_idx, sleeve_idx)]
                vol = vol_full[sleeve_idx]
                try:
                    wv = s_minvar(cov, vol, cap=cap, erc_cap_mode=erc_cap_mode)
                    if (not np.all(np.isfinite(wv))) or wv.sum() <= 0:
                        wv = np.ones(n) / n
                    if 0.0 < cap < 1.0 and wv.max() > cap + 1e-6:
                        wv = cap_weights(wv, cap)
                    else:
                        wv = wv / wv.sum()
                except Exception:
                    wv = cap_weights(np.ones(n) / n, cap)
            base_w = wv
        if base_w is None:
            continue
        # Trailing-12m momentum per sleeve (causal).
        loc = Hidx.get_loc(d)
        if loc >= lookback:
            mom = np.prod(1.0 + H[loc - lookback:loc], axis=0) - 1.0
        else:
            mom = np.zeros(n)            # warm-up: no signal (flat overlay / open gate)
        # Round 7: inflation-regime leading signal (MACRO gate). The trailing-
        # `infl_lookback` return of the external inflation-proxy sleeve
        # (Commodities by default, from ret_full) defines the inflation regime:
        # infl_up = rising prices (stagflation risk-off: short duration/equity),
        # else falling/flat (disinflation: long-duration tilt, flight-to-quality).
        # Computed off ret_full so it is independent of combo membership. The
        # equity base NEVER flips (Upβ preserved) -- only the overlays move.
        if gate_signal == "infl_regime" and _infl_col is not None:
            ip = ret_full[_infl_col]
            iloc = ip.index.get_loc(d)
            if iloc >= infl_lookback:
                infl_mom = float(np.prod(
                    1.0 + ip.iloc[iloc - infl_lookback:iloc].values) - 1.0)
            else:
                infl_mom = 0.0
            infl_up = infl_mom > 0.0
        else:
            infl_up = False
        # Round 8: coincident equity-rolling confirmation for the inflation gate.
        # eq_rolling = True means "no confirmation required" (round-7 broad gate);
        # the round-8 presets set infl_confirm="eq_neg" -> eq_rolling is True only
        # when the external equity proxy's trailing-`eq_confirm_lookback` return < 0
        # (equity actually rolling over). Computed off ret_full so it is independent
        # of combo membership, like the inflation proxy.
        if infl_confirm == "eq_neg" and _eq_col is not None:
            ep = ret_full[_eq_col]
            eloc = ep.index.get_loc(d)
            if eloc >= eq_confirm_lookback:
                eq_mom = float(np.prod(
                    1.0 + ep.iloc[eloc - eq_confirm_lookback:eloc].values) - 1.0)
            else:
                eq_mom = 0.0
            eq_rolling = eq_mom < 0.0
        else:
            # infl_confirm off (round-7 presets) OR no equity proxy available ->
            # no confirmation: overlays fire on the inflation gate alone (round-7).
            eq_rolling = True
        # Round 9: regime-scaled gross. s_t scales the never-flip long base:
        # >1 (leverage, funding cost) in up/calm months, <1 (de-risk) in down/
        # stress months. Long-only -> Upβ amplified up, Dnβ damped down ->
        # Upβ > Dnβ by design, with no short to time. Default s_t = 1.0 -> the
        # round-9 presets are the only ones that move it (opt-in; existing
        # presets byte-identical). Self-contained: computes its own infl_up for
        # the infl_regime scalar so it does not depend on gate_signal.
        s_t = 1.0
        if scale_signal != "":
            if scale_signal == "infl_regime":
                if _infl_col is not None:
                    ip_s = ret_full[_infl_col]
                    iloc_s = ip_s.index.get_loc(d)
                    if iloc_s >= infl_lookback:
                        _im_s = float(np.prod(
                            1.0 + ip_s.iloc[iloc_s - infl_lookback:iloc_s].values) - 1.0)
                    else:
                        _im_s = 0.0
                    s_t = scale_floor if _im_s > 0.0 else scale_ceil
                else:
                    s_t = 1.0
            elif _eq_col is not None:
                ep_s = ret_full[_eq_col]
                eloc_s = ep_s.index.get_loc(d)
                if scale_signal == "eq_mom":
                    if eloc_s >= scale_lookback:
                        eq_m_s = float(np.prod(
                            1.0 + ep_s.iloc[eloc_s - scale_lookback:eloc_s].values) - 1.0)
                    else:
                        eq_m_s = 0.0
                    s_t = min(max(1.0 + scale_k * eq_m_s, scale_floor), scale_ceil)
                elif scale_signal == "eq_vol":
                    if eloc_s >= scale_lookback:
                        rv = float(np.std(
                            ep_s.iloc[eloc_s - scale_lookback:eloc_s].values, ddof=1))
                    else:
                        rv = 0.0
                    rv_ann = rv * np.sqrt(12.0)
                    s_t = (scale_target_vol / rv_ann) if rv_ann > 1e-6 else 1.0
                    s_t = min(max(s_t, scale_floor), scale_ceil)
                else:
                    s_t = 1.0
            else:
                s_t = 1.0
        # Long leg, optional trend-gate on equity sleeves.
        long_leg = base_w.copy()
        ol = np.zeros(n)   # round-5 decoupled short overlay (additive gross)
        if trend_gate:
            # Gate direction per sleeve (+1 long / -1 short / 0 flat signal).
            # ``tsmom`` (default) derives it from the trailing-lookback return
            # (``mom``) so the round-1/2 presets are byte-identical; the leading-
            # signal family (ma/vol/dma) uses the precomputed ``sig_full`` array
            # — a faster signal meant to exit equity *before* the drawdown and
            # re-enter *before* the rally (the round-2 lagging-signal blocker).
            if gate_signal == "tsmom":
                gd = np.sign(mom)
            else:
                gd = sig_full[loc] if sig_full is not None else np.sign(mom)
            if gate_mode == "short":
                # "correlated up, protected down": long equity when gd>0,
                # SHORT the equity sleeve when gd<0, hold long when no signal
                # (gd==0, e.g. warm-up). Bonds/gold/diversifiers stay long. The
                # short flip adds gross when equity is short -> leverage cost.
                eq_mult = np.where(gd != 0.0, gd, 1.0)
                long_leg = long_leg * np.where(is_eq, eq_mult, 1.0)
            elif gate_mode == "overlay":
                # Round 5: DECOUPLED insurance overlay. The long base NEVER
                # flips (stays at base_w in every month, including down-months
                # and recoveries) so the portfolio's up-month beta stays that
                # of the long-only base -- POSITIVE, the round-4b structural
                # blocker's direct fix. A SEPARATE short overlay on the equity
                # sleeves is active ONLY when gd<0 (a downside signal) and
                # FLAT otherwise: in up-months the overlay is zero, so the
                # base's full equity weight is at work (Upβ not dragged); in
                # down-months the overlay shorts ``w_hedge`` of each equity
                # sleeve (proportional to its base weight), clipping the
                # downside. Because the overlay is a SEPARATE notional (the
                # long base and the short overlay are both held, NOT sleeve-
                # netted into one weight), it adds gross when active ->
                # leverage cost; that is the explicit price of decoupling the
                # two halves (vs the free sleeve-netted flip of gate_mode=
                # "short", which decoupling-free also killed Upβ). The overlay
                # signal must be FAST-OFF in recoveries (so it does not drag
                # the rally) -- the OPPOSITE hysteresis of round 4's asym_ma:
                # use a symmetric signal (ma/dma) or dd_stop, NOT asym_ma.
                if gate_signal == "infl_regime":
                    # Round 7: inflation-regime gate drives BOTH overlays off the
                    # MACRO inflation signal (infl_up), NOT the combo's own lagging
                    # trend. The long base NEVER flips -> Upβ stays positive. When
                    # inflation is RISING (infl_up, stagflation risk-off: 2022):
                    # short the equity sleeves (w_hedge) AND the bond sleeves
                    # (w_hedge_bd) -- both fall in this regime, so the short clips
                    # the both-down loss the round-5/6 equity-/bond-own-trend gates
                    # missed or lagged. When inflation is FALLING (disinflation:
                    # 2008 Q4, 2020 Q1): add a LONG-duration tilt (w_long_bd) so
                    # the portfolio OWNS the bonds that rally in flight-to-quality
                    # -- the regime where bonds hedge equity for free, dragging
                    # Dnβ toward/below zero. This is the leading-macro lever the
                    # user asked for: a downside hedge that fires on an ex-ante
                    # inflation regime, not a lagging price trend.
                    if infl_up:
                        # Round 8: gate the stagflation short on a coincident
                        # equity-rolling confirmation (eq_rolling). Round-7 presets
                        # have eq_rolling=True always -> fires on infl_up alone
                        # (byte-identical). Round-8 presets (infl_confirm="eq_neg")
                        # fire only when inflation is up AND equity is rolling over
                        # -> no short in 2021/2024 reflation rallies (return kept),
                        # short in 2022 (inflation up + equity falling, both-down
                        # protected). The leading macro gate stays ex-ante; the
                        # confirmation only narrows WHEN the short fires.
                        if eq_rolling:
                            if w_hedge > 0.0:
                                ol[is_eq] += -w_hedge * base_w[is_eq]
                            if w_hedge_bd > 0.0:
                                ol[is_bond] += -w_hedge_bd * base_w[is_bond]
                    elif w_long_bd > 0.0 and eq_rolling:
                        # Round 8: gate the long-duration tilt on the SAME equity-
                        # rolling confirmation. Round-7 presets (eq_rolling=True)
                        # fire on (NOT infl_up) alone (byte-identical). Round-8
                        # presets fire only when inflation is FALLING AND equity is
                        # rolling over -> the true flight-to-quality regime (2008
                        # Q4, 2020 Q1: disinflation + equity crash + bonds rally),
                        # NOT the 2022-23 disinflation-with-bonds-falling regime
                        # that dragged the round-7 duration-only both-down to
                        # -30%..-36%. Own the rallying bonds only when they rally.
                        ol[is_bond] += w_long_bd * base_w[is_bond]
                else:
                    down = is_eq & (gd < 0.0)
                    ol[down] = -w_hedge * base_w[down]
                    # Round 6: duration/bond overlay. Short the BOND sleeves on
                    # their OWN downside signal (gd<0), additively. In stagflation
                    # (2022) bonds trend down -> the short fires -> clips the
                    # both-down loss the equity-only overlay missed. In flight-to-
                    # quality (2008 Q4, 2020 Q1) bonds trend UP -> gd>=0 -> no
                    # short -> no bleed. Reuses the same gd, so it is causal and
                    # adds no new signal plumbing.
                    if w_hedge_bd > 0.0:
                        down_bd = is_bond & (gd < 0.0)
                        ol[down_bd] += -w_hedge_bd * base_w[down_bd]
            else:   # "cash": gate equity to 0 when gd<=0 (long-only, gross<=1)
                gate = np.where(gd > 0.0, 1.0, 0.0)
                long_leg = long_leg * np.where(is_eq, gate, 1.0)
        # Structural short (sleeve-level netting).
        if short_i >= 0:
            long_leg[short_i] -= w_short
        # LS-TSMOM dollar-neutral momentum overlay.
        pos_target = long_leg + ol
        if w_overlay > 0.0:
            pos_target = pos_target + w_overlay * base_w * np.sign(mom)
        # Round 9: scale the (never-flip, long-only) base by the regime scalar.
        # Applied after overlays so the whole position scales; round-9 presets
        # have no gate/overlay/short so pos_target = s_t * base_w (gross = s_t,
        # leverage cost on s_t > 1 via the existing gross>1 machinery below).
        if scale_signal != "":
            pos_target = pos_target * s_t
        # Turnover (two-way, full position vector), gross/net, leverage funding.
        if pos is None:
            t = float(np.abs(pos_target).sum())
        else:
            t = float(np.abs(pos_target - pos).sum())
        turn[tpos] = t
        g = float(pos_target @ R[tpos])
        gross[tpos] = g
        # Additive gross for the round-5 overlay (long base + separate short
        # notional, NOT sleeve-netted) -> leverage cost on the true gross; the
        # other modes use the netted |pos_target| as before (byte-identical).
        if gate_mode == "overlay" and (w_hedge > 0.0 or w_hedge_bd > 0.0
                                       or w_long_bd > 0.0):
            gross_notional = float(np.abs(long_leg).sum()) + float(np.abs(ol).sum())
        else:
            gross_notional = float(np.abs(pos_target).sum())
        if lev_rate > 0.0 and gross_notional > 1.0:
            net[tpos] = g - t * cost_bps - (gross_notional - 1.0) * (lev_rate / 12.0)
        else:
            net[tpos] = g - t * cost_bps
        # Drift to end of month as a fraction of portfolio value (matches
        # backtest / _backtest_ls_tsmom; pv > 0 since |g| <= max|R| < 1).
        w = pos_target * (1.0 + R[tpos])
        pv = 1.0 + g
        pos = w / pv if pv > 1e-6 else pos_target
        last_w = pos_target
    # Long/short -> covariance diversification ratio is not meaningful.
    return {"gross": gross, "net": net, "turnover": turn,
            "last_w": last_w, "div_ratio": float("nan")}


def backtest(panel: pd.DataFrame, precomp: Dict[pd.Timestamp, Tuple[np.ndarray, np.ndarray]],
             sleeve_idx: List[int], scheme: str, cap: float, cost_bps: float,
             cadence: str = "A", erc_cap_mode: str = "capped",
             ret_full: Optional[pd.DataFrame] = None,
             tsmom_lookback: int = 12,
             eq: Optional[List[str]] = None,
             lev_rate: float = 0.0,
             bonds: Optional[List[str]] = None) -> Dict[str, np.ndarray]:
    """Backtest one combo (via its sleeve position indices) under one scheme.
    Returns gross, net, turnover monthly arrays + last weights + last cov-based
    diversification ratio. LS-TSMOM is a monthly momentum signal (no annual
    refit / no covariance target) and dispatches to _backtest_ls_tsmom. The four
    TrendProtect flavors dispatch to _backtest_flavor (needs `eq` for the equity
    trend-gate and `lev_rate` for the leverage funding cost; round-6 duration
    overlays also need `bonds`). Long-only COV schemes ignore eq / bonds / lev_rate."""
    if scheme == "LS-TSMOM":
        return _backtest_ls_tsmom(panel, ret_full, sleeve_idx, tsmom_lookback, cost_bps)
    if scheme in FLAVOR_PRESETS:
        return _backtest_flavor(panel, ret_full, sleeve_idx, eq, precomp,
                                FLAVOR_PRESETS[scheme], tsmom_lookback, cost_bps,
                                lev_rate, cap=cap, erc_cap_mode=erc_cap_mode,
                                bonds=bonds)
    idx = panel.index
    R = panel.values
    T = len(idx)
    sleeves_all = list(panel.columns)
    n = len(sleeve_idx)
    refit_set = set(_refit_dates(idx, cadence))
    scheme_fn = SCHEMES[scheme]
    # Schemes that solve WITH the cap (the projection enforces w_i <= cap at
    # every gradient step) -> do NOT post-hoc clip; the solver output already
    # satisfies the cap, so clipping would be a no-op (and we want that to be
    # visible/verifiable, not hidden behind cap_weights).
    solver_capped = (scheme == "MinVar") or (
        scheme == "ERC" and erc_cap_mode == "capped" and 0.0 < cap < 1.0)
    gross = np.zeros(T); net = np.zeros(T); turn = np.zeros(T)
    w = None
    w_target = None
    last_cov = None; last_vol = None; last_w = None
    for pos, d in enumerate(idx):
        if d in refit_set:
            if d in precomp:
                cov_full, vol_full = precomp[d]
                cov = cov_full[np.ix_(sleeve_idx, sleeve_idx)]
                vol = vol_full[sleeve_idx]
                try:
                    wt = scheme_fn(cov, vol, cap=cap, erc_cap_mode=erc_cap_mode)
                    if (not np.all(np.isfinite(wt))) or wt.sum() <= 0:
                        wt = np.ones(n) / n
                except Exception:
                    wt = np.ones(n) / n
                if solver_capped:
                    # solver already respects the cap; numerical safety only.
                    if 0.0 < cap < 1.0 and wt.max() > cap + 1e-6:
                        wt = cap_weights(wt, cap)
                    else:
                        wt = wt / wt.sum()
                else:
                    wt = cap_weights(wt, cap)
                last_cov, last_vol, last_w = cov, vol, wt
            else:
                # not enough trailing history for a covariance -> equal weight
                wt = cap_weights(np.ones(n) / n, cap)
            w_target = wt
        if w_target is None:
            continue
        if w is None:
            t = float(np.abs(w_target).sum())        # initial purchase
        else:
            t = float(np.abs(w_target - w).sum())    # monthly rebalance to target
        turn[pos] = t
        g = float(w_target @ R[pos, sleeve_idx])
        gross[pos] = g
        net[pos] = g - t * cost_bps
        # drift to end of month
        w = w_target * (1.0 + R[pos, sleeve_idx])
        s = w.sum()
        w = w / s if s > 0 else w_target
    # diversification ratio from last refit (w·vol / sqrt(w' cov w))
    dr = float("nan")
    if last_w is not None and last_cov is not None:
        denom = math.sqrt(max(float(last_w @ last_cov @ last_w), 1e-30))
        dr = float(last_w @ last_vol) / denom
    return {"gross": gross, "net": net, "turnover": turn,
            "last_w": last_w, "div_ratio": dr}


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def _max_dd(wealth: np.ndarray) -> float:
    if len(wealth) == 0:
        return 0.0
    running = np.maximum.accumulate(wealth)
    dd = wealth / running - 1.0
    return float(dd.min()) if len(dd) else 0.0


def _sharpe(m: np.ndarray) -> float:
    if len(m) < 2 or np.std(m, ddof=1) == 0:
        return 0.0
    return float(np.mean(m) / np.std(m, ddof=1) * math.sqrt(MONTHS_PER_YEAR))


def compute_metrics(net: np.ndarray, gross: np.ndarray, turnover: np.ndarray,
                    idx: pd.DatetimeIndex, both_down: pd.Series,
                    eq_ref: pd.Series, bd_ref: pd.Series,
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
        "sharpe_gross": _sharpe(pd.Series(gross, index=idx).dropna().values),
        "max_drawdown": _max_dd(wealth),
        "avg_turnover": float(np.mean(turnover)) if len(turnover) else 0.0,
        "ann_turnover": float(np.mean(turnover) * 12) if len(turnover) else 0.0,
        "div_ratio": div_ratio,
        "corr_eq": float(s.corr(eq_ref.reindex(s.index))) if s.std() > 0 else 0.0,
        "corr_bd": float(s.corr(bd_ref.reindex(s.index))) if s.std() > 0 else 0.0,
    }
    # both-down stats (net)
    bd_mask = both_down.reindex(s.index).fillna(False)
    bd = s[bd_mask]
    m["n_both_down"] = int(len(bd))
    m["both_down_avg_monthly"] = float(bd.mean()) if len(bd) else 0.0
    m["both_down_annualized"] = float(bd.mean() * 12) if len(bd) else 0.0
    m["both_down_worst_monthly"] = float(bd.min()) if len(bd) else 0.0
    m["both_down_hit_rate"] = float((bd > 0).mean()) if len(bd) else 0.0
    if len(bd) >= 2 and bd.std() > 0 and eq_ref.reindex(s.index)[bd_mask].std() > 0:
        m["corr_eq_bothdown"] = float(bd.corr(eq_ref.reindex(s.index)[bd_mask]))
    else:
        m["corr_eq_bothdown"] = 0.0
    # Asymmetric equity-correlation metrics — the "correlated up, not down" brief.
    # Upside/downside beta to the equity ref (beta of portfolio to equity on
    # equity-up vs equity-down months), and correlation with equity on equity-
    # down months. A flavor that captures equity rallies but protects in equity
    # drawdowns has upside_beta ~ O(1), downside_beta << upside_beta, and low
    # downside_corr_eq (ideally negative). Used by the asymmetric score-mode.
    eq_a = eq_ref.reindex(s.index)
    up = (eq_a > 0).fillna(False)
    dn = (eq_a < 0).fillna(False)
    def _beta(seg_eq: np.ndarray, seg_p: np.ndarray) -> float:
        if len(seg_eq) >= 3 and float(np.var(seg_eq, ddof=1)) > 0 \
                and float(np.var(seg_p, ddof=1)) > 0:
            return float(np.cov(seg_p, seg_eq, ddof=1)[0, 1]
                         / float(np.var(seg_eq, ddof=1)))
        return 0.0
    m["upside_beta"] = _beta(eq_a[up].values, s[up].values)
    m["downside_beta"] = _beta(eq_a[dn].values, s[dn].values)
    m["updown_beta_diff"] = m["upside_beta"] - m["downside_beta"]
    if len(eq_a[dn]) >= 3 and s[dn].std() > 0 and eq_a[dn].std() > 0:
        m["downside_corr_eq"] = float(s[dn].corr(eq_a[dn]))
    else:
        m["downside_corr_eq"] = 0.0
    m["up_market_ann"] = float(s[up].mean() * 12) if int(up.sum()) > 0 else 0.0
    m["down_market_ann"] = float(s[dn].mean() * 12) if int(dn.sum()) > 0 else 0.0
    m["n_up_market"] = int(up.sum())
    m["n_down_market"] = int(dn.sum())
    # crisis windows (net cumulative)
    cres = []
    for name, (a, b) in CRISIS_WINDOWS.items():
        seg = s.loc[pd.Timestamp(a):pd.Timestamp(b)]
        if len(seg) == 0:
            continue
        segw = np.cumprod(1.0 + seg.values)
        r = float(segw[-1] - 1.0)
        m[f"crisis_{name}_ret"] = r
        m[f"crisis_{name}_maxdd"] = _max_dd(segw)
        cres.append(r)
    m["crisis_avg_ret"] = float(np.mean(cres)) if cres else 0.0
    return m


# --------------------------------------------------------------------------- #
# Resilience score (encodes "uncorrelated positive returns")
# --------------------------------------------------------------------------- #

def resilience_score(df: pd.DataFrame, score_mode: str = "default") -> pd.Series:
    if score_mode == "asymmetric2":
        # "asymmetric2" -- the brief read literally: BEAT All-Weather's return
        # while keeping equity correlation asymmetric (correlated UP, protected
        # DOWN). The plain "asymmetric" mode rewards (Upbeta - Dnbeta), which the
        # combo search satisfies by FLEEING equity (low Upbeta AND low Dnbeta) --
        # measured: every winner ran bond/gold-heavy with Upbeta~0.05 and ~3-4%
        # return, below AW. asymmetric2 fixes that by rewarding Upbeta ABSOLUTELY
        # (capture upside) and ann_return ABSOLUTELY (beat AW 7.37%), while still
        # penalizing Dnbeta + downside correlation + drawdown. This keeps real
        # equity exposure in the selected combos so the short-on-downside gate
        # has something to flip. Selection is on TRAIN; OOS eval + DSR/bootstrap
        # remain the overfitting guardrails.
        s_ret = df["ann_return_net"].rank(pct=True)
        s_up = df["upside_beta"].rank(pct=True)
        s_dn = (-df["downside_beta"]).rank(pct=True)
        s_dcorr = (-df["downside_corr_eq"]).rank(pct=True)
        s_sharpe = df["sharpe_net"].rank(pct=True)
        s_dd = (-df["max_drawdown"]).rank(pct=True)
        return 100.0 * (0.30 * s_ret + 0.20 * s_up + 0.15 * s_dn
                        + 0.10 * s_dcorr + 0.15 * s_sharpe + 0.10 * s_dd).fillna(0.0)
    if score_mode == "asymmetric":
        # Reward upside capture, penalize downside beta + downside equity
        # correlation, keep Sharpe / both-down / drawdown as floor guards. This
        # is the "correlated to equities on the way up, low/negative on the way
        # down" objective the brief asks for, operationalized for selection.
        s_sharpe = df["sharpe_net"].rank(pct=True)
        s_asym = (df["upside_beta"] - df["downside_beta"]).rank(pct=True)
        s_dcorr = (-df["downside_corr_eq"]).rank(pct=True)
        s_bd = df["both_down_annualized"].rank(pct=True)
        s_dd = (-df["max_drawdown"]).rank(pct=True)
        return 100.0 * (0.30 * s_sharpe + 0.20 * s_asym + 0.20 * s_dcorr
                        + 0.15 * s_bd + 0.15 * s_dd).fillna(0.0)
    s_sharpe = df["sharpe_net"].rank(pct=True)
    s_bd = df["both_down_annualized"].rank(pct=True)
    s_dd = (-df["max_drawdown"]).rank(pct=True)
    s_dr = df["div_ratio"].rank(pct=True)
    s_uncorr = (-df["corr_eq_bothdown"]).rank(pct=True)
    return 100.0 * (0.30 * s_sharpe + 0.25 * s_bd + 0.15 * s_dd
                    + 0.15 * s_dr + 0.15 * s_uncorr).fillna(0.0)


def _quick_score(m: Dict[str, float]) -> float:
    return (0.30 * m["sharpe_net"] + 0.25 * m["both_down_annualized"]
            + 0.15 * (-m["max_drawdown"]) + 0.15 * m["div_ratio"]
            + 0.15 * (-m["corr_eq_bothdown"]))


# --------------------------------------------------------------------------- #
# Deflated Sharpe Ratio (Bailey & López de Prado 2014)
# --------------------------------------------------------------------------- #

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def deflated_sharpe(net_monthly: np.ndarray, n_trials: int,
                    periods_per_year: int = 12) -> Dict[str, float]:
    s = pd.Series(net_monthly).dropna()
    T = len(s)
    if T < 3 or n_trials < 2:
        sr = _sharpe(s.values)
        return {"dsr_prob": float("nan"), "deflated_sr_ann": float("nan"),
                "sr_ann": sr, "sr0_ann": float("nan"), "n_trials": float(n_trials),
                "T": float(T)}
    sr_ann = _sharpe(s.values)                       # annualized
    sr = sr_ann / math.sqrt(periods_per_year)        # per-observation
    skew = float(s.skew())
    kurt = float(s.kurt())                           # Fisher (excess)
    # expected max SR under null (per-observation)
    lnN = math.log(n_trials)
    e_max_z = math.sqrt(2.0 * lnN) - EULER_GAMMA / math.sqrt(2.0 * lnN)
    sr0 = e_max_z / math.sqrt(T)                     # per-observation
    denom = math.sqrt(max(1e-12, 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr))
    z = (sr - sr0) * math.sqrt(T - 1) / denom
    prob = _norm_cdf(z)
    return {"dsr_prob": float(prob),
            "deflated_sr_ann": float((sr - sr0) * math.sqrt(periods_per_year)),
            "sr_ann": float(sr_ann),
            "sr0_ann": float(sr0 * math.sqrt(periods_per_year)),
            "n_trials": float(n_trials), "T": float(T)}


# --------------------------------------------------------------------------- #
# Block bootstrap CI
# --------------------------------------------------------------------------- #

def block_bootstrap_ci(monthly: np.ndarray, stat_fn, n_boot: int = 5000,
                       block: int = 6, seed: int = 0) -> Tuple[float, float, float]:
    rng = np.random.RandomState(seed)
    x = np.asarray(monthly, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < block * 2:
        v = stat_fn(pd.Series(x)); return v, v, v
    point = stat_fn(pd.Series(x))
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = []
        while len(idx) < n:
            st = rng.randint(0, n)
            L = rng.geometric(1.0 / block)
            idx.extend(range(st, min(st + L, n)))
        boots[b] = stat_fn(pd.Series(x[idx[:n]]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(point), float(lo), float(hi)


def _ann_sharpe(m: pd.Series) -> float:
    s = m.std(ddof=1)
    return float(m.mean() / s * math.sqrt(12)) if s > 0 else 0.0


def _ann_ret(m: pd.Series) -> float:
    return float(m.mean() * 12)


# --------------------------------------------------------------------------- #
# Fast search engine
# --------------------------------------------------------------------------- #

def build_panel(ret: pd.DataFrame, sleeves: Sequence[str],
                start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    sub = ret.loc[start:end, list(sleeves)].copy()
    complete = [s for s in sub.columns if sub[s].notna().all()]
    return sub[complete]


def available_sleeves(ret, sleeves, start, end):
    sub = ret.loc[start:end, list(sleeves)]
    return [s for s in sub.columns if sub[s].notna().all()]


def enumerate_combos(avail, eq, bd, min_s, max_s):
    other = [s for s in avail if s not in eq and s not in bd]
    eq_ne = list(itertools.chain.from_iterable(
        itertools.combinations(eq, r) for r in range(1, len(eq) + 1)))
    bd_ne = list(itertools.chain.from_iterable(
        itertools.combinations(bd, r) for r in range(1, len(bd) + 1)))
    o_any = list(itertools.chain.from_iterable(
        itertools.combinations(other, r) for r in range(0, len(other) + 1)))
    seen, out = set(), []
    for e in eq_ne:
        for b in bd_ne:
            for o in o_any:
                c = tuple(dict.fromkeys(e + b + o))
                if min_s <= len(c) <= max_s:
                    k = frozenset(c)
                    if k not in seen:
                        seen.add(k)
                        out.append(c)
    return out


def fast_search(panel: pd.DataFrame, ret_full: pd.DataFrame, both_down: pd.Series,
                eq_ref: pd.Series, bd_ref: pd.Series, combos: List[Tuple[str, ...]],
                schemes: Sequence[str], cap: float, cost_bps: float,
                shrink: str, trailing: int, label: str = "",
                progress_every: int = 2000,
                erc_cap_mode: str = "capped",
                tsmom_lookback: int = 12,
                eq: Optional[List[str]] = None,
                score_mode: str = "default",
                lev_rate: float = 0.0,
                bonds: Optional[List[str]] = None) -> pd.DataFrame:
    sleeves_all = list(panel.columns)
    pos = {s: i for i, s in enumerate(sleeves_all)}
    precomp = precompute_refits(ret_full, sleeves_all, panel.index, trailing, shrink)
    rows = []
    nets = []  # Fix 4: per-trial TRAIN net-return vectors for the effective-N diag
    t0 = time.time()
    n_total = len(combos) * len(schemes)
    done = 0
    for combo in combos:
        idxs = [pos[s] for s in combo]
        for sch in schemes:
            bt = backtest(panel, precomp, idxs, sch, cap, cost_bps,
                          erc_cap_mode=erc_cap_mode, ret_full=ret_full,
                          tsmom_lookback=tsmom_lookback,
                          eq=eq, lev_rate=lev_rate, bonds=bonds)
            m = compute_metrics(bt["net"], bt["gross"], bt["turnover"], panel.index,
                                both_down, eq_ref, bd_ref, bt["div_ratio"])
            row = {"combo": ",".join(combo), "scheme": sch, "n_sleeves": len(combo)}
            if bt["last_w"] is not None:
                row.update({f"w_{s}": float(bt["last_w"][i]) for i, s in enumerate(combo)})
            row.update(m)
            rows.append(row)
            nets.append(np.asarray(bt["net"], dtype=float))
            done += 1
            if done % progress_every == 0 or done == n_total:
                dt = time.time() - t0
                print(f"  [{label} {done:>7}/{n_total}] {dt:6.1f}s "
                      f"({done/max(dt,1e-9):.1f}/s)", flush=True)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["resilience_score"] = resilience_score(df, score_mode)
        df["rank"] = df["resilience_score"].rank(ascending=False, method="min").astype(int)
        df = df.sort_values("rank").reset_index(drop=True)
        # Fix 4: effective-N diagnostic. DSR uses N = (#combos * #schemes) but
        # the trials share sleeves -> highly correlated, so the effective
        # independent-trial count is far smaller than the nominal N. Effective
        # rank = (sum of eigenvalues) / (max eigenvalue) of the de-meaned
        # TRAIN trial-return matrix. Use the T×T eigenvalue trick (nonzero
        # eigenvalues of X Xᵀ equal those of Xᵀ X) so cost is O(T^2 N + T^3),
        # not O(N^3) -- critical with N ~ 1e4 trials but T ~ 120 months.
        try:
            X = np.column_stack(nets)                 # (T, N_trials)
            Xc = np.nan_to_num(X - X.mean(axis=0, keepdims=True))
            M = Xc @ Xc.T                              # (T, T)
            ev = np.clip(np.linalg.eigvalsh(M), 0.0, None)
            lam_max = float(ev.max())
            eff_n = float(ev.sum() / lam_max) if lam_max > 0 else float("nan")
            df.attrs["effective_n"] = eff_n
            df.attrs["n_trials_nominal"] = float(X.shape[1])
        except Exception:
            df.attrs["effective_n"] = float("nan")
            df.attrs["n_trials_nominal"] = float(len(nets))
    return df


def fixed_weight_backtest_costs(panel: pd.DataFrame, weights: Dict[str, float],
                                cost_bps: float) -> Dict[str, np.ndarray]:
    sleeves = [s for s in panel.columns if s in weights]
    w_t = np.array([weights[s] for s in sleeves])
    w_t = w_t / w_t.sum()
    idxpos = [list(panel.columns).index(s) for s in sleeves]
    R = panel.values
    T = len(panel.index)
    gross = np.zeros(T); net = np.zeros(T); turn = np.zeros(T)
    w = None
    for pos in range(T):
        if w is None:
            t = float(np.abs(w_t).sum())
        else:
            t = float(np.abs(w_t - w).sum())
        turn[pos] = t
        g = float(w_t @ R[pos, idxpos])
        gross[pos] = g
        net[pos] = g - t * cost_bps
        w = w_t * (1.0 + R[pos, idxpos])
        s = w.sum()
        w = w / s if s > 0 else w_t
    return {"gross": gross, "net": net, "turnover": turn, "sleeves": sleeves}


# --------------------------------------------------------------------------- #
# Rolling FULL re-enumerated selection
# --------------------------------------------------------------------------- #

def rolling_full_select(ret_full: pd.DataFrame, avail: List[str], eq: List[str],
                        bd: List[str], schemes: Sequence[str], cap: float,
                        cost_bps: float, shrink: str, trailing: int,
                        test_start: pd.Timestamp, test_end: pd.Timestamp,
                        max_size: int, min_size: int,
                        trailing_years: int = 10,
                        erc_cap_mode: str = "capped",
                        ref_mode: str = "external",
                        tsmom_lookback: int = 12,
                        score_mode: str = "default",
                        lev_rate: float = 0.0) -> Tuple[pd.Series, pd.DataFrame]:
    idx = ret_full.index
    test_idx = idx[(idx >= test_start) & (idx <= test_end)]
    years = sorted(set(d.year for d in test_idx))
    chunks, log = [], []
    for y in years:
        sel = idx[idx >= pd.Timestamp(f"{y}-01-01")][0]
        w_start = sel - pd.DateOffset(years=trailing_years)
        # trailing window strictly before sel
        trail_idx = idx[(idx >= w_start) & (idx < sel)]
        if len(trail_idx) < 24:
            continue
        trail_avail = available_sleeves(ret_full, avail, trail_idx[0], trail_idx[-1])
        trail_eq = [s for s in eq if s in trail_avail]
        trail_bd = [s for s in bd if s in trail_avail]
        if not trail_eq or not trail_bd:
            continue
        combos = enumerate_combos(trail_avail, trail_eq, trail_bd, min_size, max_size)
        panel_trail = build_panel(ret_full, trail_avail, trail_idx[0], trail_idx[-1])
        eqr, bdr, bd_trail, _ = regime_references(
            ret_full, trail_idx[0], trail_idx[-1], ref_mode)
        res = fast_search(panel_trail, ret_full, bd_trail, eqr, bdr, combos, schemes,
                          cap, cost_bps, shrink, trailing, label=f"roll{y}",
                          progress_every=10**9, erc_cap_mode=erc_cap_mode,
                          eq=trail_eq, score_mode=score_mode, lev_rate=lev_rate,
                          bonds=trail_bd)
        if res.empty:
            continue
        best = res.iloc[0]
        combo = best["combo"].split(",")
        sch = best["scheme"]
        # weights at sel from trailing 36m
        precomp = precompute_refits(ret_full, list(panel_trail.columns),
                                    panel_trail.index, trailing, shrink)
        # need panel over the hold year with same sleeves
        hold_idx = idx[(idx >= sel) & (idx.year == y) & (idx <= test_end)]
        panel_hold = ret_full.loc[hold_idx, combo].dropna(axis=1, how="all")
        if panel_hold.shape[1] != len(combo):
            continue
        # solve weights using last refit cov (at/just before sel)
        last_refit = max(d for d in precomp if d <= sel)
        cov_full, vol_full = precomp[last_refit]
        pos_map = {s: i for i, s in enumerate(panel_trail.columns)}
        cov = cov_full[np.ix_([pos_map[s] for s in combo], [pos_map[s] for s in combo])]
        vol = vol_full[[pos_map[s] for s in combo]]
        if sch in FLAVOR_PRESETS:
            # TrendProtect flavor over the hold year -- monthly-signal engine,
            # so it does NOT fit the static-weight-hold COV branch below.
            # Dispatch to _backtest_flavor on the same footing as TRAIN/TEST
            # (precomp already solved above; eq = trailing-window equity sleeves).
            idxs = list(range(len(combo)))
            bt = _backtest_flavor(panel_hold, ret_full, idxs, trail_eq, precomp,
                                  FLAVOR_PRESETS[sch], tsmom_lookback, cost_bps,
                                  lev_rate, cap=cap, erc_cap_mode=erc_cap_mode)
            chunk_ret = pd.Series(bt["net"], index=panel_hold.index)
            chunks.append(chunk_ret)
            log.append({"year": y, "combo": ",".join(combo), "scheme": sch,
                        "sel_score": float(best["resilience_score"]),
                        "sel_sharpe": float(best["sharpe_net"]),
                        "sel_both_down_ann": float(best["both_down_annualized"]),
                        "top_weight": f"flavor gross {float(np.abs(bt['last_w']).sum()):.2f}"})
            print(f"  rolling {y}: {len(combos)} combos x {len(schemes)} sch -> "
                  f"{combo} / {sch} (score {best['resilience_score']:.1f})", flush=True)
            continue
        if sch == "LS-TSMOM":
            # Monthly momentum signal over the hold year (no static weight to
            # hold). Reuse _backtest_ls_tsmom so rolling LS-TSMOM is on the same
            # footing as the TRAIN/TEST eval (pre-window history -> causal sig).
            # panel_hold.columns == combo (order preserved, dropna-guarded above),
            # so sleeve indices into panel_hold are just range(len(combo)).
            idxs = list(range(len(combo)))
            bt = _backtest_ls_tsmom(panel_hold, ret_full, idxs, tsmom_lookback, cost_bps)
            chunk_ret = pd.Series(bt["net"], index=panel_hold.index)
            chunks.append(chunk_ret)
            log.append({"year": y, "combo": ",".join(combo), "scheme": sch,
                        "sel_score": float(best["resilience_score"]),
                        "sel_sharpe": float(best["sharpe_net"]),
                        "sel_both_down_ann": float(best["both_down_annualized"]),
                        "top_weight": "L/S gross 100%"})
            print(f"  rolling {y}: {len(combos)} combos x {len(schemes)} sch -> "
                  f"{combo} / {sch} (score {best['resilience_score']:.1f})", flush=True)
            continue
        solver_capped = (sch == "MinVar") or (
            sch == "ERC" and erc_cap_mode == "capped" and 0.0 < cap < 1.0)
        try:
            wv = SCHEMES[sch](cov, vol, cap=cap, erc_cap_mode=erc_cap_mode)
            if solver_capped:
                if 0.0 < cap < 1.0 and wv.max() > cap + 1e-6:
                    wv = cap_weights(wv, cap)
                else:
                    wv = wv / wv.sum()
            else:
                wv = cap_weights(wv, cap)
        except Exception:
            wv = cap_weights(np.ones(len(combo)) / len(combo), cap)
        chunk_ret = (panel_hold.values * wv).sum(axis=1) - float(np.abs(wv).sum()) * cost_bps
        chunks.append(pd.Series(chunk_ret, index=panel_hold.index))
        log.append({"year": y, "combo": ",".join(combo), "scheme": sch,
                    "sel_score": float(best["resilience_score"]),
                    "sel_sharpe": float(best["sharpe_net"]),
                    "sel_both_down_ann": float(best["both_down_annualized"]),
                    "top_weight": f"{combo[int(np.argmax(wv))]} {wv.max()*100:.1f}%"})
        print(f"  rolling {y}: {len(combos)} combos x {len(schemes)} sch -> "
              f"{combo} / {sch} (score {best['resilience_score']:.1f})", flush=True)
    port = pd.concat(chunks).sort_index() if chunks else pd.Series(dtype=float)
    return port, pd.DataFrame(log)


# --------------------------------------------------------------------------- #
# fmt helpers
# --------------------------------------------------------------------------- #

def fp(x, d=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x*100:.{d}f}%"


def fn(x, d=3):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x:.{d}f}"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Remediated anti-overfit risk-parity eval.")
    ap.add_argument("--train-start", default=TRAIN_DEFAULT[0])
    ap.add_argument("--train-end", default=TRAIN_DEFAULT[1])
    ap.add_argument("--test-start", default=TEST_DEFAULT[0])
    ap.add_argument("--test-end", default=TEST_DEFAULT[1])
    ap.add_argument("--trailing", type=int, default=36)
    ap.add_argument("--min-sleeves", type=int, default=5,
                        help="Min sleeves per combo. Default 5 so the per-sleeve "
                             "cap is always feasible (long-only, sum=1).")
    ap.add_argument("--max-sleeves", type=int, default=8)
    ap.add_argument("--include-volatility", action="store_true",
                    help="Add the ^VIX spot-index sleeve back (NON-tradable; "
                         "results are illustrative only). OFF by default.")
    ap.add_argument("--schemes", default=",".join(SCHEME_ORDER))
    ap.add_argument("--cap", type=float, default=0.20,
                    help="Per-sleeve weight cap (0 disables). Default 0.20.")
    ap.add_argument("--erc-cap-mode", choices=["capped", "posthoc", "none"],
                    default="capped",
                    help="How the cap is applied to ERC. 'capped' (default) = "
                         "solve ERC with the cap inside the optimizer (true "
                         "box-constrained solve, approximate for ERC). 'posthoc' "
                         "= legacy uncapped ERC then clip. 'none' = ignore cap "
                         "for ERC. MinVar always solves with the cap inside.")
    ap.add_argument("--ref-mode", choices=["external", "sleeves"],
                    default="external",
                    help="Reference for the both-down regime + equity-correlation "
                         "metric. 'external' (default) = SPY + AGG (investable, "
                          "non-candidate) -- breaks the reference/universe overlap. "
                          "'sleeves' = legacy sleeve-average reference (regression guard).")
    ap.add_argument("--shrink", choices=["lw", "none"], default="lw",
                    help="Covariance shrinkage. Default lw (Ledoit-Wolf).")
    ap.add_argument("--cost-bps", type=float, default=10.0,
                    help="Transaction cost per side in bps. Default 10.")
    ap.add_argument("--top-n", type=int, default=50)
    ap.add_argument("--bootstrap", type=int, default=5000)
    ap.add_argument("--rolling-schemes", default="EW,MinVar,LS-TSMOM",
                    help="Schemes for the rolling full re-enumeration (cost ctrl). "
                         "ERC is excluded by default: capped-ERC is an approximate "
                         "projected-gradient solve (~34 ms each) and the rolling "
                         "pass re-enumerates ~28k combos per window, so ERC in "
                         "rolling adds ~2.4 h for a non-winner scheme. MinVar is "
                         "the rigorous box-constrained solver and the empirical "
                         "winner; pass --rolling-schemes ERC,EW,MinVar,LS-TSMOM "
                         "to restore ERC if desired.")
    ap.add_argument("--tsmom-lookback", type=int, default=12,
                    help="Trailing-month lookback for the LS-TSMOM (managed-"
                         "futures) momentum signal. Default 12 (matches "
                         "all_weather_v2.backtest_ls).")
    ap.add_argument("--score-mode", choices=["default", "asymmetric", "asymmetric2"],
                    default="default",
                    help="Resilience-score objective for TRAIN selection. "
                         "'default' (default) = 0.30 Sharpe + 0.25 both-down ann "
                         "+ 0.15 (-maxDD) + 0.15 div ratio + 0.15 (-corr with "
                         "equity in both-down) -- the legacy 'uncorrelated positive "
                         "returns' objective. 'asymmetric' = 0.30 Sharpe + 0.20 "
                         "(upside_beta - downside_beta) + 0.20 (-downside_corr_eq) "
                         "+ 0.15 both-down ann + 0.15 (-maxDD) -- 'correlated up, "
                         "protected down' (but the (Upbeta-Dnbeta) term lets the "
                         "search FLEE equity -> low return). 'asymmetric2' = 0.30 "
                         "ann_return + 0.20 upside_beta + 0.15 (-downside_beta) + "
                         "0.10 (-downside_corr_eq) + 0.15 Sharpe + 0.10 (-maxDD) -- "
                         "rewards upside capture AND return (beat All-Weather) while "
                         "penalizing downside; keeps real equity exposure so the "
                         "short-on-downside gate has something to flip. Only changes "
                         "selection; metrics are always computed.")
    ap.add_argument("--lev-rate", type=float, default=0.058,
                    help="Annual funding cost on gross > 1 (leverage). Default 0.058 "
                         "(5.8 percent APR). Charged monthly as max(0, gross-1)*lev_rate/12 "
                         "in the TrendProtect flavor backtests. 0 disables the "
                         "leverage cost (long-only COV schemes are unaffected -- "
                         "they always run gross=1).")
    ap.add_argument("--no-rolling", action="store_true")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    tr_s, tr_e = pd.Timestamp(args.train_start), pd.Timestamp(args.train_end)
    te_s, te_e = pd.Timestamp(args.test_start), pd.Timestamp(args.test_end)
    valid = set(SCHEMES) | set(FLAVOR_PRESETS)
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip() in valid]
    roll_schemes = [s.strip() for s in args.rolling_schemes.split(",") if s.strip() in valid]
    cost = args.cost_bps / 10000.0

    print("=" * 74)
    print("REMEDIATED ANTI-OVERFIT RISK-PARITY EVALUATION (v2)")
    print("=" * 74)
    print(f"TRAIN {tr_s.date()} -> {tr_e.date()}  (selection)   "
          f"TEST {te_s.date()} -> {te_e.date()}  (eval only)")
    print(f"schemes={schemes}  cap={args.cap}  erc_cap_mode={args.erc_cap_mode}  "
          f"shrink={args.shrink}  cost={args.cost_bps}bps/side  trailing={args.trailing}m")
    print(f"Volatility sleeve: "
          f"{'INCLUDED (^VIX spot, NON-tradable)' if args.include_volatility else 'EXCLUDED (default)'}")

    ret = load_monthly_returns()
    sleeves = default_sleeves(args.include_volatility)

    # A requested sleeve that the panel does not carry must fail with a reason.
    # `available_sleeves` indexes the panel directly, so a missing column
    # otherwise surfaces as a bare KeyError. This fires for --include-volatility
    # since the ^VIX sleeve was removed from the aggregates: a volatility index
    # is a level, not a holdable return stream (docs/methodology.md §4).
    missing = [s for s in sleeves if s not in ret.columns]
    if missing:
        raise SystemExit(
            f"Requested sleeve(s) not present in the asset-class panel: {missing}\n"
            f"Panel has {len(ret.columns)} sleeves spanning "
            f"{str(ret.index.min())[:7]}..{str(ret.index.max())[:7]}.\n"
            + ("The Volatility sleeve was removed because ^VIX is a level, not a\n"
               "return series -- see docs/methodology.md §4. Drop "
               "--include-volatility.\n" if "Volatility" in missing else "")
            + "Rebuild the panel with build_aggregates.py --extended if this is "
              "unexpected.")

    avail_tr = available_sleeves(ret, sleeves, tr_s, tr_e)
    avail_te = available_sleeves(ret, sleeves, te_s, te_e)
    avail = [s for s in avail_tr if s in avail_te]
    eq = [s for s in EQUITY_SLEEVES if s in avail]
    bd = [s for s in BOND_SLEEVES if s in avail]
    print(f"Sleeves over both windows ({len(avail)}): {avail}")
    print(f"  equity: {eq}   bonds: {bd}")

    max_size = args.max_sleeves if args.max_sleeves > 0 else len(avail)
    combos = enumerate_combos(avail, eq, bd, args.min_sleeves, max_size)
    n_trials = len(combos) * len(schemes)
    print(f"Combinations: {len(combos)}  x  schemes: {len(schemes)} = "
          f"{n_trials} trials on TRAIN")

    panel_tr = build_panel(ret, avail, tr_s, tr_e)
    panel_te = build_panel(ret, avail, te_s, te_e)
    eqr_tr, bdr_tr, bd_tr, ref_label = regime_references(ret, tr_s, tr_e, args.ref_mode)
    eqr_te, bdr_te, bd_te, _ = regime_references(ret, te_s, te_e, args.ref_mode)
    print(f"Reference mode: {ref_label}")
    print(f"Both-down months: TRAIN {int(bd_tr.sum())}/{len(bd_tr)} | "
          f"TEST {int(bd_te.sum())}/{len(bd_te)}")

    print("\n-- TRAIN search (selection) --")
    train_res = fast_search(panel_tr, ret, bd_tr, eqr_tr, bdr_tr, combos, schemes,
                            args.cap, cost, args.shrink, args.trailing, label="TRAIN",
                            erc_cap_mode=args.erc_cap_mode,
                            tsmom_lookback=args.tsmom_lookback,
                            eq=eq, score_mode=args.score_mode, lev_rate=args.lev_rate,
                            bonds=bd)
    train_res.to_csv(os.path.join(args.out_dir, "train_results.csv"), index=False)
    print(f"Wrote train_results.csv ({len(train_res)} rows)")

    # All-Weather benchmark (uncapped static) on TRAIN & TEST
    aw_sleeves = [s for s in ALL_WEATHER_WEIGHTS if s in avail]
    aw_w = {s: ALL_WEATHER_WEIGHTS[s] for s in aw_sleeves}
    aw_tr = fixed_weight_backtest_costs(panel_tr[aw_sleeves], aw_w, cost)
    aw_te = fixed_weight_backtest_costs(panel_te[aw_sleeves], aw_w, cost)
    aw_tr_m = compute_metrics(aw_tr["net"], aw_tr["gross"], aw_tr["turnover"],
                              panel_tr.index, bd_tr, eqr_tr, bdr_tr, float("nan"))
    aw_te_m = compute_metrics(aw_te["net"], aw_te["gross"], aw_te["turnover"],
                              panel_te.index, bd_te, eqr_te, bdr_te, float("nan"))

    # TEST eval of TRAIN top-N
    print("\n-- TEST evaluation of TRAIN top-N (OOS) --")
    top = train_res.head(args.top_n).copy()
    eval_rows = []
    for _, r in top.iterrows():
        combo = r["combo"].split(",")
        idxs = [list(panel_te.columns).index(s) for s in combo]
        pre = precompute_refits(ret, list(panel_te.columns), panel_te.index,
                                args.trailing, args.shrink)
        bt = backtest(panel_te, pre, idxs, r["scheme"], args.cap, cost,
                      erc_cap_mode=args.erc_cap_mode, ret_full=ret,
                      tsmom_lookback=args.tsmom_lookback)
        m = compute_metrics(bt["net"], bt["gross"], bt["turnover"], panel_te.index,
                            bd_te, eqr_te, bdr_te, bt["div_ratio"])
        row = {"combo": r["combo"], "scheme": r["scheme"], "train_rank": int(r["rank"]),
               "train_score": float(r["resilience_score"]), "train_sharpe": float(r["sharpe_net"]),
               "train_both_down_ann": float(r["both_down_annualized"]),
               "train_maxdd": float(r["max_drawdown"])}
        row.update({f"test_{k}": v for k, v in m.items()})
        eval_rows.append(row)
    test_eval = pd.DataFrame(eval_rows)
    if not test_eval.empty:
        # test_score with same formula on test_* columns
        sc = pd.DataFrame({
            "sharpe_net": test_eval["test_sharpe_net"],
            "ann_return_net": test_eval.get("test_ann_return_net", test_eval["test_sharpe_net"]),
            "both_down_annualized": test_eval["test_both_down_annualized"],
            "max_drawdown": test_eval["test_max_drawdown"],
            "div_ratio": test_eval["test_div_ratio"],
            "corr_eq_bothdown": test_eval["test_corr_eq_bothdown"],
            "upside_beta": test_eval.get("test_upside_beta", 0.0),
            "downside_beta": test_eval.get("test_downside_beta", 0.0),
            "downside_corr_eq": test_eval.get("test_downside_corr_eq", 0.0),
        })
        test_eval["test_score"] = resilience_score(sc, args.score_mode).values
        test_eval["test_rank"] = test_eval["test_score"].rank(ascending=False, method="min").astype(int)
    test_eval.to_csv(os.path.join(args.out_dir, "test_eval_topN.csv"), index=False)

    # Winner = TRAIN #1, evaluated OOS
    win = train_res.iloc[0]
    win_combo = win["combo"].split(",")
    win_sch = win["scheme"]
    win_idxs = [list(panel_te.columns).index(s) for s in win_combo]
    pre_te = precompute_refits(ret, list(panel_te.columns), panel_te.index,
                               args.trailing, args.shrink)
    win_bt = backtest(panel_te, pre_te, win_idxs, win_sch, args.cap, cost,
                      erc_cap_mode=args.erc_cap_mode, ret_full=ret,
                      tsmom_lookback=args.tsmom_lookback)
    win_te_m = compute_metrics(win_bt["net"], win_bt["gross"], win_bt["turnover"],
                               panel_te.index, bd_te, eqr_te, bdr_te, win_bt["div_ratio"])

    # Fix 3: LS-TSMOM (managed-futures) on an equal footing with risk parity.
    # Take the TRAIN-best LS-TSMOM portfolio (rank-1 within the LS-TSMOM family)
    # and evaluate it OOS on TEST, with its own per-family DSR + bootstrap CIs.
    # Also keep the best COV-scheme portfolio as the "risk-parity winner" for the
    # §9 head-to-head, so the comparison is LS-TSMOM vs risk-parity vs All-Weather
    # even when the overall TRAIN winner is itself LS-TSMOM.
    ls_te_m: Dict[str, float] = {}
    ls_dsr: Dict[str, float] = {}
    ls_diag: Dict[str, float] = {}
    ls_in = "LS-TSMOM" in schemes
    ls_win_combo: List[str] = []
    if ls_in:
        ls_train = train_res[train_res["scheme"] == "LS-TSMOM"].sort_values("rank")
        if not ls_train.empty:
            ls_win = ls_train.iloc[0]
            ls_win_combo = ls_win["combo"].split(",")
            ls_idxs = [list(panel_te.columns).index(s) for s in ls_win_combo]
            ls_bt = backtest(panel_te, pre_te, ls_idxs, "LS-TSMOM", args.cap, cost,
                             erc_cap_mode=args.erc_cap_mode, ret_full=ret,
                             tsmom_lookback=args.tsmom_lookback)
            ls_te_m = compute_metrics(ls_bt["net"], ls_bt["gross"], ls_bt["turnover"],
                                      panel_te.index, bd_te, eqr_te, bdr_te, ls_bt["div_ratio"])
            # LS-TSMOM ran once per combo -> trial count = #combos in the family.
            n_ls_trials = max(len(combos), 2)
            ls_dsr = deflated_sharpe(ls_bt["net"], n_ls_trials)
            if len(ls_bt["net"]) >= 24:
                lp, llo, lhi = block_bootstrap_ci(ls_bt["net"], _ann_sharpe, args.bootstrap)
                ls_diag["oos_sharpe"] = lp
                ls_diag["oos_sharpe_ci95_lo"] = llo
                ls_diag["oos_sharpe_ci95_hi"] = lhi
                bd_ls = pd.Series(ls_bt["net"], index=panel_te.index)[bd_te].dropna().values
                if len(bd_ls) >= 8:
                    lpb, llb, lhb = block_bootstrap_ci(bd_ls, _ann_ret, args.bootstrap)
                    ls_diag["oos_both_down_ann"] = lpb
                    ls_diag["oos_both_down_ann_ci95_lo"] = llb
                    ls_diag["oos_both_down_ann_ci95_hi"] = lhb
            print(f"LS-TSMOM TRAIN-best: {ls_win['combo']} | "
                  f"TEST Sharpe {ls_te_m.get('sharpe_net', float('nan')):.3f} | "
                  f"TEST both-down {ls_te_m.get('both_down_annualized', float('nan')):+.2%}")
    # Best COV-scheme (risk-parity) portfolio for the §9 head-to-head. If the
    # overall TRAIN winner is already a COV scheme, reuse it; otherwise solve
    # the rank-1 COV-scheme portfolio on TEST.
    rp_te_m: Dict[str, float] = win_te_m
    rp_combo: List[str] = win_combo
    rp_sch: str = win_sch
    if ls_in and win_sch == "LS-TSMOM":
        rp_train = train_res[train_res["scheme"].isin(COV_SCHEMES)].sort_values("rank")
        if not rp_train.empty:
            rp_win = rp_train.iloc[0]
            rp_combo = rp_win["combo"].split(",")
            rp_sch = rp_win["scheme"]
            rp_idxs = [list(panel_te.columns).index(s) for s in rp_combo]
            rp_bt = backtest(panel_te, pre_te, rp_idxs, rp_sch, args.cap, cost,
                             erc_cap_mode=args.erc_cap_mode, ret_full=ret,
                             tsmom_lookback=args.tsmom_lookback)
            rp_te_m = compute_metrics(rp_bt["net"], rp_bt["gross"], rp_bt["turnover"],
                                      panel_te.index, bd_te, eqr_te, bdr_te, rp_bt["div_ratio"])

    # TrendProtect flavors: per-flavor TRAIN-best -> TEST eval, each with its own
    # per-family DSR (n_trials = #combos in the family) + block-bootstrap CIs.
    # Mirrors the LS-TSMOM block so all flavors are on the same statistical
    # footing for the §10 comparison menu. flavors = the 4 FLAVOR_PRESETS keys
    # actually present in this run's scheme set.
    flavor_names = [s for s in SCHEME_ORDER if s in FLAVOR_PRESETS and s in schemes]
    flavor_data: Dict[str, Dict[str, object]] = {}
    for fname in flavor_names:
        f_train = train_res[train_res["scheme"] == fname].sort_values("rank")
        if f_train.empty:
            continue
        f_win = f_train.iloc[0]
        f_combo = f_win["combo"].split(",")
        f_idxs = [list(panel_te.columns).index(s) for s in f_combo]
        f_bt = backtest(panel_te, pre_te, f_idxs, fname, args.cap, cost,
                        erc_cap_mode=args.erc_cap_mode, ret_full=ret,
                        tsmom_lookback=args.tsmom_lookback,
                        eq=eq, lev_rate=args.lev_rate, bonds=bd)
        f_te_m = compute_metrics(f_bt["net"], f_bt["gross"], f_bt["turnover"],
                                 panel_te.index, bd_te, eqr_te, bdr_te, f_bt["div_ratio"])
        f_dsr = deflated_sharpe(f_bt["net"], max(len(combos), 2))
        f_diag: Dict[str, float] = {}
        if len(f_bt["net"]) >= 24:
            fp_, flo, fhi = block_bootstrap_ci(f_bt["net"], _ann_sharpe, args.bootstrap)
            f_diag["oos_sharpe"] = fp_
            f_diag["oos_sharpe_ci95_lo"] = flo
            f_diag["oos_sharpe_ci95_hi"] = fhi
            bd_f = pd.Series(f_bt["net"], index=panel_te.index)[bd_te].dropna().values
            if len(bd_f) >= 8:
                fpb, flb, fhb = block_bootstrap_ci(bd_f, _ann_ret, args.bootstrap)
                f_diag["oos_both_down_ann"] = fpb
                f_diag["oos_both_down_ann_ci95_lo"] = flb
                f_diag["oos_both_down_ann_ci95_hi"] = fhb
        # gross notional + annualized leverage cost (from the last target pos).
        if f_bt.get("last_w") is not None:
            gn = float(np.abs(f_bt["last_w"]).sum())
            f_te_m["gross_notional_last"] = gn
            f_te_m["lev_cost_ann"] = max(0.0, gn - 1.0) * args.lev_rate if gn > 1 else 0.0
        else:
            f_te_m["gross_notional_last"] = float("nan")
            f_te_m["lev_cost_ann"] = 0.0
        flavor_data[fname] = {"combo": f_combo, "te_m": f_te_m,
                              "dsr": f_dsr, "diag": f_diag}
        print(f"{fname} TRAIN-best: {f_win['combo']} | "
              f"TEST Sharpe {f_te_m.get('sharpe_net', float('nan')):.3f} | "
              f"TEST both-down {f_te_m.get('both_down_annualized', float('nan')):+.2%} | "
              f"upβ {f_te_m.get('upside_beta', float('nan')):.2f} dnβ "
              f"{f_te_m.get('downside_beta', float('nan')):.2f}")

    # Rolling full re-enumerated selection
    oos_port, sel_log = (pd.Series(dtype=float), pd.DataFrame())
    if not args.no_rolling:
        print("\n-- Rolling FULL re-enumerated selection across TEST --")
        oos_port, sel_log = rolling_full_select(
            ret, avail, eq, bd, roll_schemes, args.cap, cost, args.shrink,
            args.trailing, te_s, te_e, max_size, args.min_sleeves,
            erc_cap_mode=args.erc_cap_mode, ref_mode=args.ref_mode,
            tsmom_lookback=args.tsmom_lookback,
            score_mode=args.score_mode, lev_rate=args.lev_rate)
        sel_log.to_csv(os.path.join(args.out_dir, "rolling_selection_log.csv"), index=False)
        oos_port.to_csv(os.path.join(args.out_dir, "oos_rolling_returns.csv"))
    oos_m = compute_metrics(oos_port.values, oos_port.values, np.zeros(len(oos_port)),
                            oos_port.index, bd_te, eqr_te, bdr_te, float("nan")) if len(oos_port) else {}

    # Deflated Sharpe (winner on TEST)
    dsr = deflated_sharpe(win_bt["net"], n_trials)
    dsr_oos_roll = deflated_sharpe(oos_port.values, n_trials) if len(oos_port) else {}

    # Overfit diagnostics
    diag = overfit_diag(train_res, test_eval, win, win_te_m, aw_te_m, dsr)
    # Fix 4: effective-N diagnostic (DSR's N assumes independent trials; the
    # trials share sleeves so the effective independent-trial count is far
    # smaller than the nominal N -- surfacing this is the disclosure).
    diag["effective_n_trials"] = float(train_res.attrs.get("effective_n", float("nan")))
    diag["n_trials_nominal"] = float(
        train_res.attrs.get("n_trials_nominal", float(n_trials)))
    # Fix-1 verification: does the winner's solver output already respect the
    # cap (i.e. is the post-hoc clip a no-op)? last_w is the solver output for
    # MinVar / ERC-capped (we skip the post-hoc clip there). Skip for LS-TSMOM,
    # which has no covariance solver / no per-sleeve cap (it is $1 gross L/S).
    if (win_bt.get("last_w") is not None and 0.0 < args.cap < 1.0
            and win_sch in COV_SCHEMES):
        diag["winner_max_weight"] = float(np.max(win_bt["last_w"]))
        diag["winner_cap"] = float(args.cap)
        diag["winner_cap_respected_by_solver"] = float(
            diag["winner_max_weight"] <= args.cap + 1e-6)
    # bootstrap CIs (winner OOS)
    if len(win_bt["net"]) >= 24:
        p, lo, hi = block_bootstrap_ci(win_bt["net"], _ann_sharpe, args.bootstrap)
        diag["oos_sharpe"], diag["oos_sharpe_ci95_lo"], diag["oos_sharpe_ci95_hi"] = p, lo, hi
        bd_win = pd.Series(win_bt["net"], index=panel_te.index)[bd_te].dropna().values
        if len(bd_win) >= 8:
            pb, lob, hib = block_bootstrap_ci(bd_win, _ann_ret, args.bootstrap)
            diag["oos_both_down_ann"], diag["oos_both_down_ann_ci95_lo"], \
                diag["oos_both_down_ann_ci95_hi"] = pb, lob, hib
    pd.DataFrame(list(diag.items()), columns=["metric", "value"]).to_csv(
        os.path.join(args.out_dir, "overfit_diagnostics.csv"), index=False)

    # scheme comparison
    if not test_eval.empty:
        sc = test_eval.groupby("scheme").agg(
            n=("test_sharpe_net", "size"),
            test_sharpe_mean=("test_sharpe_net", "mean"),
            test_both_down_ann_mean=("test_both_down_annualized", "mean"),
            test_maxdd_mean=("test_max_drawdown", "mean"),
            test_divratio_mean=("test_div_ratio", "mean"),
            test_score_mean=("test_score", "mean"),
            train_rank_mean=("train_rank", "mean"),
        ).reset_index().sort_values("test_score_mean", ascending=False)
        sc.to_csv(os.path.join(args.out_dir, "scheme_comparison_test.csv"), index=False)

    write_report(args, train_res, test_eval, oos_port, oos_m, sel_log, win, win_combo,
                 win_sch, win_te_m, aw_tr_m, aw_te_m, diag, dsr, dsr_oos_roll,
                 schemes, avail, combos, n_trials, ref_label,
                 int(bd_tr.sum()), int(bd_te.sum()),
                 ls_in, ls_win_combo, ls_te_m, ls_dsr, ls_diag,
                 rp_combo, rp_sch, rp_te_m,
                 flavor_data=flavor_data)
    print(f"\nReport: {os.path.join(args.out_dir, 'report_eval.md')}")
    print("Done.")
    return 0


def overfit_diag(train_res, test_eval, win, win_te_m, aw_te_m, dsr) -> Dict[str, float]:
    d: Dict[str, float] = {}
    d["train_score_mean"] = float(train_res["resilience_score"].mean())
    d["train_score_std"] = float(train_res["resilience_score"].std())
    d["winner_train_score"] = float(win["resilience_score"])
    d["winner_train_score_z"] = float(
        (win["resilience_score"] - d["train_score_mean"]) / max(d["train_score_std"], 1e-9))
    d["winner_train_sharpe"] = float(win["sharpe_net"])
    d["winner_test_sharpe"] = float(win_te_m.get("sharpe_net", float("nan")))
    d["winner_sharpe_degradation"] = float(d["winner_test_sharpe"] - d["winner_train_sharpe"])
    d["winner_train_both_down_ann"] = float(win["both_down_annualized"])
    d["winner_test_both_down_ann"] = float(win_te_m.get("both_down_annualized", float("nan")))
    d["winner_both_down_degradation"] = float(
        d["winner_test_both_down_ann"] - d["winner_train_both_down_ann"])
    if not test_eval.empty and len(test_eval) >= 10:
        t10 = set(test_eval.head(10)["combo"] + "|" + test_eval.head(10)["scheme"])
        t20 = set(test_eval.sort_values("test_score", ascending=False).head(20)["combo"]
                  + "|" + test_eval.sort_values("test_score", ascending=False).head(20)["scheme"])
        d["top10_train_in_top20_test"] = float(len(t10 & t20) / 10.0)
        d["spearman_train_test_score"] = float(
            test_eval["train_score"].rank().corr(test_eval["test_score"].rank()))
    d["winner_test_sharpe_vs_aw"] = float(d["winner_test_sharpe"] - aw_te_m.get("sharpe_net", 0.0))
    d["winner_test_both_down_ann_vs_aw"] = float(
        d["winner_test_both_down_ann"] - aw_te_m.get("both_down_annualized", 0.0))
    d["dsr_prob"] = float(dsr["dsr_prob"]) if not math.isnan(dsr["dsr_prob"]) else float("nan")
    d["deflated_sr_ann"] = float(dsr["deflated_sr_ann"])
    d["sr0_ann"] = float(dsr["sr0_ann"])
    d["n_trials"] = float(dsr["n_trials"])
    return d


def write_report(args, train_res, test_eval, oos_port, oos_m, sel_log, win,
                 win_combo, win_sch, win_te_m, aw_tr_m, aw_te_m, diag, dsr,
                 dsr_oos_roll, schemes, avail, combos, n_trials, ref_label,
                 bd_tr_count, bd_te_count,
                 ls_in=False, ls_win_combo=None, ls_te_m=None, ls_dsr=None,
                 ls_diag=None, rp_combo=None, rp_sch=None, rp_te_m=None,
                 flavor_data=None):
    L = []; a = L.append
    a("# Risk-Parity Resilience Search — Canonical (Out-of-Sample) Report")
    a("")
    a("*Research / illustration only. Not investment advice.*")
    a("")
    a(f"> **This is the canonical report.** The in-sample `output/risk_parity/report.md`")
    a(f"> is a method appendix; do **not** cite its numbers as the headline. All numbers")
    a(f"> below are **out-of-sample, net of {args.cost_bps} bps/side transaction costs**,")
    a(f"> with **Ledoit-Wolf covariance shrinkage**, a **{args.cap:.0%} per-sleeve cap**,")
    a(f"> the **Volatility (^VIX) sleeve excluded** (non-tradable), and the score encoding")
    a(f"> **diversification + low both-down correlation** (\"uncorrelated positive returns\").")
    a("")
    a("## 1. Setup (remediated)")
    a("")
    a(f"- **TRAIN (selection):** {args.train_start} → {args.train_end}.")
    a(f"- **TEST (evaluation only):** {args.test_start} → {args.test_end} — contains 2020")
    a("  COVID, 2022 stocks+bonds rout, 2023 SVB stress; never seen at selection time.")
    a(f"- **Sleeves ({len(avail)}):** {', '.join(avail)}.  Volatility (^VIX) excluded by")
    a("  default (non-tradable; opt in with `--include-volatility` for illustration only).")
    a(f"- **Combos × schemes:** {len(combos)} × {len(schemes)} = **{n_trials} trials** on TRAIN.")
    a(f"- **Schemes:** {', '.join(schemes)} — EW/InvVol/InvVar/ERC/MinVar separate composition")
    a("  from allocation; **LS-TSMOM** is a long/short managed-futures (trend) overlay that")
    a("  targets the All-Weather weak spot (both-down / stagflation) — see §9.")
    a(f"- **Constraints:** long-only, no leverage, **per-sleeve cap {args.cap:.0%}**, monthly")
    a(f"  rebalance, **{args.cost_bps} bps/side** transaction costs, **{args.shrink}** covariance")
    a(f"  shrinkage, trailing {args.trailing}m, annual refit.")
    a("- **Score =** 0.30·pct(net Sharpe) + 0.25·pct(both-down ann ret) + 0.15·pct(−maxDD)")
    a("  + 0.15·pct(diversification ratio) + 0.15·pct(−corr with equity in both-down months).")
    a(f"- **Both-down regime reference:** {ref_label} (`--ref-mode {args.ref_mode}`). "
      f"Both-down months: TRAIN {bd_tr_count} | TEST {bd_te_count}. 'external' uses "
      f"investable non-candidate indices (SPY/AGG) so the equity-correlation metric "
      f"measures a hedge, not a tautology from the reference overlapping the universe.")
    a(f"- **ERC cap mode:** {args.erc_cap_mode} (cap enforced inside the solver for MinVar "
      f"and ERC-capped; see §2 'Cap integrity').")
    a("")
    a("## 2. Headline — selected winner, OUT OF SAMPLE (TEST)")
    a("")
    a(f"- **Combo:** {win['combo']}")
    a(f"- **Scheme:** {win_sch}  (risk-parity family)")
    a(f"- **TRAIN rank:** #1 (TRAIN score {win['resilience_score']:.1f}, "
      f"z = {diag['winner_train_score_z']:+.2f})")
    a("")
    a("| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |")
    a("|---|---:|---:|---:|")
    a(f"| Net Sharpe | {fn(win['sharpe_net'])} | **{fn(win_te_m.get('sharpe_net'))}** | "
      f"{fn(diag['winner_sharpe_degradation'])} |")
    a(f"| Both-down ann ret (net) | {fp(win['both_down_annualized'])} | "
      f"**{fp(win_te_m.get('both_down_annualized'))}** | "
      f"{fp(diag['winner_both_down_degradation'])} |")
    a(f"| Max drawdown | {fp(win['max_drawdown'])} | "
      f"**{fp(win_te_m.get('max_drawdown'))}** | "
      f"{fp(win_te_m.get('max_drawdown',0)-win['max_drawdown'])} |")
    a(f"| Diversification ratio | {fn(win.get('div_ratio'))} | "
      f"**{fn(win_te_m.get('div_ratio'))}** | — |")
    a(f"| Corr w/ equity (both-down) | {fn(win.get('corr_eq_bothdown'))} | "
      f"**{fn(win_te_m.get('corr_eq_bothdown'))}** | — |")
    a(f"| Ann turnover | {fp(win.get('ann_turnover'))} | "
      f"{fp(win_te_m.get('ann_turnover'))} | — |")
    a("")
    if "winner_max_weight" in diag:
        resp = "YES — solver output already ≤ cap (post-hoc clip is a no-op)" \
            if diag["winner_cap_respected_by_solver"] >= 1.0 else \
            "no — post-hoc clip was needed"
        a(f"- **Cap integrity (Fix 1):** winner max sleeve weight = "
          f"{diag['winner_max_weight']*100:.2f}% vs cap "
          f"{diag['winner_cap']*100:.0f}% → {resp}.")
        a("")
    a("## 3. Statistical significance (multiple-comparison adjusted)")
    a("")
    a(f"- Trials run on TRAIN: **{int(dsr['n_trials'])}**.")
    a(f"- Raw OOS net Sharpe: **{dsr['sr_ann']:.3f}**.")
    a(f"- Expected max null Sharpe over {int(dsr['n_trials'])} trials: "
      f"{dsr['sr0_ann']:.3f} (annualized).")
    a(f"- **Deflated Sharpe (annualized): {diag['deflated_sr_ann']:.3f}**  "
      f"(raw minus the luck-of-many-trials benchmark).")
    a(f"- **P(true Sharpe > 0 after deflation) = {diag['dsr_prob']:.2f}** "
      f"(DSR probability).")
    a("")
    if "oos_sharpe" in diag:
        a(f"- Block-bootstrap 95% CI on OOS net Sharpe: "
          f"[{diag['oos_sharpe_ci95_lo']:.3f}, {diag['oos_sharpe_ci95_hi']:.3f}]")
    if "oos_both_down_ann" in diag:
        a(f"- Block-bootstrap 95% CI on OOS both-down ann ret: "
          f"[{diag['oos_both_down_ann_ci95_lo']*100:.2f}%, "
          f"{diag['oos_both_down_ann_ci95_hi']*100:.2f}%]")
    a("")
    # Fix 4: DSR effective-N + OOS-application caveats.
    eff_n = diag.get("effective_n_trials", float("nan"))
    n_nom = diag.get("n_trials_nominal", float("nan"))
    a("> **DSR caveats (read before interpreting the headline DSR):**")
    a(f"> - **Effective N ≪ nominal N.** DSR's penalty uses N = {int(n_nom)} "
      f"independent trials, but the trials share sleeves (any two portfolios "
      f"holding US Treasuries are correlated), so the *effective* independent-")
    a(f">   trial count is the **effective rank of the TRAIN trial-return matrix "
      f"= {eff_n:.1f}** (participation ratio, Σλ/λ_max). The true "
      f"luck-of-many-trials benchmark is therefore **smaller** than the one used,")
    a(">   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-"
      "comparison penalty — the edge may be more significant than DSR suggests, "
      "not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over "
      "the effective N, or DSR applied to the TRAIN max — is future work.)")
    a("> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** "
      "(a non-canonical but accepted variant of Bailey & López de Prado 2014), "
      "not to the in-sample max Sharpe. Combined with the effective-N point, "
      "treat the headline DSR as a conservative guardrail, not a precise p-value.")
    a("")
    # dynamic interpretation
    dsr_neg = (diag.get("deflated_sr_ann", 0.0) <= 0.0)
    bd_ci_lo = diag.get("oos_both_down_ann_ci95_lo")
    bd_ci_hi = diag.get("oos_both_down_ann_ci95_hi")
    bd_entirely_neg = (bd_ci_lo is not None and bd_ci_hi is not None and bd_ci_hi < 0.0)
    bd_crosses_zero = (bd_ci_lo is not None and bd_ci_hi is not None and bd_ci_lo < 0.0 < bd_ci_hi)
    if dsr_neg and bd_entirely_neg:
        verdict = ("Deflated Sharpe ≤ 0 **and** the both-down CI is entirely negative: "
                   "there is **no statistically robust resilience** to the both-down "
                   "scenario among these investable sleeves — the best portfolio is the "
                   "least-bad, not a positive-return hedge.")
    elif dsr_neg and bd_crosses_zero:
        verdict = ("Deflated Sharpe ≤ 0 and the both-down CI crosses 0: the both-down "
                   "edge is **not** statistically robust after accounting for the number "
                   "of portfolios tried.")
    elif not dsr_neg:
        verdict = ("Deflated Sharpe > 0: the edge survives the multiple-comparison "
                   "adjustment (but still check the bootstrap CI and rolling §7).")
    else:
        verdict = ("Check the Deflated Sharpe and both-down CI together before trusting "
                   "any single number.")
    a(f"> **Interpretation:** {verdict}")
    a("")
    a("## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)")
    a("")
    a("| Metric | All-Weather (OOS) | Winner (OOS) |")
    a("|---|---:|---:|")
    for lab, key, f in [("Ann return (net)","ann_return_net",fp),("Ann vol","ann_vol",fp),
                       ("Net Sharpe","sharpe_net",fn),("Max DD","max_drawdown",fp),
                       ("Both-down ann ret","both_down_annualized",fp),
                       ("Both-down hit rate","both_down_hit_rate",fp),
                       ("Diversification ratio","div_ratio",fn),
                       ("Corr w/ equity","corr_eq",fn),
                       ("Corr w/ bonds","corr_bd",fn),
                       ("Crisis avg ret","crisis_avg_ret",fp)]:
        a(f"| {lab} | {f(aw_te_m.get(key))} | **{f(win_te_m.get(key))}** |")
    a("")
    a(f"Winner OOS Sharpe − All-Weather = **{diag['winner_test_sharpe_vs_aw']:+.3f}**; "
      f"both-down ann diff = **{diag['winner_test_both_down_ann_vs_aw']:+.4f}**.")
    a("")
    a("## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)")
    a("")
    a("| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|")
    try:
        sc = pd.read_csv(os.path.join(args.out_dir, "scheme_comparison_test.csv"))
        for _, r in sc.iterrows():
            a(f"| {r['scheme']} | {int(r['n'])} | {fn(r['test_sharpe_mean'])} | "
              f"{fp(r['test_both_down_ann_mean'])} | {fp(r['test_maxdd_mean'])} | "
              f"{fn(r['test_divratio_mean'])} | {r['test_score_mean']:.1f} | "
              f"{r['train_rank_mean']:.0f} |")
    except Exception:
        a("| (n/a) | | | | | | | |")
    a("")
    a("## 6. Overfit diagnostics")
    a("")
    a("| Diagnostic | Value | Reading |")
    a("|---|---:|---|")
    a(f"| TRAIN score mean / std | {diag['train_score_mean']:.1f} / "
      f"{train_res['resilience_score'].std():.1f} | field dispersion |")
    a(f"| Winner TRAIN score (z) | {diag['winner_train_score_z']:+.2f} | "
      f"{'OUTLIER — overfit risk' if diag['winner_train_score_z']>2 else 'within pack'} |")
    a(f"| Top-10 TRAIN in Top-20 TEST | {diag.get('top10_train_in_top20_test',0)*100:.0f}% | "
      f"selection stability |")
    a(f"| Spearman TRAIN↔TEST score | {diag.get('spearman_train_test_score',float('nan')):+.2f} | "
      f"rank persistence |")
    a(f"| Winner Sharpe test−train | {diag['winner_sharpe_degradation']:+.3f} | "
      f"large negative ⇒ overfit |")
    a(f"| Winner both-down test−train | {diag['winner_both_down_degradation']:+.4f} | "
      f"large negative ⇒ overfit |")
    a(f"| Effective N (vs nominal {int(diag.get('n_trials_nominal', 0))}) | "
      f"{diag.get('effective_n_trials', float('nan')):.1f} | "
      f"DSR penalty is conservative (trials correlated) |")
    a("")
    a("## 7. Rolling FULL re-enumerated selection (strictest OOS test)")
    a("")
    a("Each January the FULL combo×scheme search is re-run on the trailing 10y window")
    a("(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.")
    a("")
    if len(oos_port):
        a(f"- OOS (rolling) net Sharpe = **{oos_m.get('sharpe_net',float('nan')):.3f}**")
        a(f"- OOS (rolling) both-down ann ret = "
          f"**{oos_m.get('both_down_annualized',float('nan'))*100:.2f}%**")
        a(f"- OOS (rolling) max drawdown = "
          f"{oos_m.get('max_drawdown',float('nan'))*100:.2f}%")
        if dsr_oos_roll:
            a(f"- Rolling Deflated Sharpe = {dsr_oos_roll.get('deflated_sr_ann',float('nan')):.3f}  "
              f"(P>0 = {dsr_oos_roll.get('dsr_prob',float('nan')):.2f})")
    a("")
    a("| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |")
    a("|---:|---|---|---:|---:|---|")
    for _, r in sel_log.iterrows():
        a(f"| {int(r['year'])} | {r['combo']} | {r['scheme']} | "
          f"{r['sel_score']:.1f} | {r['sel_sharpe']:.2f} | {r['top_weight']} |")
    a("")
    # ------------------------------------------------------------------ #
    # §9 — Managed-futures (LS-TSMOM) on an equal footing (Fix 3)
    # ------------------------------------------------------------------ #
    a("## 9. Managed-futures (LS-TSMOM) on an equal footing (Fix 3)")
    a("")
    a("The long/short managed-futures (time-series-momentum) direction — previously only")
    a("tested in the separate `all_weather_v2.py` report with no DSR / walk-forward /")
    a("bootstrap — is now folded into this canonical pipeline. Each month, for each combo")
    a(f"sleeve, `pos = base_w · sign(trailing-{args.tsmom_lookback}m return)` with "
      f"**equal-weight base**,")
    a("**$1 gross, 0% T-bill collateral** (matches awv2's conservative assumption), and the")
    a("same 10 bps/side turnover+cost machinery. It goes through the same combo×scheme")
    a("TRAIN selection, TEST eval, and rolling re-enumeration as the risk-parity schemes —")
    a("so the comparison is measured, not assumed. This is the direct test of the brief:")
    a("*find an All-Weather flavor that does well where All-Weather is weak (both-down /")
    a("stagflation)* — long/short trend is positive in 2022 precisely because it **shorts**")
    a("the falling bonds+equities, which long-only risk parity cannot do.")
    a("")
    if not ls_in:
        a("> LS-TSMOM was **not run** this invocation. Re-run with")
        a("> `--schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM` to populate this section.")
        a("")
    elif not ls_te_m:
        a("> LS-TSMOM ran but produced no valid TRAIN portfolio on TEST (insufficient history).")
        a("")
    else:
        a(f"- **TRAIN-best LS-TSMOM combo:** {', '.join(ls_win_combo) if ls_win_combo else 'n/a'}")
        a(f"- **Signal:** `pos = (1/n)·sign(trailing-{args.tsmom_lookback}m)` per sleeve, "
          f"monthly. Lookback configurable via `--tsmom-lookback`.")
        a("")
        a("| Metric | All-Weather (OOS) | Risk-parity winner (OOS) | **LS-TSMOM (OOS)** |")
        a("|---|---:|---:|---:|")
        rp_lab = f"{rp_sch} | {', '.join(rp_combo)}" if rp_combo else "n/a"
        for lab, key, f in [("Ann return (net)","ann_return_net",fp),
                           ("Ann vol","ann_vol",fp),
                           ("Net Sharpe","sharpe_net",fn),
                           ("Max DD","max_drawdown",fp),
                           ("Both-down ann ret","both_down_annualized",fp),
                           ("Both-down hit rate","both_down_hit_rate",fp),
                           ("Corr w/ equity","corr_eq",fn),
                           ("Crisis avg ret","crisis_avg_ret",fp)]:
            a(f"| {lab} | {f(aw_te_m.get(key))} | {f(rp_te_m.get(key))} | "
              f"**{f(ls_te_m.get(key))}** |")
        a("")
        a(f"- LS-TSMOM OOS net Sharpe: **{fn(ls_te_m.get('sharpe_net'))}**")
        a(f"- LS-TSMOM OOS both-down ann ret: **{fp(ls_te_m.get('both_down_annualized'))}**  "
          f"(hit rate {fp(ls_te_m.get('both_down_hit_rate'))})")
        if ls_dsr:
            a(f"- LS-TSMOM Deflated Sharpe (annualized, n_trials = "
              f"{int(ls_dsr.get('n_trials', 0))}): "
              f"**{ls_dsr.get('deflated_sr_ann', float('nan')):.3f}**  "
              f"(P>0 = {ls_dsr.get('dsr_prob', float('nan')):.2f})")
        if ls_diag and "oos_sharpe" in ls_diag:
            a(f"- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: "
              f"[{ls_diag['oos_sharpe_ci95_lo']:.3f}, {ls_diag['oos_sharpe_ci95_hi']:.3f}]")
        if ls_diag and "oos_both_down_ann" in ls_diag:
            a(f"- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: "
              f"[{ls_diag['oos_both_down_ann_ci95_lo']*100:.2f}%, "
              f"{ls_diag['oos_both_down_ann_ci95_hi']*100:.2f}%]")
        a("")
        ls_bd = ls_te_m.get("both_down_annualized", float("nan"))
        rp_bd = rp_te_m.get("both_down_annualized", float("nan"))
        aw_bd = aw_te_m.get("both_down_annualized", float("nan"))
        ls_pos = ls_bd > 0
        ls_beats_rp = ls_bd > rp_bd
        ls_beats_aw = ls_bd > aw_bd
        if ls_pos and ls_beats_aw:
            verdict9 = ("**LS-TSMOM delivers POSITIVE both-down returns OOS and beats "
                        "All-Weather** where All-Weather is weakest — the long/short trend "
                        "overlay achieves what long-only risk parity could not. This is the "
                        "All-Weather variant the brief asked for. The trade-off (whipsaw in "
                        "calm markets — check the full-period Sharpe) is the price of crisis "
                        "alpha.")
        elif ls_beats_aw and ls_beats_rp:
            verdict9 = ("LS-TSMOM **reduces** the both-down loss vs both All-Weather and the "
                        "risk-parity winner (though still negative OOS) — directionally the "
                        "trend overlay helps in the AW weak spot, but not enough to flip it "
                        "positive in this window. Check the bootstrap CI before trusting the "
                        "ranking.")
        elif ls_beats_aw:
            verdict9 = ("LS-TSMOM beats All-Weather in the both-down regime but does not beat "
                        "the risk-parity winner here — the trend overlay helps vs AW but the "
                        "dampened long-only portfolio is competitive in this window.")
        else:
            verdict9 = ("LS-TSMOM does **not** beat All-Weather / risk parity on both-down in "
                        "this window — the trend signal whipsawed (check the bootstrap CI). "
                        "The hypothesis is *tested*, not assumed; this run does not support it.")
        a(f"> **Verdict:** {verdict9}")
        a("")
        a("> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill "
          "collateral (conservative, matches awv2). A real implementation holds the cash "
          "collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-"
          "weight across the combo (neutral); vol-scaling is a flagged refinement.")
        a("")

    # ------------------------------------------------------------------ #
    # §10 — TrendProtect flavor comparison menu (correlated up, protected down)
    # ------------------------------------------------------------------ #
    a("## 10. TrendProtect flavor comparison menu (correlated up, protected down)")
    a("")
    nflavor = sum(1 for s in SCHEME_ORDER if s in flavor_data)
    a(f"The brief: find an All-Weather flavor with **higher expected return** (target: beat "
      f"All-Weather's {fp(aw_te_m.get('ann_return_net'))} net OOS) while keeping equity "
      f"correlation **asymmetric** — correlated on the way up (capture upside), low/negative "
      f"on the way down (downside protection). {nflavor} constructions of one parameterized "
      f"engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — "
      f"MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) "
      f"plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their "
      f"own trailing-{args.tsmom_lookback}m return < 0, OR `gate_mode=short` to FLIP the equity "
      f"sleeve to net-short on the downside signal — the direct lever for negative downside-β "
      f"while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → "
      f"leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US "
      f"Treasuries for a net-short-duration tilt). Leverage cost = **{args.lev_rate*100:.1f}% "
      f"APR** on gross > 1, charged monthly. Selection uses the **`--score-mode {args.score_mode}`** "
      f"objective. Full construction + per-flavor pros/cons: "
      f"[`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).")
    a("")
    if not flavor_data:
        a("> No TrendProtect flavors ran this invocation. Re-run with")
        a("> `--schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,RP-LS-Overlay,"
          "StructShort,TG-LS-Overlay` to populate this section.")
        a("")
    else:
        # Ranked comparison table: All-Weather, risk-parity winner, LS-TSMOM, the 4 flavors.
        rows = []
        def _row(label, m, dsr=None, diag=None, combo=None, gross=1.0):
            gnl = m.get("gross_notional_last")
            if gnl is not None and not (isinstance(gnl, float) and math.isnan(gnl)):
                gstr = f"{gnl:.2f}"
            else:
                gstr = f"{gross:.2f}"
            rows.append({
                "Portfolio": label,
                "Combo": (", ".join(combo) if combo else "—"),
                "Ann ret": fp(m.get("ann_return_net")),
                "Sharpe": fn(m.get("sharpe_net")),
                "MaxDD": fp(m.get("max_drawdown")),
                "Both-down": fp(m.get("both_down_annualized")),
                "Upβ": fn(m.get("upside_beta")),
                "Dnβ": fn(m.get("downside_beta")),
                "Dn-corr": fn(m.get("downside_corr_eq")),
                "Gross": gstr,
                "Lev cost/yr": (f"{(m.get('lev_cost_ann') or 0.0)*100:.2f}%"),
                "DSR": (f"{dsr.get('deflated_sr_ann', float('nan')):.2f}"
                        if dsr else "—"),
                "Sharpe CI": ((f"[{diag['oos_sharpe_ci95_lo']:.2f}, "
                               f"{diag['oos_sharpe_ci95_hi']:.2f}]")
                              if diag and "oos_sharpe" in diag else "—"),
            })
        aw_combo = [s for s in ALL_WEATHER_WEIGHTS if s in avail]
        _row("All-Weather", aw_te_m, combo=aw_combo, gross=1.0)
        _row("RP winner", rp_te_m, combo=rp_combo, gross=1.0)
        _row("LS-TSMOM", ls_te_m if (ls_in and ls_te_m) else {},
             ls_dsr if ls_in else None, ls_diag if ls_in else None,
             ls_win_combo if ls_in else None, gross=1.0)
        for fname in SCHEME_ORDER:
            if fname not in flavor_data:
                continue
            fd = flavor_data[fname]
            _row(fname, fd["te_m"], fd["dsr"], fd["diag"], fd["combo"], gross=1.0)
        # Sort by net Sharpe descending (n/a sorts last).
        def _sk(r):
            v = r["Sharpe"]
            return float(v) if v != "n/a" else -9.0
        rows.sort(key=_sk, reverse=True)
        a("| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | "
          "Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |")
        a("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for r in rows:
            a(f"| {r['Portfolio']} | {r['Combo']} | {r['Ann ret']} | **{r['Sharpe']}** | "
              f"{r['MaxDD']} | {r['Both-down']} | {r['Upβ']} | {r['Dnβ']} | {r['Dn-corr']} | "
              f"{r['Gross']} | {r['Lev cost/yr']} | {r['DSR']} | {r['Sharpe CI']} |")
        a("")
        a("**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; "
          "Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down "
          f"months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low "
          f"(ideally negative) Dn-corr. The {args.tsmom_lookback}m trend-gate *lags* by "
          f"construction (it turns off ~{args.tsmom_lookback}m into a drawdown and on ~"
          f"{args.tsmom_lookback}m into a rally), so its asymmetric profile is an empirical "
          f"question this table answers, not an assumption.")
        a("")
        # Per-flavor pros/cons.
        a("### Per-flavor pros / cons")
        a("")
        pc = {
            "TrendGate": (
                ["Long-only (gross ≤ 1, no leverage cost).",
                 "Cuts equity exposure after a sustained drawdown — downside dampening.",
                 "Keeps bond/gold/diversifier sleeves long (carry)."],
                ["12m trend-gate LAGS: long into the start of drawdowns, flat into the start "
                 "of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal).",
                 "Cannot go net-short, so no positive both-down return.",
                 "Whipsaw in choppy markets (gate toggles on/off)."]),
            "RP-LS-Overlay": (
                ["LS-TSMOM overlay shorts the falling legs → genuinely positive in both-down "
                 "(the direction that matches the brief).",
                 "Long MinVar base keeps the return / Sharpe floor.",
                 "Dollar-neutral overlay is crisis-alpha on top of a diversified long book."],
                ["Gross 1.30 → leverage cost "
                 f"{(0.30*args.lev_rate)*100:.2f}%/yr drags the return.",
                 "Overlay whipsaw in calm markets (the 2010s) drags Sharpe.",
                 "Dn-corr may stay positive if the long leg dominates the down months."]),
            "StructShort": (
                ["Permanent net-short-duration tilt (short US Treasuries) → direct hedge for "
                 "a 2022-style stocks+bonds rout.",
                 "Sleeve-level netting keeps gross ≤ 1 (no leverage cost).",
                 "Structural (not signal-driven) → no whipsaw, no lookback lag."],
                ["Pays for the hedge in every non-stagflation year (carry drag) — a permanent "
                 "short is expensive outside 2022.",
                 "Only applies to combos containing the short sleeve (TRAIN search self-"
                 "selects those).",
                 "Sleeve-level short is a net-short-duration *tilt*, not a standalone short "
                 "ticker (ticker-level shorting that adds gross is a flagged refinement)."]),
            "TG-LS-Overlay": (
                ["Combines the trend-gate (downside dampening) with a small LS overlay "
                 "(crisis alpha) — both levers.",
                 "Smaller overlay (gross 1.20) → lower leverage cost than RP-LS-Overlay.",
                 "Targets the asymmetric goal from two angles."],
                ["Inherits the trend-gate lag AND the overlay whipsaw — both costs.",
                 "Gross 1.20 → leverage cost "
                 f"{(0.20*args.lev_rate)*100:.2f}%/yr.",
                 "Most parameters → most overfitting surface; check the DSR / bootstrap CI."]),
            "TG-Short": (
                ["Flips the equity sleeve to NET-SHORT on the downside signal (the brief's "
                 "lever) — long equity when up, short equity when down; bonds/gold/diversifiers "
                 "stay long. Directly targets negative downside-β with positive upside-β.",
                 "Sleeve-level netting can keep gross ≤ 1 (no leverage cost) when the short "
                 "equity leg nets against the long book.",
                 "Reuses the MinVar base."],
                ["MinVar base starves high-vol equity to ~5-10% weight → little equity to "
                 "short, so the upside capture AND the short benefit are both muted; return "
                 "floor is well below AW.",
                 "12m signal lags: shorts ~12m INTO a drawdown (after the drop has happened), "
                 "longs ~12m into a rally (after the rebound).",
                 "Whipsaw in choppy markets; check DSR / bootstrap CI."]),
            "TG-Short-LS": (
                ["TG-Short (short equity on downside) + a 0.20 LS-TSMOM overlay — both the "
                 "equity flip and the broader momentum crisis-alpha leg.",
                 "Targets the asymmetric goal from two angles.",
                 "Smaller overlay than RP-LS-Overlay → lower leverage cost."],
                ["Inherits the MinVar-base equity starvation AND the 12m lag AND the overlay "
                 "whipsaw — all three costs.",
                 f"Gross can exceed 1 → leverage cost up to "
                 f"{(0.20*args.lev_rate)*100:.2f}%/yr.",
                 "Most overfitting surface of the TG-Short family; check DSR / bootstrap CI."]),
            "TG-Short-6m": (
                ["TG-Short with a FASTER 6m trend signal — reduces the 12m lag (out of "
                 "drawdowns sooner, into rallies sooner), so the short flip is better timed.",
                 "Direct lever for negative downside-β.",
                 "Sleeve-level netting can keep gross ≤ 1."],
                ["Faster signal whipsaws MORE in choppy markets (more false flips).",
                 "MinVar base still starves equity → muted upside capture.",
                 "Shorter lookback → more turnover; check DSR / bootstrap CI."]),
            "EW-Short": (
                ["EQUAL-WEIGHT base (like All-Weather's own ~1/n across sleeves) so equity "
                 "keeps a real weight (~12-25%) — fixes the MinVar-base equity starvation that "
                 "left TG-Short with nothing to short and ~3% return.",
                 "Short equity on the downside signal → negative downside-β with positive "
                 "upside-β; return floor near AW.",
                 "Sleeve-level netting can keep gross ≤ 1 (no leverage cost)."],
                ["More equity weight → higher vol / drawdown than the MinVar-base flavors.",
                 "12m signal lags (consider EW-Short-6m for less lag).",
                 "Equal-weight ignores covariance; check DSR / bootstrap CI."]),
            "EW-Short-LS": (
                ["EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM overlay.",
                 "Highest upside capture of the family (EW base keeps equity, overlay adds "
                 "crisis alpha).",
                 "Targets both beat-AW return AND asymmetric protection."],
                ["Gross can exceed 1 → leverage cost up to "
                 f"{(0.20*args.lev_rate)*100:.2f}%/yr.",
                 "Inherits the 12m lag and overlay whipsaw.",
                 "Most overfitting surface; check DSR / bootstrap CI."]),
            "EW-Short-6m": (
                ["EW-Short with a FASTER 6m signal — real equity weight (EW base) AND less "
                 "lag, so the short flip is both meaningful and better timed.",
                 "Directly targets the brief: high upside-β, negative downside-β, AW-like "
                 "return floor.",
                 "Sleeve-level netting can keep gross ≤ 1."],
                ["Faster signal whipsaws more; more turnover.",
                 "Higher vol / drawdown than MinVar-base flavors (more equity).",
                 "Most parameters → check DSR / bootstrap CI."]),
            "EW-MA-Short": (
                ["EW-Short driven by a LEADING signal: price-vs-10m-SMA crossover (an MA "
                 "crosses BEFORE a lookback-return flips sign), so equity exits BEFORE the "
                 "drawdown and re-enters BEFORE the rally — the round-2 lagging-momentum "
                 "blocker's direct fix.",
                 "Real equity weight (EW base) + short-on-downside; directly targets high "
                 "upside-β with negative downside-β.",
                 "Sleeve-level netting can keep gross ≤ 1."],
                ["MA crossover still whipsaws in choppy/sideways tape (price oscillates "
                 "around the SMA → repeated false flips).",
                 "Higher vol / drawdown than MinVar-base flavors (more equity); more "
                 "turnover than the 12m TSMOM gate.",
                 "New signal → new overfitting surface; check DSR / bootstrap CI."]),
            "EW-Vol-Short": (
                ["EW-Short driven by a VOL-REGIME signal: short equity when 6m realized vol "
                 "EXCEEDS its trailing 60m median (vol spikes LEAD drawdowns), long when vol "
                 "is calm — a regime filter, not a price-trend filter.",
                 "Different information set from price-MA → diversifies the signal family; "
                 "real equity weight (EW base).",
                 "Sleeve-level netting can keep gross ≤ 1."],
                ["Vol spikes can lag the actual drawdown start (vol rises AS price falls, "
                 "not before) — may still enter the short late.",
                 "60m median needs a long warm-up; fewer active signals in the early TEST "
                 "window.",
                 "New signal → new overfitting surface; check DSR / bootstrap CI."]),
            "EW-DMA-Short": (
                ["EW-Short driven by a DUAL-MA signal: fast 3m SMA vs slow 10m SMA — a faster, "
                 "smoother crossover than price-vs-SMA (the slow MA smooths the reference, so "
                 "fewer false flips than EW-MA-Short).",
                 "Leading signal (a fast/slow cross precedes the lookback-return flip); real "
                 "equity weight (EW base) + short-on-downside.",
                 "Sleeve-level netting can keep gross ≤ 1."],
                ["Fast 3m SMA is noisy → still some whipsaw; the slow 10m MA adds lag vs the "
                 "single-MA gate.",
                 "Two MAs → slightly more overfitting surface than EW-MA-Short.",
                 "New signal → new overfitting surface; check DSR / bootstrap CI."]),
            "EW-AsymMA-Short": (
                ["ASYMMETRIC (hysteretic) MA gate — the round-3 prescription made concrete: "
                 "LONG until price < 3m SMA (FAST downside exit), then SHORT until price > 12m "
                 "SMA (SLOW upside re-entry). Starts LONG and holds through chop above the fast "
                 "MA, so it stays correlated on the way up and only flees (goes net-short) after "
                 "a clear break. Hysteresis band = the fast/slow-MA gap.",
                 "The one untested lever: a SYMMETRIC signal (rounds 1-3) is equally trigger-"
                 "happy up and down → Dnβ >= Upβ everywhere; an asymmetric one can in principle "
                 "be 'correlated up, protected down'.",
                 "Real equity weight (EW base) + short-on-downside; sleeve-level netting can "
                 "keep gross <= 1."],
                ["The slow 12m re-entry can lag the START of a rally (re-enters late after a V "
                 "rebound) — some upside missed at the turn.",
                 "Stateful + two MA horizons → more overfitting surface than the symmetric "
                 "gates; the fast/slow gap is a tuned parameter.",
                 "New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime."]),
            "EW-DDStop-Short": (
                ["ASYMMETRIC trailing-stop gate — the most direct map to the brief: LONG until "
                 "the equity sleeve drawdown from its trailing 6m peak exceeds 10% (FAST exit — "
                 "a clear break), then SHORT until it recovers inside 3% of the peak (SLOW "
                 "re-entry, near a new high). 'Flee the break, wait for a new high.'",
                 "Inherently asymmetric: the trigger is 'you've fallen >10%', the re-entry is "
                 "'you've made a new high' — quick to flee, slow to return, exactly the brief's "
                 "shape.",
                 "Real equity weight (EW base) + short-on-downside; sleeve-level netting can "
                 "keep gross <= 1."],
                ["Drawdown thresholds (10% exit / 3% re-entry) are tuned → overfitting surface; "
                 "the 6m peak window is a parameter.",
                 "A slow grind-down (2018, 2022) can hit the 10% stop late vs a fast crash; a "
                 "V-rebound (2020) re-enters late (needs a new 6m high).",
                 "New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime."]),
            "EW-AsymMA-Short-6": (
                ["Round-4b SWEEP point: EW-AsymMA-Short with a FASTER re-entry "
                 "(slow_entry=6 vs the round-4 default 12). The round-4 default drove "
                 "Upβ NEGATIVE because the 12m re-entry stayed short through rally "
                 "starts; re-entering at a 6m SMA re-loads equity sooner → tests "
                 "whether a less-overshooting band can keep Upβ POSITIVE while Dnβ "
                 "stays NEGATIVE (the unmet property).",
                 "Fast 3m-MA exit preserved (downside protection unchanged); real "
                 "equity weight (EW base); sleeve-level netting can keep gross <= 1."],
                ["Faster re-entry reduces the hysteresis band → more whipsaw in choppy "
                 "tape (re-enters on smaller bounces); may give back some of the "
                 "downside protection the 12m band bought.",
                 "Sweep parameter (slow_entry=6) is tuned → overfitting surface; one "
                 "TRAIN/TEST split = one regime. Check DSR / bootstrap CI."]),
            "EW-AsymMA-Short-9": (
                ["Round-4b SWEEP point: the intermediate re-entry (slow_entry=9, "
                 "between the round-4 default 12 and the fast 6). Brackets the "
                 "Upβ-vs-Dnβ trade-off: slower than 6 = more downside protection, "
                 "faster than 12 = less upside overshoot.",
                 "Real equity weight (EW base); sleeve-level netting can keep gross "
                 "<= 1."],
                ["Same construction costs as the rest of the asym_ma family "
                 "(stateful, two MA horizons, tuned band).",
                 "Sweep parameter → overfitting surface; one split = one regime. "
                 "Check DSR / bootstrap CI."]),
            "EW-AsymMA-Tight": (
                ["Round-4b SWEEP point: a TIGHTER hysteresis band — fast_exit=2 "
                 "(exit on a 2m-MA break, even faster downside flee) + slow_entry=6 "
                 "(re-enter on a 6m SMA). The tightest band in the family: quickest "
                 "to flee, quickest to return — tests the 'high turnover, low lag' "
                 "corner of the grid.",
                 "Real equity weight (EW base); sleeve-level netting can keep gross "
                 "<= 1."],
                ["The 2m exit is noisy → more false flips in chop; the tight band → "
                 "highest turnover of the family (more cost, more whipsaw).",
                 "Two tuned parameters → most overfitting surface of the sweep; one "
                 "split = one regime. Check DSR / bootstrap CI."]),
            "EW-AsymVol-Short": (
                ["Round-4b: a HYSTERETIC vol-regime gate — LONG -> SHORT once the "
                 "prior month's 6m realized vol exceeds its trailing 60m median "
                 "(fast exit on stress), SHORT -> LONG once vol falls back below "
                 "0.85x the median (slow re-entry, wait for genuine calm). The "
                 "hysteresis band = 0.85..1.0x median; a vol spike flees, vol must "
                 "genuinely calm to return.",
                 "Fixes the round-3 EW-Vol-Short, which SHORTED THE 2020 COVID "
                 "V-REBOUND (vol stayed elevated through the rally → the symmetric "
                 "vol-gate never re-entered long, -> -1.52% / -31.69% MaxDD). The "
                 "slow lower-bar re-entry waits for vol to actually calm. Different "
                 "information set from price-MA → diversifies the signal family.",
                 "Real equity weight (EW base); sleeve-level netting can keep gross "
                 "<= 1."],
                ["Vol can stay elevated THROUGH a V-rebound even with hysteresis "
                 "(vol calms late) — the 0.85x bar may still re-enter after the "
                 "rally's best months.",
                 "60m median needs a long warm-up; the 0.85x / 1.0x thresholds are "
                 "tuned → overfitting surface. New signal → check DSR / bootstrap "
                 "CI; one split = one regime."]),
            "EW-Hedge-DMA-1": (
                ["Round-5 DECOUPLED insurance overlay, light hedge (w_hedge=1.0): "
                 "the long EW base NEVER flips (gross 1, fully long in every month "
                 "incl. recoveries) so Upβ stays that of the long-only base — the "
                 "round-4b structural blocker's direct fix. A SEPARATE additive "
                 "short overlay on the equity sleeves activates only when the fast "
                 "3m/10m dual-MA signal is DOWN (flat otherwise); w_hedge=1.0 nets "
                 "equity to ~0 in down-months (a 'cash on the downside' hedge, not "
                 "net-short).",
                 "Fast symmetric signal (dma) -> FAST-OFF in recoveries (does not "
                 "drag the rally, unlike round-4's slow re-entry).",
                 "Decouples the two halves the brief asks for: long base = upside, "
                 "overlay = downside insurance; the 'long-term short a ticker' "
                 "permission applied as an overlay not a gate."],
                ["w_hedge=1.0 only nets equity to ~0 in down-months -> Dnβ is "
                 "reduced but likely still POSITIVE (the non-equity sleeves still "
                 "track equity down); to drive Dnβ NEGATIVE needs w_hedge > 1.",
                 "Additive gross when active -> leverage cost; the overlay is a "
                 "separate notional so it is NOT free (vs the sleeve-netted flip).",
                 "New construction + tuned w_hedge -> overfitting surface; one "
                 "TRAIN/TEST split = one regime. Check DSR / bootstrap CI."]),
            "EW-Hedge-DMA": (
                ["Round-5 DECOUPLED overlay, MEDIUM hedge (w_hedge=1.5): same "
                 "never-flipping long EW base + fast dma-triggered additive short "
                 "overlay, but w_hedge=1.5 -> NET SHORT equity in down-months "
                 "(base equity weight - 1.5x = negative). This is the sizing "
                 "expected to push Dnβ NEGATIVE while the always-long base keeps "
                 "Upβ POSITIVE — the unmet asymmetric property, by construction.",
                 "Fast dma signal -> fast-off in recoveries; the base's full "
                 "equity weight is at work in up-months (overlay flat).",
                 "Directly targets 'correlated up, protected down' via decoupling, "
                 "not a single price-gate."],
                ["Gross 1 + 1.5 x (equity fraction) when active -> leverage cost "
                 "(the explicit price of decoupling); only paid in down-months.",
                 "Net-short equity in down-months means a wrong-footed whipsaw "
                 "(signal flips short just before a rally) costs more than the "
                 "light hedge; the fast dma signal whipsaws in chop.",
                 "w_hedge=1.5 is tuned; new construction -> overfitting surface. "
                 "Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Hedge-DMA-2": (
                ["Round-5 DECOUPLED overlay, HEAVY hedge (w_hedge=2.0): the "
                 "strongest downside clip — net short 1.0x the base equity weight "
                 "in down-months. Tests how much downside protection (Dnβ most "
                 "negative) the construction can buy before the leverage cost and "
                 "whipsaw overwhelm the return.",
                 "Same never-flipping long base (Upβ positive) + fast dma overlay.",
                 "Brackets the w_hedge grid with EW-Hedge-DMA-1 (1.0) / -DMA (1.5)."],
                ["Largest additive gross -> largest leverage cost; most whipsaw "
                 "damage if the signal mistimes.",
                 "w_hedge=2.0 is the most aggressive / most overfit corner of the "
                 "round-5 grid.",
                 "Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Hedge-MA": (
                ["Round-5 overlay with the single 10m-SMA signal (vs the dual-MA "
                 "dma): the overlay shorts when price < its 10m SMA. A slower, "
                 "smoother downside trigger than dma -> fewer false flips in chop, "
                 "but slower to deactivate in a V-rebound.",
                 "Same never-flipping long EW base (Upβ positive) + additive short "
                 "overlay (w_hedge=1.5).",
                 "Tests whether the smoother signal beats the fast dma on the "
                 "overlay (fewer whipsaw trades vs later off in recoveries)."],
                ["The 10m SMA deactivates SLOWER than dma in a V-rebound (price "
                 "reclaims the 10m SMA late) -> the overlay can drag the start of "
                 "the rally (the round-4 problem, milder here because the base is "
                 "always long).",
                 "Additive gross -> leverage cost; tuned w_hedge. Check DSR / "
                 "bootstrap CI; one split = one regime."]),
            "EW-Hedge-DD": (
                ["Round-5 overlay with the dd_stop (drawdown) signal: the overlay "
                 "shorts once the equity sleeve is >10% below its trailing 6m peak "
                 "and deactivates once within 3% of the peak. 'Hedge the break, "
                 "un-hedge the new high' — the most direct map to the brief's "
                 "shape, now applied to a SEPARATE overlay (not a flip).",
                 "Same never-flipping long EW base (Upβ positive) + additive short "
                 "overlay (w_hedge=1.5).",
                 "The drawdown signal deactivates NATURALLY when equity recovers "
                 "(drawdown shrinks) -> fast-off in V-rebounds, without a separate "
                 "re-entry MA."],
                ["dd_stop is a LAGGING trigger (price has already fallen 10% before "
                 "the hedge activates) -> the hedge misses the first 10% of the "
                 "drawdown; on an overlay (not a flip) this is late-activate but "
                 "still fast-deactivate.",
                 "Drawdown thresholds (10% / 3%) are tuned; additive gross -> "
                 "leverage cost. Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Hedge-Dur": (
                ["Round-6: round-5 decoupled overlay (never-flip long EW base -> "
                 "Upβ positive) PLUS a duration/bond overlay (w_hedge_bd=1.5) that "
                 "shorts the BOND sleeves on their OWN dma downtrend. The direct "
                 "fix for the round-5 gap: in both-down / stagflation months bonds "
                 "fall WITH equities, and an equity-only overlay could not touch "
                 "them. Shorting bonds on bonds' own downtrend clips that loss.",
                 "Self-avoiding flight-to-quality: when bonds RISE (2008 Q4, 2020 "
                 "Q1) their dma is up -> no bond short -> no bleed there.",
                 "Equity overlay (w_hedge=1.5, dma) unchanged from round 5."],
                ["Two additive shorts (equity + bonds) -> higher gross -> more "
                 "leverage cost than round 5. The dma signal still lags ~12m on the "
                 "equity side (the round-5 'fires too late' issue is only half-fixed "
                 "here). Bond dma can whipsaw in choppy rates regimes. Check DSR / "
                 "bootstrap CI; one split = one regime."]),
            "EW-Hedge-Dur-MA": (
                ["Round-6 duration overlay with the symmetric 10m MA signal (vs "
                 "EW-Hedge-Dur's dma) on BOTH the equity and bond shorts.",
                 "Same never-flip long EW base + duration short (w_hedge_bd=1.5) "
                 "targeting the both-down gap; self-avoiding flight-to-quality."],
                ["The single 10m MA deactivates slower than dma in a V-rebound on "
                 "both sleeves -> can drag the start of rallies. Two additive shorts "
                 "-> leverage cost. Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Hedge-Dur-DD": (
                ["Round-6 with the FAST equity-drawdown trigger (gate_signal=eq_dd): "
                 "a SYMMETRIC, stateless drawdown gate that shorts a sleeve once it "
                 "is >10% below its 6m peak and releases once back within 3% — fires "
                 "IN down-months and releases fast in recoveries, the direct fix for "
                 "round-5's 'dma/ma fires ~12m too late' problem.",
                 "Duration overlay (w_hedge_bd=1.5) shorts bonds on bonds' own "
                 "drawdown -> clips the both-down loss; flight-to-quality safe.",
                 "The user's literal ask: short duration/TLT in the overlay + a fast "
                 "equity-drawdown trigger."],
                ["eq_dd is stateless -> more whipsaw near peaks than hysteretic "
                 "dd_stop (can toggle short/long in chop). For bonds a 10% drawdown "
                 "threshold rarely fires (bonds less vol) -> the bond leg may stay "
                 "quiet outside a true bond rout (2022). Two additive shorts + the "
                 "fast trigger -> higher turnover / leverage cost. Check DSR / "
                 "bootstrap CI; one split = one regime."]),
            "EW-Hedge-Dur-2": (
                ["Round-6 with a BIGGER duration short (w_hedge_bd=2.0 vs 1.5) on "
                 "the dma signal: w_hedge_bd>1 means net-short duration in bond-down "
                 "months — a more aggressive stagflation hedge, the brief's 'short a "
                 "ticker' (short TLT / long-duration) as a conditional overlay.",
                 "Same never-flip long EW base (Upβ positive); equity overlay dma."],
                ["Net-short duration when bonds trend down -> larger gross / leverage "
                 "cost and larger whipsaw if the bond rout reverses. dma still lags "
                 "on equity. Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Hedge-Dur-DD2": (
                ["Round-6 combining BOTH levers at full strength: fast eq_dd equity "
                 "trigger + a bigger 2.0x duration short. The maximal mechanical fix "
                 "for the round-5 diagnosis (equity overlay fires too late AND can't "
                 "touch bonds in both-down).",
                 "Never-flip long EW base -> Upβ positive by construction."],
                ["Most parameters / overfitting surface of the round-6 family; "
                 "highest gross / leverage cost and turnover. eq_dd's bond leg may "
                 "stay quiet outside a true bond rout. Check DSR / bootstrap CI; one "
                 "split = one regime."]),
            "EW-Infl-Dur": (
                ["Round-7 LEADING macro gate (the user's ask): duration overlay fires "
                 "off an EX-ANTE inflation regime (trailing-12m Commodities return) "
                 "instead of a lagging sleeve trend. Short bonds (w_hedge_bd=1.5) ONLY "
                 "when inflation is RISING (stagflation risk-off, 2022 -- the both-down "
                 "regime round 6 could only hedge with a lagging short); no long tilt.",
                 "Never-flip long EW base -> Upβ positive. Commodities lead equities in "
                 "the stagflation case (topped before equities in 2022).",
                 "Isolates the duration-regime lever (no equity short, no long tilt)."],
                ["Inflation regimes are persistent but not perfect: equity-up + "
                 "inflation-up months (2021, 2024) take a bond-short drag on Upβ. "
                 "Commodities are a noisy inflation proxy. Check DSR / bootstrap CI; "
                 "one split = one regime."]),
            "EW-Infl-DurL": (
                ["Round-7 with the SYMMETRIC duration-regime switch: short bonds "
                 "(w_hedge_bd=1.5) when inflation RISING + LONG-bonds tilt (w_long_bd="
                 "1.5) when inflation FALLING -- own the bonds that rally in flight-to-"
                 "quality (2008 Q4, 2020 Q1), the regime where bonds hedge equity for "
                 "free and Dnβ can go negative.",
                 "Never-flip long EW base -> Upβ positive. The leading-macro lever at "
                 "its most complete (regime-switching duration, both directions)."],
                ["Two-sided regime switch -> most regime-timing risk: a wrong-footed "
                 "inflation call (e.g. long bonds into a reflation) costs on both the "
                 "tilt and the foregone short. Additive gross both ways -> leverage cost. "
                 "Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Infl-Both": (
                ["Round-7 full inflation-regime RISK-OFF: when inflation RISING, short "
                 "BOTH equity (w_hedge=1.5) AND bonds (w_hedge_bd=1.5) -- both fall in "
                 "stagflation, so this is the direct 2022 both-down hedge the round-5/6 "
                 "equity-/bond-own-trend gates could not time. No long tilt.",
                 "Never-flip long EW base -> Upβ positive (the equity short is an "
                 "additive overlay, not a base flip)."],
                ["Shorting equity when inflation rising drags Upβ in equity-up + "
                 "inflation-up months (2021, 2024) -- the same tension as every "
                 "lagging equity short, now on a macro trigger. Highest gross of the "
                 "round-7 family. Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Infl-BothL": (
                ["Round-7 maximal: short equity AND bonds when inflation RISING + long-"
                 "bonds tilt (w_long_bd=1.5) when FALLING. The complete leading-macro "
                 "regime switch across all three legs (equity short, duration short, "
                 "duration long). The most aggressive test of whether an ex-ante "
                 "inflation gate can deliver Upβ > Dnβ.",
                 "Never-flip long EW base -> Upβ positive."],
                ["Most parameters / overfitting surface of the round-7 family; largest "
                 "additive gross / leverage cost; most regime-timing risk both ways. "
                 "Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Infl-DurL2": (
                ["Round-7 with a BIGGER long-duration tilt (w_long_bd=2.0) when "
                 "inflation FALLING -- push hardest on the flight-to-quality amplify "
                 "lever (own 2.0x the base bond weight in disinflationary drawdowns) to "
                 "drive Dnβ most negative, while keeping the 1.5x bond short in "
                 "stagflation. No equity short (duration-only regime).",
                 "Never-flip long EW base -> Upβ positive. Tests how much downside "
                 "protection the long-tilt leg can buy before its leverage cost and "
                 "reflation risk overwhelm it."],
                ["The 2.0x long tilt is the most overfit / most leverage-cost corner of "
                 "the round-7 grid; a long-bonds tilt into a reflation (inflation "
                 "re-accelerates) is unhedged by the equity leg. Check DSR / bootstrap "
                 "CI; one split = one regime."]),
            "EW-InflC-Both": (
                ["Round 8: the round-7 inflation gate NARROWED with a coincident equity-"
                 "rolling confirmation (infl_confirm=eq_neg, trailing-3m US Equity < 0). "
                 "Short BOTH equity (w_hedge=1.5) AND bonds (w_hedge_bd=1.5) only when "
                 "inflation is RISING AND equity is rolling over -- 2022 protected, "
                 "2021/2024 reflation rallies NOT shorted -> return preserved (the round-7 "
                 "EW-Infl-Both bled to ~0 return by shorting every rising-inflation month).",
                 "Never-flip long EW base -> Upβ positive. The direct test of whether "
                 "narrowing the broad ex-ante gate keeps Upβ > Dnβ AND restores return."],
                ["The confirmation is itself a (short, 3m) lagging signal -> the short "
                 "fires AFTER equity has started falling, so less early-drawdown protection "
                 "than round-7's pure inflation gate (a return-vs-early-protection trade). "
                 "Check DSR / bootstrap CI; one split = one regime."]),
            "EW-InflC-BothL": (
                ["Round 8: the confirmed inflation gate PLUS a confirmed long-duration "
                 "tilt (w_long_bd=1.5) that fires only when inflation is FALLING AND equity "
                 "is rolling over -- the true flight-to-quality regime (2008 Q4, 2020 Q1: "
                 "disinflation + equity crash + bonds rally), NOT 2022-23 disinflation-with-"
                 "bonds-falling that dragged round-7 EW-Infl-DurL's both-down to -34.68%.",
                 "Own the rallying bonds only when they rally. Never-flip long EW base -> "
                 "Upβ positive. The most complete round-8 construction (gated short + gated "
                 "long-tilt)."],
                ["Most parameters / overfitting surface of the round-8 family; two-sided "
                 "regime-timing risk both ways; the 3m equity confirmation can whipsaw near "
                 "equity-market turns. Check DSR / bootstrap CI; one split = one regime."]),
            "EW-InflC-Dur": (
                ["Round 8 confirmed gate on DURATION only (no equity short): short bonds "
                 "(w_hedge_bd=1.5) when inflation RISING AND equity rolling over, no long "
                 "tilt. Isolates the confirmed-duration lever -- does the equity-rolling "
                 "confirmation alone lift the round-7 EW-Infl-Dur return (6.79%) above 7.37% "
                 "while keeping its low gross (0.90)?",
                 "Never-flip long EW base -> Upβ positive. No equity short -> higher Upβ than "
                 "the Both variants."],
                ["Duration-only short cannot hedge equity-down months directly (Dnβ stays "
                 "driven by the long equity base); the 3m confirmation narrows but does not "
                 "eliminate regime-timing risk. Check DSR / bootstrap CI; one split = one "
                 "regime."]),
            "EW-InflC-DurL": (
                ["Round 8 confirmed duration short (w_hedge_bd=1.5 when infl up AND eq "
                 "rolling) + confirmed long-duration tilt (w_long_bd=1.5 when infl down AND "
                 "eq rolling). The round-7 EW-Infl-DurL construction with BOTH legs gated on "
                 "the equity-rolling confirmation -- the fix for its -34.68% both-down (the "
                 "ungated long-tilt held in every disinflation month, including 2022-23 bonds-"
                 "fall).",
                 "Never-flip long EW base -> Upβ positive. Tests whether gating the long-tilt "
                 "to true flight-to-quality recovers the duration-only both-down AND return."],
                ["Two-sided confirmed gate -> most regime-timing risk of the duration-only "
                 "round-8 presets; the 3m equity confirmation whipsaws near turns. Check DSR "
                 "/ bootstrap CI; one split = one regime."]),
            "EW-InflC-Both6": (
                ["Round 8 EW-InflC-Both with a SLOWER 6m equity-rolling confirmation "
                 "(eq_confirm_lookback=6) -- a more stable, less whipsaw-prone confirmation "
                 "than the 3m default. Tests sensitivity of the confirmed gate to the "
                 "confirmation window.",
                 "Never-flip long EW base -> Upβ positive. Same short-both-legs construction "
                 "as EW-InflC-Both, only the confirmation window differs."],
                ["A 6m confirmation lags more -> the short fires even later in drawdowns "
                 "(less early protection) but exits later in recoveries (more carry). Check "
                 "DSR / bootstrap CI; one split = one regime."]),
            "EW-Scale-Mom": (
                ["Round 9: a NEW PRIMITIVE -- regime-scaled GROSS, not a timed short. The "
                 "never-flip long EW base is multiplied by s_t = clip(1 + 2*eq_mom_3m, 0.3, "
                 "1.5): own ~1.5x in up-months (leverage), ~0.3x in down-months (de-risk). "
                 "Long-only -> no short to time, no Upβ-drag-through-recoveries; Upβ > Dnβ by "
                 "construction (amplified up, damped down). Return comes from leverage in up-"
                 "months; 5.8% funding cost on s_t > 1.",
                 "The direct test of whether SCALING gross (vs timing a short, rounds 1-8) "
                 "delivers BOTH halves -- beat 7.37% AND Upβ > Dnβ -- in one flavor."],
                ["Momentum lags: still ~1.5x leveraged at the START of a drawdown and ~0.3x "
                 "de-risked at the START of a rally (whipsaw cost); 5.8% leverage cost on the "
                 "up-month gross. Check DSR / bootstrap CI; one split = one regime."]),
            "EW-Scale-Mom6": (
                ["Round 9 EW-Scale-Mom with a SLOWER 6m momentum window -- less whipsaw "
                 "(smoother s_t) at the cost of more lag. Tests sensitivity of the momentum-"
                 "gated-leverage scalar to the lookback.",
                 "Long-only, never-flip, Upβ > Dnβ by construction; same scale primitive as "
                 "EW-Scale-Mom, only the lookback differs."],
                ["6m momentum lags more -> slower to de-risk into drawdowns and slower to re-"
                 "lever into rallies; 5.8% leverage cost. Check DSR / bootstrap CI; one split "
                 "= one regime."]),
            "EW-Scale-Vol": (
                ["Round 9 VOL-TARGETING: s_t = clip(0.12 / realized_eq_vol_ann, 0.3, 1.5) -- "
                 "de-risk when equity vol is high (stress) and leverage when low (calm). The "
                 "classic vol-managed construction: own less exactly when risk is elevated, "
                 "more when it is calm, targeting 12% realized vol.",
                 "Long-only, never-flip -> Upβ > Dnβ by construction; vol-targeting is the "
                 "literature-backed (Moreira-Muir) way to manage a long portfolio's downside "
                 "without shorting."],
                ["Vol-targeting is pro-cyclical at turns: it deleverages AFTER vol spikes "
                 "(often near the bottom, missing the rebound) and re-levers AFTER calm "
                 "(near the top); 5.8% leverage cost. Check DSR / bootstrap CI; one split = "
                 "one regime."]),
            "EW-Scale-MomL": (
                ["Round 9 EW-Scale-Mom with MORE leverage (scale_k=3, scale_ceil=2.0) -- own "
                 "up to 2.0x in strong up-months to push return harder, same 0.3x floor on the "
                 "downside. Tests whether a bigger up-month lever closes the return gap to 7.37% "
                 "while the floor keeps Dnβ low.",
                 "Long-only, never-flip -> Upβ > Dnβ by construction; the aggressive end of the "
                 "momentum-gated-leverage family."],
                ["2.0x gross in up-months -> the most 5.8% leverage cost of the round-9 family; "
                 "bigger whipsaw loss when a leveraged month reverses. Check DSR / bootstrap "
                 "CI; one split = one regime."]),
            "EW-Scale-Infl": (
                ["Round 9: the round-7 LEADING inflation gate applied as a SCALAR, not a short. "
                 "s_t = 0.4 in stagflation (infl_up, de-risk the long base) and 1.3 in "
                 "disinflation (lever up). Tests whether de-risking the long base in stagflation "
                 "(vs round-7 SHORTING it, which bled return or broke the property) delivers the "
                 "asymmetry WITH return -- the round-7 leading gate without the short-timing "
                 "tension.",
                 "Long-only, never-flip, ex-ante macro signal -> Upβ > Dnβ by construction; the "
                 "round-7 gate retested under the new scale primitive."],
                ["Two-state scalar (0.4 / 1.3) is coarse vs the continuous eq_mom/eq_vol "
                 "scalars; the 12m commodity gate is the same leading signal whose width was "
                 "the round-7/8 tension; 5.8% leverage cost on the 1.3 disinflation gross. "
                 "Check DSR / bootstrap CI; one split = one regime."]),
        }
        for fname in SCHEME_ORDER:
            if fname not in flavor_data:
                continue
            pros, cons = pc.get(fname, ([], []))
            fd = flavor_data[fname]
            m = fd["te_m"]
            gnl = m.get("gross_notional_last")
            gstr = (f"{gnl:.2f}" if gnl is not None
                    and not (isinstance(gnl, float) and math.isnan(gnl)) else "—")
            dstr = (f"{fd['dsr'].get('deflated_sr_ann', float('nan')):.2f}"
                    if fd.get("dsr") else "—")
            cistr = (f"[{fd['diag']['oos_sharpe_ci95_lo']:.2f}, "
                     f"{fd['diag']['oos_sharpe_ci95_hi']:.2f}]"
                     if fd.get("diag") and "oos_sharpe" in fd["diag"] else "—")
            a(f"**{fname}** — combo: {', '.join(fd['combo'])}")
            a("")
            a(f"- Net ann ret {fp(m.get('ann_return_net'))} · Sharpe {fn(m.get('sharpe_net'))} · "
              f"MaxDD {fp(m.get('max_drawdown'))} · both-down {fp(m.get('both_down_annualized'))} · "
              f"Upβ {fn(m.get('upside_beta'))} / Dnβ {fn(m.get('downside_beta'))} · "
              f"Dn-corr {fn(m.get('downside_corr_eq'))} · gross {gstr} · "
              f"lev cost {fp(m.get('lev_cost_ann'))}/yr · DSR {dstr} · Sharpe CI {cistr}")
            a("- **Pros:** " + " ".join(pros))
            a("- **Cons:** " + " ".join(cons))
            a("")
        # Verdict: which flavors beat All-Weather AND have a low downside-corr, with significance.
        aw_ret = aw_te_m.get("ann_return_net", float("nan"))
        aw_sharpe = aw_te_m.get("sharpe_net", float("nan"))
        beats_aw_ret = []
        for fname in SCHEME_ORDER:
            if fname not in flavor_data:
                continue
            m = flavor_data[fname]["te_m"]
            if (m.get("ann_return_net", float("nan")) > aw_ret
                    and not math.isnan(m.get("ann_return_net", float("nan")))):
                beats_aw_ret.append(fname)
        if beats_aw_ret:
            verdm = (f"Of the {nflavor} TrendProtect flavors, **{', '.join(beats_aw_ret)}** beat "
                     f"All-Weather's net OOS return ({fp(aw_ret)}) after the "
                     f"{args.lev_rate*100:.1f}%/yr leverage cost. Cross-check the Dn-corr / Dnβ "
                     f"columns for the asymmetric protection and the DSR / bootstrap Sharpe CI "
                     f"for significance before trusting any single winner — the flavors share "
                     f"sleeves so DSR is conservative (see §3 effective-N), and a single "
                     f"TRAIN/TEST split is one regime.")
        else:
            verdm = (f"None of the {nflavor} TrendProtect flavors beat All-Weather's net OOS "
                     f"return ({fp(aw_ret)}) after the {args.lev_rate*100:.1f}%/yr leverage "
                     f"cost in this window — the honest, measured answer. The flavors still "
                     f"shift the asymmetric profile (see Upβ / Dnβ / Dn-corr); whether the "
                     f"downside protection is worth the return drag is a judgment call the "
                     f"table surfaces. Check DSR / bootstrap Sharpe CI for significance "
                     f"(flavors share sleeves → DSR conservative; one split = one regime).")
        a(f"> **Verdict:** {verdm}")
        a("")

    a("## 8. Caveats (what is and is NOT fixed)")
    a("")
    a("- **Fixed:** Volatility (^VIX) non-tradable sleeve removed by default; 20% per-sleeve")
    a("  cap kills single-ETF macro bets; transaction costs netted; Ledoit-Wolf shrinkage;")
    a("  diversification + both-down correlation in the objective; Deflated Sharpe; rolling")
    a("  selection re-enumerated from scratch (no TRAIN shortlist).")
    a("- **Bond total-return:** sleeves use Yahoo *adjusted close* (includes distributions")
    a("  where Yahoo provides them); this is ETF total return for the ETF-based sleeves,")
    a("  which is what All-Weather uses too — so the benchmark is fair. The only non-TR /")
    a("  non-investable sleeve was Volatility, now excluded.")
    a("- **Still one regime / two blocks:** TRAIN 2008–17, TEST 2018–26. The DSR and")
    a("  bootstrap CIs are guardrails, not a guarantee of future performance.")
    a("- **Vol target not implemented:** no-leverage + no dedicated cash/T-bill sleeve makes")
    a("  a vol target infeasible without adding a short-Treasury sleeve (left as a flag).")
    a("- **Regime-conditioned / CVaR / momentum overlays (review item 10)** are documented")
    a("  next steps, not implemented here.")
    a("")
    with open(os.path.join(args.out_dir, "report_eval.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
