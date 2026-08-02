"""
frontier_sweep.py -- the exhaustive map we never actually drew.

WHY THIS EXISTS
---------------
Everything so far compared a HANDFUL of declared books. That was the right
response to walk-forward (searching for an optimum does not survive not knowing
the future), but it left the original question half-answered: we never
established what is ACHIEVABLE, so we never knew whether the incumbent books
sit near the frontier or far from it.

This enumerates every long-only combination of the panel's exposures at a
stated granularity and maps the achievable region.

WHAT THIS IS AND IS NOT
-----------------------
It is a MAP, not a SELECTOR. Walk-forward already showed what happens when the
best point on an in-sample frontier is chosen as a recommendation: every
drawdown ceiling breached out of sample by 25-45 points. So the frontier is
used to answer "how much room is there above the incumbent" -- and every point
on it is then walk-forward validated before any of it is believed.

GRANULARITY, STATED HONESTLY
----------------------------
"Every possible combination" is infinite for continuous weights. This
enumerates the 5% simplex grid with at most MAX_SLEEVES non-zero sleeves --
2.1M portfolios over 11 exposures. Long-only optima are typically sparse, so
capping the sleeve count costs little, but it IS a cap and it is reported.
"""
from __future__ import annotations

import itertools
import os

import numpy as np
import pandas as pd

import candidates as C

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_CSV = os.path.join(HERE, "output", "study_panel.csv")
OUT_DIR = os.path.join(HERE, "output", "frontier")

GRID = 20                 # 20 units of 5%
MAX_SLEEVES = 5
COST_BPS = 10.0           # per side, on turnover
START = "1998-06"         # widest window with the small-value sleeve present
CEILINGS = [40, 35, 30, 25, 20]
CHUNK = 200_000


def compositions(total: int, parts: int):
    """All positive integer vectors of length `parts` summing to `total`."""
    for cuts in itertools.combinations(range(1, total), parts - 1):
        prev, out = 0, []
        for c in cuts:
            out.append(c - prev)
            prev = c
        out.append(total - prev)
        yield out


def enumerate_weights(n_assets: int) -> tuple[np.ndarray, np.ndarray]:
    """Every grid weight vector with 1..MAX_SLEEVES non-zero sleeves."""
    rows, masks = [], []
    for k in range(1, MAX_SLEEVES + 1):
        combos = list(itertools.combinations(range(n_assets), k))
        comps = np.array(list(compositions(GRID, k)), dtype=np.float32) / GRID
        for idx in combos:
            w = np.zeros((len(comps), n_assets), dtype=np.float32)
            w[:, list(idx)] = comps
            rows.append(w)
            masks.append(np.full(len(comps), k, dtype=np.int8))
    return np.vstack(rows), np.concatenate(masks)


def evaluate(R: np.ndarray, W: np.ndarray, cost_bps: float = COST_BPS) -> dict:
    """Monthly-rebalanced portfolio stats for every weight row, net of costs.

    Rebalancing policy was measured as second-order (<=0.24pp CAGR across all
    policies), so monthly is used here for speed and the survivors are
    re-checked under annual rebalancing in `main`.
    """
    n = R.shape[0]
    rp = R @ W.T                                   # (months, portfolios)
    # Turnover cost: drift of each sleeve away from the portfolio return.
    drift = np.abs(R[:, :, None] - rp[:, None, :])
    turn = np.einsum("map,ap->mp", drift, W.T)
    rp = rp - (turn / (1.0 + rp)) * (cost_bps / 1e4)

    wealth = np.cumprod(1.0 + rp, axis=0)
    peak = np.maximum.accumulate(wealth, axis=0)
    maxdd = (wealth / peak - 1.0).min(axis=0) * 100
    cagr = (wealth[-1] ** (12.0 / n) - 1.0) * 100
    downside = np.sqrt((np.minimum(rp, 0.0) ** 2).mean(axis=0)) * np.sqrt(12)
    # A book with no down months has no downside deviation. Divide only where
    # it is defined rather than dividing everywhere and masking afterwards --
    # np.where evaluates both branches, so the naive form warns on every call.
    sortino = np.full(downside.shape, np.nan, dtype=np.float64)
    ok = downside > 0
    sortino[ok] = rp.mean(axis=0)[ok] * 12 / downside[ok]
    return dict(cagr=cagr, maxdd=maxdd, sortino=sortino)


def sweep(R: np.ndarray, W: np.ndarray) -> pd.DataFrame:
    out = {k: [] for k in ("cagr", "maxdd", "sortino")}
    for i in range(0, len(W), CHUNK):
        r = evaluate(R, W[i:i + CHUNK])
        for k in out:
            out[k].append(r[k])
    return pd.DataFrame({k: np.concatenate(v) for k, v in out.items()})


def book_vector(book: dict, assets: list[str]) -> np.ndarray | None:
    if any(a not in assets for a in book):
        return None
    w = np.zeros(len(assets), dtype=np.float32)
    for a, x in book.items():
        w[assets.index(a)] = x
    return w


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    p = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True).loc[START:]
    assets = [c for c in p.columns if p[c].notna().all()]
    R = p[assets].to_numpy(dtype=np.float32)
    print(f"window {p.index.min():%Y-%m}..{p.index.max():%Y-%m}  "
          f"n={len(p)} months")
    print(f"{len(assets)} exposures: {', '.join(assets)}")

    W, k = enumerate_weights(len(assets))
    print(f"\nenumerating {len(W):,} portfolios "
          f"(5% grid, <= {MAX_SLEEVES} sleeves), net of {COST_BPS:.0f}bps/side")

    res = sweep(R, W)
    res["n_sleeves"] = k
    print(f"evaluated {len(res):,}")

    # ---- where do the declared books sit?
    print("\n" + "=" * 74)
    print("INCUMBENT BOOKS vs THE ACHIEVABLE FRONTIER")
    print("=" * 74)
    rows = []
    for name, book in C.CANDIDATES.items():
        v = book_vector(book, assets)
        if v is None:
            continue
        s = evaluate(R, v[None, :])
        cg, dd, so = s["cagr"][0], s["maxdd"][0], s["sortino"][0]
        # Best achievable Sortino at no worse drawdown than this book.
        elig = res[res.maxdd >= dd]
        best_so = elig.sortino.max()
        best_cg = res[(res.maxdd >= dd)].cagr.max()
        pct = (res.sortino < so).mean() * 100
        rows.append(dict(book=name, cagr=cg, maxdd=dd, sortino=so,
                         best_sortino_at_same_dd=best_so,
                         sortino_gap=best_so - so,
                         best_cagr_at_same_dd=best_cg,
                         cagr_gap=best_cg - cg,
                         percentile=pct))
    t = pd.DataFrame(rows).sort_values("sortino", ascending=False)
    print(t.to_string(index=False, float_format=lambda v: f"{v:7.2f}"))
    t.to_csv(os.path.join(OUT_DIR, "books_vs_frontier.csv"), index=False)

    # ---- the frontier itself
    print("\n" + "=" * 74)
    print("FRONTIER: best achievable at each drawdown ceiling (IN SAMPLE)")
    print("=" * 74)
    frows = []
    for c in CEILINGS:
        elig = res[res.maxdd >= -c]
        if elig.empty:
            print(f"  {c}% ceiling: INFEASIBLE")
            continue
        for obj in ("sortino", "cagr"):
            i = elig[obj].idxmax()
            w = W[i]
            book = {assets[j]: round(float(w[j]), 2)
                    for j in np.nonzero(w)[0]}
            frows.append(dict(ceiling=c, objective=obj,
                              cagr=res.cagr[i], maxdd=res.maxdd[i],
                              sortino=res.sortino[i], weights=book))
            print(f"  {c}% / max {obj:7s}: CAGR {res.cagr[i]:5.2f}%  "
                  f"DD {res.maxdd[i]:6.2f}%  Sortino {res.sortino[i]:4.2f}")
            print(f"      {book}")
    pd.DataFrame(frows).to_csv(os.path.join(OUT_DIR, "frontier.csv"),
                               index=False)

    res.to_parquet(os.path.join(OUT_DIR, "all_portfolios.parquet"))
    print(f"\nwrote {OUT_DIR}/")


if __name__ == "__main__":
    main()
