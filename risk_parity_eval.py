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
SCHEME_ORDER = ["EW", "InvVol", "InvVar", "ERC", "MinVar", "LS-TSMOM"]
# Schemes that solve a covariance-based target weight annually (vs LS-TSMOM,
# which is a monthly momentum signal with no covariance target).
COV_SCHEMES = {"EW", "InvVol", "InvVar", "ERC", "MinVar"}


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


def backtest(panel: pd.DataFrame, precomp: Dict[pd.Timestamp, Tuple[np.ndarray, np.ndarray]],
             sleeve_idx: List[int], scheme: str, cap: float, cost_bps: float,
             cadence: str = "A", erc_cap_mode: str = "capped",
             ret_full: Optional[pd.DataFrame] = None,
             tsmom_lookback: int = 12) -> Dict[str, np.ndarray]:
    """Backtest one combo (via its sleeve position indices) under one scheme.
    Returns gross, net, turnover monthly arrays + last weights + last cov-based
    diversification ratio. LS-TSMOM is a monthly momentum signal (no annual
    refit / no covariance target) and dispatches to _backtest_ls_tsmom."""
    if scheme == "LS-TSMOM":
        return _backtest_ls_tsmom(panel, ret_full, sleeve_idx, tsmom_lookback, cost_bps)
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

def resilience_score(df: pd.DataFrame) -> pd.Series:
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
                tsmom_lookback: int = 12) -> pd.DataFrame:
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
                          tsmom_lookback=tsmom_lookback)
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
        df["resilience_score"] = resilience_score(df)
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
                        tsmom_lookback: int = 12) -> Tuple[pd.Series, pd.DataFrame]:
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
                          progress_every=10**9, erc_cap_mode=erc_cap_mode)
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
    ap.add_argument("--no-rolling", action="store_true")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    tr_s, tr_e = pd.Timestamp(args.train_start), pd.Timestamp(args.train_end)
    te_s, te_e = pd.Timestamp(args.test_start), pd.Timestamp(args.test_end)
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip() in SCHEMES]
    roll_schemes = [s.strip() for s in args.rolling_schemes.split(",") if s.strip() in SCHEMES]
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
                            tsmom_lookback=args.tsmom_lookback)
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
            "both_down_annualized": test_eval["test_both_down_annualized"],
            "max_drawdown": test_eval["test_max_drawdown"],
            "div_ratio": test_eval["test_div_ratio"],
            "corr_eq_bothdown": test_eval["test_corr_eq_bothdown"],
        })
        test_eval["test_score"] = resilience_score(sc).values
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

    # Rolling full re-enumerated selection
    oos_port, sel_log = (pd.Series(dtype=float), pd.DataFrame())
    if not args.no_rolling:
        print("\n-- Rolling FULL re-enumerated selection across TEST --")
        oos_port, sel_log = rolling_full_select(
            ret, avail, eq, bd, roll_schemes, args.cap, cost, args.shrink,
            args.trailing, te_s, te_e, max_size, args.min_sleeves,
            erc_cap_mode=args.erc_cap_mode, ref_mode=args.ref_mode,
            tsmom_lookback=args.tsmom_lookback)
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
                 rp_combo, rp_sch, rp_te_m)
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
                 ls_diag=None, rp_combo=None, rp_sch=None, rp_te_m=None):
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
