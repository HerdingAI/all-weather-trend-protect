"""
drawdown_ladder.py -- maximum return at each drawdown ceiling.

THE QUESTION
------------
Not "what is the best portfolio" but "what does each step down in pain cost?"
For ceilings 40% -> 20%, find the highest-return long-only allocation that
stays inside it, and report the whole ladder. If the curve is flat between two
rungs, a large reduction in drawdown is nearly free, and that is more useful
than any single recommendation.

WHAT "PAIN" MEANS HERE
----------------------
Maximum drawdown and "worst loss relative to an investor's own cost basis" are
the SAME statistic -- both minimise w[j]/w[i] over i <= j. Verified, not
assumed. So a second depth measure adds nothing.

What actually separates the unlucky entrant is not depth but TIME: how long the
money stays below the price they paid. A 1999 buyer of US equity suffered the
same -45% the index shows, but waited ~13 years to be clearly ahead. So each
rung reports, alongside drawdown:

  underwater  -- longest run of months below a prior peak (= below cost basis
                 for the worst-timed entrant).
  worst 10y   -- lowest annualised return over any 10-year window, which is the
                 sequence risk a fixed horizon actually faces.

SEARCH
------
No structure is assumed. Nothing is seeded with 60/40, risk parity or
All-Weather, and no sleeve is pre-selected on a story about what it is "for".

  pass 1  exhaustive grid over every subset up to MAX_EXHAUSTIVE assets at
          GRID_STEP weights -- this genuinely enumerates the space most real
          portfolios occupy.
  pass 2  large-sample Dirichlet search over the full universe with local
          refinement, reaching allocations the grid cannot.
  pass 3  convergence check on an independent seed; if the frontier moves, the
          search was not converged and the result says so.

Coverage actually achieved is reported numerically. "We searched everything" is
a claim requiring proof.

Run:  .venv/bin/python drawdown_ladder.py [--window 1986-01] [--draws 200000]
"""
from __future__ import annotations

import argparse
import itertools
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "output", "drawdown_ladder")
PANEL_CSV = os.path.join(HERE, "output", "study_panel.csv")

CEILINGS = [0.40, 0.35, 0.30, 0.25, 0.20]
GRID_STEP = 0.05
MAX_EXHAUSTIVE = 4          # subsets up to this size are enumerated exactly
COST_BPS = 10.0             # per side, on rebalancing turnover

BENCHMARKS = {
    "80/20 VTI-GLD": {"US Total Market": 0.80, "Gold": 0.20},
    "60/20/20":      {"US Total Market": 0.60, "Intl Developed": 0.20, "Gold": 0.20},
    "S&P 500":       {"US Large Cap": 1.00},
    "100% US Total": {"US Total Market": 1.00},
}


# --------------------------------------------------------------------------- #
# Core metrics -- vectorised so millions of allocations are feasible
# --------------------------------------------------------------------------- #

def wealth_curve(r: np.ndarray) -> np.ndarray:
    return np.cumprod(1.0 + r, axis=0)


def max_drawdown(w: np.ndarray) -> np.ndarray:
    """Peak-to-trough, per column. Equals the worst entry-relative loss."""
    peak = np.maximum.accumulate(w, axis=0)
    return (w / peak - 1.0).min(axis=0)


def longest_underwater(w: np.ndarray) -> np.ndarray:
    """Longest run of months strictly below a prior peak, per column."""
    peak = np.maximum.accumulate(w, axis=0)
    under = w < peak * (1 - 1e-12)
    out = np.zeros(w.shape[1])
    run = np.zeros(w.shape[1])
    for t in range(w.shape[0]):
        run = np.where(under[t], run + 1, 0)
        out = np.maximum(out, run)
    return out


def worst_rolling(w: np.ndarray, months: int) -> np.ndarray:
    """Lowest annualised return over any `months`-long window, per column."""
    if w.shape[0] <= months:
        return np.full(w.shape[1], np.nan)
    ratio = w[months:] / w[:-months]
    return (ratio ** (12.0 / months) - 1.0).min(axis=0)


def cagr(w: np.ndarray, n_months: int) -> np.ndarray:
    return w[-1] ** (12.0 / n_months) - 1.0


def evaluate(R: np.ndarray, W: np.ndarray) -> dict:
    """R: (T, k) asset returns. W: (k, n) weight columns. Monthly rebalanced.

    GROSS of costs. Rebalancing cost is a per-allocation calculation that needs
    a (T, k, n) intermediate, which is a memory blow-up at search scale and
    would not change the ranking materially: monthly turnover on these books is
    a few percent, so 10 bps/side is single-digit bps/yr. Costs are applied
    exactly, via `net_of_costs`, to the finalists and the benchmarks.
    """
    port = R @ W
    wc = wealth_curve(port)
    return dict(port=port, wealth=wc,
                cagr=cagr(wc, R.shape[0]),
                dd=max_drawdown(wc))


def net_of_costs(R: np.ndarray, w: np.ndarray, cost_bps: float = COST_BPS) -> dict:
    """Exact monthly-rebalanced result for ONE allocation, net of turnover cost.

    Rebalancing back to target after a month costs
        turnover_t = sum_i w_i * |r_i,t - r_p,t| / (1 + r_p,t)
    which is the drift that has to be traded away.
    """
    rp = R @ w
    drift = np.abs(R - rp[:, None]) @ w
    turn = drift / (1.0 + rp)
    net = rp - turn * (cost_bps / 1e4)
    wc = np.cumprod(1.0 + net)[:, None]
    return dict(cagr=float(cagr(wc, len(net))[0]),
                dd=float(max_drawdown(wc)[0]),
                underwater=float(longest_underwater(wc)[0]),
                worst10=float(worst_rolling(wc, 120)[0]),
                turnover_ann=float(turn.mean() * 12))


# --------------------------------------------------------------------------- #
# Weight generation
# --------------------------------------------------------------------------- #

def grid_weights(k: int, step: float) -> np.ndarray:
    """All compositions of 1.0 into k parts on a `step` grid."""
    n = int(round(1.0 / step))
    out = []
    for c in itertools.combinations_with_replacement(range(k), n):
        v = np.zeros(k)
        for i in c:
            v[i] += step
        out.append(v)
    return np.unique(np.array(out), axis=0)


def exhaustive(n_assets: int, max_size: int, step: float):
    """Yield (asset_index_tuple, weight_matrix) for every subset up to max_size."""
    for size in range(1, max_size + 1):
        gw = grid_weights(size, step)
        gw = gw[(gw > 0).all(axis=1)]          # subsets are exact: no zero legs
        if len(gw) == 0:
            continue
        for idx in itertools.combinations(range(n_assets), size):
            yield idx, gw


def dirichlet_draws(k: int, n: int, rng: np.random.Generator,
                    concentration: float = 0.35) -> np.ndarray:
    """Sparse-ish draws: low concentration favours concentrated books, which is
    where the return-maximising corner of the frontier lives."""
    return rng.dirichlet(np.full(k, concentration), size=n).T


def refine(R: np.ndarray, base: np.ndarray, rng: np.random.Generator,
           ceiling: float, rounds: int = 6, per_round: int = 400) -> tuple:
    """Local hill-climb around a starting allocation, keeping the constraint."""
    best_w, best_c = base.copy(), -np.inf
    for rd in range(rounds):
        scale = 0.12 * (0.6 ** rd)
        cand = best_w[:, None] + rng.normal(0, scale, size=(len(base), per_round))
        cand = np.clip(cand, 0, None)
        s = cand.sum(axis=0)
        cand = cand[:, s > 0] / s[s > 0]
        cand = np.hstack([best_w[:, None], cand])
        ev = evaluate(R, cand)
        ok = -ev["dd"] <= ceiling
        if not ok.any():
            continue
        c = np.where(ok, ev["cagr"], -np.inf)
        j = int(np.argmax(c))
        if c[j] > best_c:
            best_c, best_w = c[j], cand[:, j]
    return best_w, best_c


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", default="1986-01",
                    help="First month of the evaluation window (default 1986-01).")
    ap.add_argument("--draws", type=int, default=150_000,
                    help="Dirichlet draws in pass 2 (default 150000).")
    ap.add_argument("--seed", type=int, default=20260801)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    panel = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)
    sub = panel.loc[args.window:].dropna(axis=1, how="any").dropna()
    assets = list(sub.columns)
    R = sub.values
    T, k = R.shape

    print("=" * 80)
    print("DRAWDOWN LADDER")
    print("=" * 80)
    print(f"\nWindow : {str(sub.index.min())[:7]} -> {str(sub.index.max())[:7]}  "
          f"({T} months, {T/12:.1f}y)")
    print(f"Assets ({k}): {', '.join(assets)}")
    print(f"Costs  : {COST_BPS:.0f} bps/side on rebalancing turnover")
    print("\nGate: maximum drawdown (which equals the worst entry-relative loss).")
    print("Time underwater and worst 10y return are reported per rung -- they are")
    print("what actually separates a badly-timed entry from a well-timed one.")

    # ---- benchmarks -------------------------------------------------------
    print("\n" + "-" * 80)
    print("BENCHMARKS on this window")
    print("-" * 80)
    print(f"{'portfolio':18s} {'CAGR':>7s} {'maxDD':>9s} {'underwtr':>8s} {'worst10y':>9s}")
    bench = {}
    for name, wts in BENCHMARKS.items():
        if any(a not in assets for a in wts):
            print(f"{name:18s} (needs an asset outside this window)")
            continue
        v = np.zeros((k, 1))
        for a, x in wts.items():
            v[assets.index(a), 0] = x
        v /= v.sum()
        m = net_of_costs(R, v[:, 0])
        bench[name] = dict(weights=wts, **m)
        print(f"{name:18s} {m['cagr']*100:6.2f}% {m['dd']*100:8.2f}% "
              f"{m['underwater']/12:7.1f}y {m['worst10']*100:8.2f}%")

    # ---- pass 1: exhaustive ----------------------------------------------
    print("\n" + "-" * 80)
    print(f"PASS 1 — exhaustive: every subset up to {MAX_EXHAUSTIVE} assets "
          f"at {GRID_STEP:.0%} steps")
    print("-" * 80)
    rng = np.random.default_rng(args.seed)
    best = {c: dict(cagr=-np.inf, w=None, src=None) for c in CEILINGS}
    n_eval = 0
    for idx, gw in exhaustive(k, MAX_EXHAUSTIVE, GRID_STEP):
        Wsub = np.zeros((k, gw.shape[0]))
        Wsub[list(idx), :] = gw.T
        ev = evaluate(R, Wsub)
        n_eval += Wsub.shape[1]
        worst = -ev["dd"]
        for c in CEILINGS:
            ok = worst <= c
            if not ok.any():
                continue
            cg = np.where(ok, ev["cagr"], -np.inf)
            j = int(np.argmax(cg))
            if cg[j] > best[c]["cagr"]:
                best[c] = dict(cagr=float(cg[j]), w=Wsub[:, j].copy(), src="grid")
    print(f"  evaluated {n_eval:,} allocations")

    # ---- pass 2: dirichlet + refine ---------------------------------------
    print("\n" + "-" * 80)
    print(f"PASS 2 — {args.draws:,} Dirichlet draws over all {k} assets, "
          "then local refinement")
    print("-" * 80)
    CH = 25_000
    done = 0
    while done < args.draws:
        n = min(CH, args.draws - done)
        W = dirichlet_draws(k, n, rng)
        ev = evaluate(R, W)
        worst = -ev["dd"]
        for c in CEILINGS:
            ok = worst <= c
            if not ok.any():
                continue
            cg = np.where(ok, ev["cagr"], -np.inf)
            j = int(np.argmax(cg))
            if cg[j] > best[c]["cagr"]:
                best[c] = dict(cagr=float(cg[j]), w=W[:, j].copy(), src="dirichlet")
        done += n
        n_eval += n
    for c in CEILINGS:
        if best[c]["w"] is None:
            continue
        w2, c2 = refine(R, best[c]["w"], rng, c)
        if c2 > best[c]["cagr"]:
            best[c] = dict(cagr=float(c2), w=w2, src=best[c]["src"] + "+refine")
    print(f"  cumulative allocations evaluated: {n_eval:,}")

    # ---- pass 3: convergence ---------------------------------------------
    print("\n" + "-" * 80)
    print("PASS 3 — convergence check on an independent seed")
    print("-" * 80)
    rng2 = np.random.default_rng(args.seed + 777)
    alt = {c: -np.inf for c in CEILINGS}
    done = 0
    while done < args.draws // 2:
        n = min(CH, args.draws // 2 - done)
        W = dirichlet_draws(k, n, rng2)
        ev = evaluate(R, W)
        worst = -ev["dd"]
        for c in CEILINGS:
            ok = worst <= c
            if ok.any():
                alt[c] = max(alt[c], float(np.where(ok, ev["cagr"], -np.inf).max()))
        done += n
    converged = True
    for c in CEILINGS:
        gap = (best[c]["cagr"] - alt[c]) * 100
        flag = "ok" if abs(gap) < 0.25 else "NOT CONVERGED"
        if abs(gap) >= 0.25:
            converged = False
        print(f"  ceiling {c:.0%}: main {best[c]['cagr']*100:6.2f}%  "
              f"half-budget independent seed {alt[c]*100:6.2f}%  "
              f"gap {gap:+.2f} pp  {flag}")

    # ---- the ladder -------------------------------------------------------
    print("\n" + "=" * 80)
    print("THE LADDER")
    print("=" * 80)
    print(f"{'ceiling':8s} {'CAGR':>7s} {'maxDD':>9s} {'underwtr':>8s} {'worst10y':>9s}  allocation")
    rows = []
    for c in CEILINGS:
        b = best[c]
        if b["w"] is None:
            print(f"{c:.0%}      no allocation satisfies this ceiling")
            continue
        m = net_of_costs(R, b["w"])
        alloc = ", ".join(f"{assets[i]} {b['w'][i]:.0%}"
                          for i in np.argsort(-b["w"]) if b["w"][i] >= 0.005)
        print(f"{c:.0%}     {m['cagr']*100:6.2f}% {m['dd']*100:8.2f}% "
              f"{m['underwater']/12:7.1f}y {m['worst10']*100:8.2f}%  {alloc}")
        rows.append(dict(ceiling=c, cagr=m["cagr"]*100, maxdd=m["dd"]*100,
                         underwater_yrs=m["underwater"]/12, worst10=m["worst10"]*100,
                         turnover_ann=m["turnover_ann"], source=b["src"],
                         allocation=alloc,
                         **{a: b["w"][i] for i, a in enumerate(assets)}))

    if rows:
        print("\nCost of each step down:")
        for a, bnext in zip(rows, rows[1:]):
            print(f"  {a['ceiling']:.0%} -> {bnext['ceiling']:.0%}: "
                  f"{a['cagr']-bnext['cagr']:+.2f} pp of CAGR")

    print(f"\nCoverage: {n_eval:,} allocations evaluated; subsets up to "
          f"{MAX_EXHAUSTIVE} assets enumerated exhaustively at {GRID_STEP:.0%}; "
          f"{'converged' if converged else 'NOT CONVERGED — treat as provisional'}.")

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(args.out_dir, "ladder.csv"), index=False)
    pd.DataFrame(bench).T.to_csv(os.path.join(args.out_dir, "benchmarks.csv"))
    print(f"Wrote {args.out_dir}/ladder.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
