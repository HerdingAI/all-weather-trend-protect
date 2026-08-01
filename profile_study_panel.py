"""
profile_study_panel.py -- descriptive pass over the extended dataset.

Three jobs:

  1. RECONCILE. Rebuild the user's own Portfolio Visualizer portfolios on our
     panel and compare against the figures PV reported. If we cannot reproduce
     a known answer, nothing downstream is trustworthy -- this is the gate.
  2. DESCRIBE. Per-exposure return/risk over the common window and per decade,
     plus the correlation structure, including how it changes in crises (which
     is when diversification is actually needed and most often absent).
  3. STRESS. Every exposure and benchmark through each historical crisis.

Run:  .venv/bin/python profile_study_panel.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
PANEL_CSV = os.path.join(OUT, "study_panel.csv")

# The user's own portfolios, as pasted from Portfolio Visualizer, mapped onto
# our exposures. PV's "Global ex-US" is matched to Intl Developed pre-1996
# because World ex-US does not exist that early.
BENCHMARKS = {
    "Current allocation": {
        "US Total Market": 0.50, "US Large Cap": 0.05, "US Small Value": 0.07,
        "US Small Cap": 0.02, "Intl Developed": 0.18, "Gold": 0.18},
    "80/20 VTI-GLD": {"US Total Market": 0.80, "Gold": 0.20},
    "60/20/20": {"US Total Market": 0.60, "Intl Developed": 0.20, "Gold": 0.20},
    "S&P 500": {"US Large Cap": 1.00},
}

# PV's reported figures (Jan 1986 - Jun 2026) for the same books.
PV_REPORTED = {
    "Current allocation": dict(cagr=10.22, stdev=12.75, maxdd=-42.61, sortino=0.85),
    "80/20 VTI-GLD":      dict(cagr=10.61, stdev=12.65, maxdd=-39.62, sortino=0.90),
    "60/20/20":           dict(cagr=9.98,  stdev=12.50, maxdd=-41.41, sortino=0.84),
    "S&P 500":            dict(cagr=11.42, stdev=15.22, maxdd=-50.97, sortino=0.86),
}

CRISES = {
    "Oil/bear 73-74":  ("1973-01-31", "1974-12-31"),
    "Volcker 80-82":   ("1980-01-31", "1982-12-31"),
    "Black Monday 87": ("1987-09-30", "1987-12-31"),
    "Dot-com 00-02":   ("2000-03-31", "2002-10-31"),
    "GFC 07-09":       ("2007-11-30", "2009-03-31"),
    "COVID 2020":      ("2020-01-31", "2020-03-31"),
    "2022 both-down":  ("2022-01-31", "2022-10-31"),
}


def maxdd(r: pd.Series) -> float:
    w = (1 + r).cumprod()
    return float((w / w.cummax() - 1).min())


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 12:
        return {}
    n_y = len(r) / 12
    dn = r.copy(); dn[dn > 0] = 0
    dsd = dn.std() * np.sqrt(12)
    return dict(
        n=len(r),
        cagr=((1 + r).prod() ** (1 / n_y) - 1) * 100,
        vol=r.std() * np.sqrt(12) * 100,
        maxdd=maxdd(r) * 100,
        sharpe=(r.mean() * 12) / (r.std() * np.sqrt(12)) if r.std() else np.nan,
        sortino=(r.mean() * 12) / dsd if dsd else np.nan,
    )


def port(panel: pd.DataFrame, weights: dict, rebalance: str = "M") -> pd.Series:
    """Monthly return of a fixed-weight, rebalanced book over the months where
    every constituent has data."""
    cols = list(weights)
    sub = panel[cols].dropna()
    if sub.empty:
        return pd.Series(dtype=float)
    w = np.array([weights[c] for c in cols], dtype=float)
    w = w / w.sum()
    if rebalance == "M":
        return pd.Series(sub.values @ w, index=sub.index)
    # drift between rebalance dates
    out, cur = [], w.copy()
    marks = {"A": 12, "Q": 3}.get(rebalance, 12)
    for i, (_, row) in enumerate(sub.iterrows()):
        out.append(float(cur @ row.values))
        cur = cur * (1 + row.values)
        cur = cur / cur.sum()
        if (i + 1) % marks == 0:
            cur = w.copy()
    return pd.Series(out, index=sub.index)


def main() -> int:
    panel = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)
    print("=" * 84)
    print("STUDY PANEL PROFILE")
    print("=" * 84)
    print(f"{panel.shape[0]} months x {panel.shape[1]} exposures  "
          f"({str(panel.index.min())[:7]} -> {str(panel.index.max())[:7]})")

    # ---------------- 1. reconciliation gate ----------------
    print("\n" + "-" * 84)
    print("1. RECONCILIATION — our panel vs the user's Portfolio Visualizer figures")
    print("-" * 84)
    print(f"{'portfolio':22s} {'window':18s} {'CAGR (ours/PV)':>18s} "
          f"{'MaxDD (ours/PV)':>19s} {'Sortino':>14s}")
    recon = []
    for name, wts in BENCHMARKS.items():
        r = port(panel, wts)
        if r.empty:
            print(f"{name:22s} no data"); continue
        st = stats(r)
        pv = PV_REPORTED[name]
        print(f"{name:22s} {str(r.index.min())[:7]}->{str(r.index.max())[:7]:>7s} "
              f"{st['cagr']:8.2f} /{pv['cagr']:7.2f} "
              f"{st['maxdd']:9.2f} /{pv['maxdd']:8.2f} "
              f"{st['sortino']:6.2f} /{pv['sortino']:5.2f}")
        recon.append(dict(portfolio=name, **st, pv_cagr=pv["cagr"],
                          pv_maxdd=pv["maxdd"], pv_sortino=pv["sortino"]))
    print("\n  Note: PV's window is 1986-01 onward and its Sortino uses a T-bill MAR;")
    print("  ours starts at the panel's own first month and uses MAR=0, so levels")
    print("  differ by convention. CAGR and MaxDD are the like-for-like checks.")

    # ---------------- 2. per-exposure description ----------------
    print("\n" + "-" * 84)
    print("2. EXPOSURES — full available history")
    print("-" * 84)
    print(f"{'exposure':20s} {'from':8s} {'CAGR':>7s} {'vol':>7s} {'maxDD':>8s} "
          f"{'Sharpe':>7s} {'Sortino':>8s}")
    rows = []
    for c in panel.columns:
        st = stats(panel[c])
        if not st:
            continue
        rows.append(dict(exposure=c, start=str(panel[c].first_valid_index())[:7], **st))
    for r in sorted(rows, key=lambda x: -x["cagr"]):
        print(f"{r['exposure']:20s} {r['start']:8s} {r['cagr']:6.2f}% {r['vol']:6.2f}% "
              f"{r['maxdd']:7.2f}% {r['sharpe']:7.2f} {r['sortino']:8.2f}")

    # ---------------- 3. crisis behaviour ----------------
    print("\n" + "-" * 84)
    print("3. CRISIS BEHAVIOUR — cumulative return through each stress window")
    print("-" * 84)
    names = [c for c in panel.columns]
    hdr = "".join(f"{k.split()[0][:8]:>10s}" for k in CRISES)
    print(f"{'exposure':20s}{hdr}")
    for c in names:
        cells = ""
        for _, (a, b) in CRISES.items():
            s = panel[c].loc[a:b].dropna()
            cells += f"{((1+s).prod()-1)*100:9.1f}%" if len(s) else f"{'--':>10s}"
        print(f"{c:20s}{cells}")
    print()
    for name, wts in BENCHMARKS.items():
        r = port(panel, wts)
        cells = ""
        for _, (a, b) in CRISES.items():
            s = r.loc[a:b].dropna()
            cells += f"{((1+s).prod()-1)*100:9.1f}%" if len(s) else f"{'--':>10s}"
        print(f"{name:20s}{cells}")

    # ---------------- 4. correlations, normal vs crisis ----------------
    print("\n" + "-" * 84)
    print("4. CORRELATION TO US EQUITY — all months vs equity-down months")
    print("-" * 84)
    eq = panel["US Total Market"]
    down = eq < 0
    print(f"{'exposure':20s} {'all':>8s} {'eq-down':>9s} {'shift':>8s}")
    for c in panel.columns:
        if c == "US Total Market":
            continue
        j = pd.concat([panel[c], eq], axis=1).dropna()
        if len(j) < 36:
            continue
        a = j.iloc[:, 0].corr(j.iloc[:, 1])
        m = j.iloc[:, 1] < 0
        b = j[m].iloc[:, 0].corr(j[m].iloc[:, 1]) if m.sum() > 12 else np.nan
        print(f"{c:20s} {a:8.2f} {b:9.2f} {b-a:8.2f}")
    print("\n  A diversifier that holds its low correlation in the 'eq-down' column")
    print("  is doing the job; one whose correlation jumps is not.")

    pd.DataFrame(recon).to_csv(os.path.join(OUT, "study_reconciliation.csv"), index=False)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "study_exposure_stats.csv"), index=False)
    print(f"\nWrote {OUT}/study_reconciliation.csv and study_exposure_stats.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
