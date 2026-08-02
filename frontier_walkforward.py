"""
frontier_walkforward.py -- is the gap above the incumbent books REAL?

frontier_sweep.py showed the declared books sit at the 72nd-99th percentile of
2.1M enumerated portfolios, with 0.35 of Sortino and ~1.1pp of CAGR apparently
left on the table at the 50/25/25 risk level.

That gap is measured IN SAMPLE. The whole study already has one hard result
about in-sample gaps: walk-forward destroyed the drawdown ladder, breaching
every ceiling by 25-45 points. So the gap is not believable until the SAME
selection procedure is run without hindsight.

Procedure: expanding window, refit every `HOLD` months, pick the best training
portfolio under the objective, hold it, record what actually happened. Compare
against simply holding a fixed declared book over the identical span.

A coarser 10% grid is used here than in the sweep (92k vs 2.1M portfolios)
because the search is repeated at every refit. Coarsening can only HURT the
searcher, so if the searcher still loses, the conclusion is safe; if it wins,
the finer grid would need re-running before believing it.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import candidates as C
import frontier_sweep as F

HOLD = 12
MIN_TRAIN = 10          # years
OUT_DIR = os.path.join(F.HERE, "output", "frontier")
CEILINGS = [40, 30, 25, 20]


def held_return(test, w):
    """Net-of-cost return path for holding `w` over `test`."""
    rp = test @ w
    drift = np.abs(test - rp[:, None]) @ w
    return rp - (drift / (1.0 + rp)) * (F.COST_BPS / 1e4)


def walk_forward_all(R, dates, W, ceilings, objectives):
    """One pass. The training sweep does not depend on ceiling or objective,
    so it is computed ONCE per refit and read by every (ceiling, objective)
    pair -- 8x less work than sweeping per combination.
    """
    keys = [(c, o) for c in ceilings for o in objectives]
    oos = {k: [] for k in keys}
    folds = {k: [] for k in keys}
    t = MIN_TRAIN * 12
    while t < len(R):
        train, test = R[:t], R[t:t + HOLD]
        if len(test) == 0:
            break
        s = F.sweep(train, W)                      # <- the expensive part, once
        for c, o in keys:
            elig = s[s.maxdd >= -c]
            if elig.empty:
                oos[(c, o)].append(np.zeros(len(test)))
                folds[(c, o)].append(dict(train_end=dates[t], feasible=False))
                continue
            w = W[int(elig[o].idxmax())]
            oos[(c, o)].append(held_return(test, w))
            folds[(c, o)].append(dict(train_end=dates[t], feasible=True,
                                      w=w.copy()))
        print(f"    refit {dates[t]:%Y-%m} done", flush=True)
        t += HOLD
    return ({k: np.concatenate(v) for k, v in oos.items()}, folds)


def summarise(r):
    if len(r) < 12:
        return {}
    w = np.cumprod(1 + r)
    dd = (w / np.maximum.accumulate(w) - 1).min() * 100
    ds = np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(12)
    return dict(cagr=(w[-1] ** (12 / len(r)) - 1) * 100, maxdd=dd,
                sortino=(r.mean() * 12 / ds) if ds > 0 else np.nan)


def main():
    p = pd.read_csv(F.PANEL_CSV, index_col=0, parse_dates=True).loc[F.START:]
    assets = [c for c in p.columns if p[c].notna().all()]
    R = p[assets].to_numpy(dtype=np.float32)
    dates = p.index

    F.GRID = 10                       # coarser grid, see module docstring
    W, _ = F.enumerate_weights(len(assets))
    print(f"window {dates.min():%Y-%m}..{dates.max():%Y-%m}  n={len(R)}")
    print(f"searching {len(W):,} portfolios per refit, "
          f"{HOLD}-month holds after {MIN_TRAIN}y minimum train\n")

    objectives = ("sortino", "cagr")
    oos, folds = walk_forward_all(R, dates, W, CEILINGS, objectives)

    print("\n  --- OUT OF SAMPLE, searched fresh at every refit ---")
    rows = []
    for c in CEILINGS:
        for o in objectives:
            st = summarise(oos[(c, o)])
            n_feas = sum(f["feasible"] for f in folds[(c, o)])
            rows.append(dict(ceiling=c, objective=o,
                             oos_cagr=st.get("cagr"), oos_maxdd=st.get("maxdd"),
                             oos_sortino=st.get("sortino"),
                             folds=len(folds[(c, o)]), feasible=n_feas))
            print(f"  {c}% / max {o:7s}: OOS CAGR "
                  f"{st.get('cagr', float('nan')):5.2f}%  DD "
                  f"{st.get('maxdd', float('nan')):7.2f}%  Sortino "
                  f"{st.get('sortino', float('nan')):4.2f}   "
                  f"({n_feas}/{len(folds[(c, o)])} folds feasible)"
                  + ("  <- BREACHED" if st.get("maxdd", 0) < -c else ""))

    # Same span, but simply holding a declared book.
    first = MIN_TRAIN * 12
    print(f"\n  --- holding a fixed book over the identical OOS span "
          f"({dates[first]:%Y-%m}..{dates[-1]:%Y-%m}) ---")
    hold_rows = []
    for name in ("50/25/25 eq-gold-dur", "60/20/20 eq-gold-dur",
                 "80/20 VTI-GLD", "Current allocation", "100% US Total"):
        v = F.book_vector(C.CANDIDATES[name], assets)
        if v is None:
            continue
        sub = R[first:]
        rp = sub @ v
        drift = np.abs(sub - rp[:, None]) @ v
        rp = rp - (drift / (1.0 + rp)) * (F.COST_BPS / 1e4)
        st = summarise(rp)
        hold_rows.append(dict(book=name, **st))
        print(f"  {name:22s}: CAGR {st['cagr']:5.2f}%  DD {st['maxdd']:7.2f}%"
              f"  Sortino {st['sortino']:4.2f}")

    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "walkforward.csv"),
                              index=False)
    pd.DataFrame(hold_rows).to_csv(os.path.join(OUT_DIR, "walkforward_hold.csv"),
                                   index=False)


if __name__ == "__main__":
    main()
