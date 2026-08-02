"""
walkforward_ladder.py -- does the ladder survive not knowing the future?

THE POINT
---------
drawdown_ladder.py maximises return on the same history it reports. That is a
description of the past, not a recommendation: the ceiling is fitted to the very
drawdown it is measured against, so of course the book honours it.

Here the allocation is chosen using ONLY data strictly before each test period,
then held and measured on months it has never seen. The out-of-sample series is
the concatenation of those held-out periods.

The question that matters is not "what CAGR did it earn" but:

    a book selected to respect a 25% ceiling IN SAMPLE --
    does it respect 25% OUT of sample?

If the out-of-sample drawdown blows through the ceiling, the ladder is a
description of one path, and the ceiling is not a control the investor actually
has. That is the finding either way, and it is why this runs before any
recommendation is made.

Run:  .venv/bin/python walkforward_ladder.py [--window 1996-07] [--min-train 10]
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from drawdown_ladder import (
    CEILINGS, COST_BPS, BENCHMARKS, PANEL_CSV,
    cagr, max_drawdown, longest_underwater, worst_rolling,
    net_of_costs, solve_ceiling, window_slice,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "output", "drawdown_ladder")


def walk_forward(R: np.ndarray, dates: pd.DatetimeIndex, ceiling: float,
                 min_train: int, hold: int, rng: np.random.Generator,
                 draws: int) -> tuple[np.ndarray, list[dict]]:
    """Expanding-window selection, held for `hold` months at a time.

    Returns the concatenated out-of-sample monthly return series and one record
    per refit. `train_end` is EXCLUSIVE: the selection at each step sees rows
    [0, t) and is measured on [t, t+hold). Nothing at or after t can influence
    the weights, which is the only property that makes the result honest.
    """
    oos, folds = [], []
    t = min_train * 12
    while t < len(R):
        train = R[:t]                              # strictly prior
        test = R[t:t + hold]
        if len(test) == 0:
            break
        w = solve_ceiling(train, ceiling, rng, draws=draws)
        if w is None:
            # No book satisfies the ceiling on what we knew then. Holding cash
            # is the honest action; pretending otherwise would leak hindsight.
            oos.append(np.zeros(len(test)))
            folds.append(dict(train_end=dates[t], n_test=len(test),
                              feasible=False, weights=None))
        else:
            rp = test @ w
            drift = np.abs(test - rp[:, None]) @ w
            rp = rp - (drift / (1.0 + rp)) * (COST_BPS / 1e4)
            oos.append(rp)
            folds.append(dict(train_end=dates[t], n_test=len(test),
                              feasible=True, weights=w.copy()))
        t += hold
    return (np.concatenate(oos) if oos else np.array([])), folds


def summarise(r: np.ndarray) -> dict:
    if len(r) < 12:
        return {}
    w = np.cumprod(1.0 + r)[:, None]
    return dict(
        n=len(r),
        cagr=float(cagr(w, len(r))[0]) * 100,
        maxdd=float(max_drawdown(w)[0]) * 100,
        underwater_yrs=float(longest_underwater(w)[0]) / 12,
        worst10=float(worst_rolling(w, 120)[0]) * 100,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", default="1996-07")
    ap.add_argument("--min-train", type=int, default=10,
                    help="Years of history before the first selection.")
    ap.add_argument("--hold", type=int, default=12,
                    help="Months a selected book is held before refitting.")
    ap.add_argument("--draws", type=int, default=25_000)
    ap.add_argument("--seed", type=int, default=20260801)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    panel = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)
    sub, dropped = window_slice(panel, args.window)
    assets, R, dates = list(sub.columns), sub.values, sub.index

    print("=" * 80)
    print("WALK-FORWARD LADDER — selection never sees the months it is scored on")
    print("=" * 80)
    print(f"\nWindow    : {str(dates.min())[:7]} -> {str(dates.max())[:7]} "
          f"({len(R)} months)")
    print(f"Assets    : {len(assets)}")
    print(f"Protocol  : expanding window, first selection after {args.min_train}y, "
          f"refit every {args.hold} months, {COST_BPS:.0f} bps/side")
    if dropped:
        print("Excluded  : " + "; ".join(dropped))
    first_oos = dates[args.min_train * 12] if args.min_train * 12 < len(dates) else None
    print(f"OOS starts: {str(first_oos)[:7]}")

    rng = np.random.default_rng(args.seed)
    rows = []
    for c in CEILINGS:
        oos, folds = walk_forward(R, dates, c, args.min_train, args.hold,
                                  rng, args.draws)
        st = summarise(oos)
        if not st:
            continue
        infeasible = sum(1 for f in folds if not f["feasible"])
        breach = abs(st["maxdd"]) / 100 > c + 1e-9
        rows.append(dict(ceiling=c, **st, refits=len(folds),
                         infeasible_refits=infeasible,
                         honoured=not breach))
        print(f"\n  ceiling {c:.0%}: OOS CAGR {st['cagr']:6.2f}%   "
              f"OOS maxDD {st['maxdd']:7.2f}%   "
              f"{'HONOURED' if not breach else 'BREACHED out of sample'}")
        print(f"     {len(folds)} refits ({infeasible} with no feasible book), "
              f"underwater {st['underwater_yrs']:.1f}y, worst 10y {st['worst10']:.2f}%")

    # Benchmarks need no selection, so their OOS is simply the same span.
    print("\n" + "-" * 80)
    print("BENCHMARKS over the identical out-of-sample span")
    print("-" * 80)
    bench = []
    start = args.min_train * 12
    for name, wts in BENCHMARKS.items():
        if any(a not in assets for a in wts):
            continue
        v = np.zeros(len(assets))
        for a, x in wts.items():
            v[assets.index(a)] = x
        v /= v.sum()
        m = net_of_costs(R[start:], v)
        bench.append(dict(portfolio=name, cagr=m["cagr"] * 100, maxdd=m["dd"] * 100,
                          underwater_yrs=m["underwater"] / 12,
                          worst10=m["worst10"] * 100))
        print(f"  {name:16s} CAGR {m['cagr']*100:6.2f}%   maxDD {m['dd']*100:7.2f}%   "
              f"worst10y {m['worst10']*100:6.2f}%")

    print("\n" + "=" * 80)
    print("IN-SAMPLE vs OUT-OF-SAMPLE")
    print("=" * 80)
    try:
        ins = pd.read_csv(os.path.join(args.out_dir, "w1996", "ladder.csv"))
        print(f"{'ceiling':8s} {'IS CAGR':>9s} {'OOS CAGR':>9s} {'shrink':>8s} "
              f"{'IS maxDD':>9s} {'OOS maxDD':>10s}  ceiling held OOS?")
        for r in rows:
            m = ins[np.isclose(ins["ceiling"], r["ceiling"])]
            if m.empty:
                continue
            i = m.iloc[0]
            print(f"{r['ceiling']:.0%}     {i['cagr']:8.2f}% {r['cagr']:8.2f}% "
                  f"{r['cagr']-i['cagr']:+7.2f}pp {i['maxdd']:8.2f}% "
                  f"{r['maxdd']:9.2f}%  {'yes' if r['honoured'] else 'NO'}")
        print("\nShrinkage is the price of not knowing the future. A ceiling that")
        print("holds in sample but not out of sample was never a control the")
        print("investor had -- it was a property of one path.")
    except FileNotFoundError:
        print("  (in-sample ladder not found; run drawdown_ladder.py first)")

    pd.DataFrame(rows).to_csv(os.path.join(args.out_dir, "walkforward.csv"), index=False)
    pd.DataFrame(bench).to_csv(os.path.join(args.out_dir, "walkforward_benchmarks.csv"),
                               index=False)
    print(f"\nWrote {args.out_dir}/walkforward.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
