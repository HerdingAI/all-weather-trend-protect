"""
compare_candidates.py -- how a few fixed allocations behave, under real cashflow.

Walk-forward removed optimisation from the table: searching for the best book
lost ~5pp of return out of sample and breached every drawdown ceiling by 25-45
points. So this compares the fixed set declared in candidates.py, and answers
the two questions that remain live:

  ENTRY TIMING  Does it matter WHEN you start? A full-period CAGR averages the
                lucky and unlucky entrant into one number and hides the case
                that actually hurts -- someone who bought in 1999 and waited
                more than a decade to be clearly ahead.

  CASHFLOW      $250K now plus $5K/month. Contributions exceed the initial stake
                within about four years, which should blunt entry-timing risk.
                That is a claim to MEASURE, not assert.

  REBALANCING   With optimisation gone, the rebalancing policy is one of the few
                levers left, and rebalancing between equity and gold is where
                the diversification is actually harvested.

Run:  .venv/bin/python compare_candidates.py
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from candidates import CANDIDATES, INCUMBENT, CONSIDERING, assets_used

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
PANEL_CSV = os.path.join(OUT, "study_panel.csv")
OUT_DIR = os.path.join(OUT, "candidates")

COST_BPS = 10.0

CRISES = {
    "Dot-com":  ("2000-03-31", "2002-10-31"),
    "GFC":      ("2007-11-30", "2009-03-31"),
    "COVID":    ("2020-01-31", "2020-03-31"),
    "2022":     ("2022-01-31", "2022-10-31"),
}


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #

def simulate(R: pd.DataFrame, weights: dict, policy: str = "M",
             band: float = None, cost_bps: float = COST_BPS) -> pd.Series:
    """Monthly returns of a fixed-weight book under a rebalancing policy.

    policy: "M"/"Q"/"A" calendar, or "band" with `band` as the relative drift
    tolerance (0.10 = rebalance when any weight is 10% away from target,
    relative to the target, not in absolute percentage points).

    Costs are charged on the turnover actually traded, so a policy that
    rebalances rarely genuinely pays less.
    """
    cols = list(weights)
    sub = R[cols].dropna()
    tgt = np.array([weights[c] for c in cols], dtype=float)
    tgt = tgt / tgt.sum()

    out = np.empty(len(sub))
    cur = tgt.copy()
    marks = {"M": 1, "Q": 3, "A": 12}.get(policy)
    for i, row in enumerate(sub.values):
        out[i] = float(cur @ row)
        grown = cur * (1.0 + row)
        grown = grown / grown.sum()
        rebal = False
        if marks is not None:
            rebal = ((i + 1) % marks == 0)
        else:                                   # threshold band
            rebal = bool(np.any(np.abs(grown - tgt) > band * tgt))
        if rebal:
            turn = float(np.abs(grown - tgt).sum()) / 2.0
            out[i] -= turn * (cost_bps / 1e4)
            cur = tgt.copy()
        else:
            cur = grown
    return pd.Series(out, index=sub.index)


def wealth(r: pd.Series) -> pd.Series:
    return (1.0 + r).cumprod()


def maxdd(r: pd.Series) -> float:
    w = wealth(r)
    return float((w / w.cummax() - 1.0).min())


def stats(r: pd.Series) -> dict:
    n_y = len(r) / 12
    dsd = float(np.sqrt((np.minimum(r, 0.0) ** 2).mean()) * np.sqrt(12))
    w = wealth(r)
    under = w < w.cummax() * (1 - 1e-12)
    run = best = 0
    for u in under:
        run = run + 1 if u else 0
        best = max(best, run)
    return dict(
        cagr=((1 + r).prod() ** (1 / n_y) - 1) * 100,
        vol=r.std() * np.sqrt(12) * 100,
        maxdd=maxdd(r) * 100,
        sortino=(r.mean() * 12) / dsd if dsd else np.nan,
        underwater_yrs=best / 12,
    )


def rolling_cagr(r: pd.Series, months: int) -> np.ndarray:
    """Annualised return of every window of `months`, INCLUDING the one that
    starts at the first month -- the unlucky entrant's own window."""
    w = np.concatenate([[1.0], wealth(r).values])
    if len(w) <= months:
        return np.array([])
    return (w[months:] / w[:-months]) ** (12.0 / months) - 1.0


def months_to_recover(r: pd.Series, start: int) -> float:
    """Months for an investor entering at `start` to regain their cost basis.
    np.inf if they never do within the sample."""
    w = wealth(r.iloc[start:]) / 1.0
    below = w < 1.0
    if not below.any():
        return 0.0
    last = np.where(~below.values)[0]
    first_bad = int(np.argmax(below.values))
    after = last[last > first_bad]
    return float(after[0] - first_bad) if len(after) else float("inf")


def cashflow_path(r: pd.Series, initial: float, monthly: float) -> dict:
    """Deploy `initial` at month 0 and add `monthly` every month thereafter.

    Reports the worst shortfall against MONEY PUT IN, which is the number a
    contributor actually feels -- not the strategy's peak-to-trough, which is
    measured from a peak they may never have owned.
    """
    bal, contributed = 0.0, 0.0
    worst_gap, bal_path = 0.0, []
    for i, x in enumerate(r.values):
        add = initial if i == 0 else monthly
        bal = (bal + add) * (1.0 + x)
        contributed += add
        bal_path.append(bal)
        worst_gap = min(worst_gap, bal / contributed - 1.0)
    return dict(final=bal, contributed=contributed,
                multiple=bal / contributed,
                worst_vs_contributed=worst_gap * 100,
                path=pd.Series(bal_path, index=r.index))


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args(argv)
    os.makedirs(args.out_dir, exist_ok=True)

    panel = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)
    common = panel[sorted(assets_used())].dropna()
    start_all = common.index.min()

    print("=" * 92)
    print("CANDIDATE COMPARISON — fixed allocations, declared before running")
    print("=" * 92)
    print(f"\nCommon window: {str(start_all)[:7]} -> {str(common.index.max())[:7]} "
          f"({len(common)} months, {len(common)/12:.1f}y) — covers dot-com, GFC, "
          "COVID and 2022.")

    # ---- 1. headline comparison ------------------------------------------
    print("\n" + "-" * 92)
    print("1. THE BOOKS, annually rebalanced, net of costs")
    print("-" * 92)
    print(f"{'candidate':24s} {'CAGR':>7s} {'vol':>6s} {'maxDD':>8s} {'Sortino':>8s} "
          f"{'underwtr':>9s}  {'worst 10y':>10s}")
    rows = []
    for name, w in CANDIDATES.items():
        r = simulate(common, w, "A")
        st = stats(r)
        roll = rolling_cagr(r, 120)
        st["worst10"] = roll.min() * 100 if len(roll) else np.nan
        rows.append(dict(candidate=name, **st))
        print(f"{name:24s} {st['cagr']:6.2f}% {st['vol']:5.2f}% {st['maxdd']:7.2f}% "
              f"{st['sortino']:8.2f} {st['underwater_yrs']:8.1f}y  {st['worst10']:9.2f}%")
    df = pd.DataFrame(rows)

    # ---- 2. crises --------------------------------------------------------
    print("\n" + "-" * 92)
    print("2. CRISES — cumulative return through each window")
    print("-" * 92)
    hdr = "".join(f"{k:>12s}" for k in CRISES)
    print(f"{'candidate':24s}{hdr}")
    crisis_rows = []
    for name, w in CANDIDATES.items():
        r = simulate(common, w, "A")
        cells, rec = "", dict(candidate=name)
        for cname, (a, b) in CRISES.items():
            seg = r.loc[a:b]
            v = ((1 + seg).prod() - 1) * 100 if len(seg) else np.nan
            rec[cname] = v
            cells += f"{v:11.1f}%"
        crisis_rows.append(rec)
        print(f"{name:24s}{cells}")

    # ---- 3. entry timing --------------------------------------------------
    print("\n" + "-" * 92)
    print("3. ENTRY TIMING — every possible start month")
    print("-" * 92)
    print(f"{'candidate':24s} {'10y worst':>10s} {'10y p5':>8s} {'10y med':>8s} "
          f"{'5y worst':>9s} {'spread':>7s} {'worst recovery':>15s}")
    timing = []
    for name, w in CANDIDATES.items():
        r = simulate(common, w, "A")
        r10, r5 = rolling_cagr(r, 120), rolling_cagr(r, 60)
        rec = max(months_to_recover(r, i) for i in range(0, len(r) - 12))
        t = dict(candidate=name,
                 w10=r10.min() * 100, p5_10=np.percentile(r10, 5) * 100,
                 med10=np.median(r10) * 100, w5=r5.min() * 100,
                 spread10=(r10.max() - r10.min()) * 100,
                 worst_recovery_yrs=rec / 12 if np.isfinite(rec) else np.inf)
        timing.append(t)
        rr = "never" if not np.isfinite(rec) else f"{rec/12:.1f}y"
        print(f"{name:24s} {t['w10']:9.2f}% {t['p5_10']:7.2f}% {t['med10']:7.2f}% "
              f"{t['w5']:8.2f}% {t['spread10']:6.1f}pp {rr:>15s}")

    # ---- 4. cashflow ------------------------------------------------------
    print("\n" + "-" * 92)
    print("4. CASHFLOW — $250K deployed at the worst possible month, then $5K/month")
    print("-" * 92)
    print("   Lump-only vs lump+contributions, both entered at each candidate's")
    print("   WORST start month, so this is the unlucky entrant in both cases.")
    print(f"\n{'candidate':24s} {'lump only':>12s} {'with $5K/mo':>13s} "
          f"{'worst vs paid-in':>17s}")
    cash = []
    for name, w in CANDIDATES.items():
        r = simulate(common, w, "A")
        r10 = rolling_cagr(r, 120)
        worst_start = int(np.argmin(r10)) if len(r10) else 0
        seg = r.iloc[worst_start:]
        lump = cashflow_path(seg, 250_000, 0.0)
        both = cashflow_path(seg, 250_000, 5_000)
        cash.append(dict(candidate=name, worst_start=str(seg.index[0])[:7],
                         lump_multiple=lump["multiple"],
                         both_multiple=both["multiple"],
                         lump_worst=lump["worst_vs_contributed"],
                         both_worst=both["worst_vs_contributed"]))
        print(f"{name:24s} {lump['multiple']:11.2f}x {both['multiple']:12.2f}x "
              f"{lump['worst_vs_contributed']:8.1f}% -> {both['worst_vs_contributed']:5.1f}%")
    print("\n   'worst vs paid-in' is how far below the money actually contributed")
    print("   the balance ever fell -- the loss a contributor feels, which the")
    print("   strategy's peak-to-trough does not measure.")

    # ---- 5. rebalancing ---------------------------------------------------
    print("\n" + "-" * 92)
    print("5. REBALANCING POLICY")
    print("-" * 92)
    policies = [("monthly", "M", None), ("quarterly", "Q", None),
                ("annual", "A", None), ("band 10%", "band", 0.10),
                ("band 20%", "band", 0.20)]
    print(f"{'candidate':24s}" + "".join(f"{p[0]:>12s}" for p in policies))
    reb = []
    for name, w in CANDIDATES.items():
        cells, rec = "", dict(candidate=name)
        for label, pol, band in policies:
            r = simulate(common, w, pol, band)
            c = stats(r)["cagr"]
            rec[label] = c
            cells += f"{c:11.2f}%"
        reb.append(rec)
        print(f"{name:24s}{cells}")
    print("\n   CAGR net of 10 bps/side on traded turnover.")

    for obj, fn in ((df, "candidates.csv"), (pd.DataFrame(crisis_rows), "crises.csv"),
                    (pd.DataFrame(timing), "entry_timing.csv"),
                    (pd.DataFrame(cash), "cashflow.csv"),
                    (pd.DataFrame(reb), "rebalancing.csv")):
        obj.to_csv(os.path.join(args.out_dir, fn), index=False)
    print(f"\nWrote {args.out_dir}/*.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
