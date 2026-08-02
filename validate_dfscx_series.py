"""
validate_dfscx_series.py -- gate the user-supplied DFSCX series before use.

DFSCX (DFA US Micro Cap) is a SIZE sleeve, not size+value -- it is not
interchangeable with DFSVX, and the two are compared here rather than merged.
Its backtest starts 1991-01, which extends US small-cap history 26 months
before DFSVX but still does NOT reach the 1980-82 Volcker window that Q3
actually needs.

It is also the fund the Felix comparison names as having underperformed the
S&P 500 since its 1981 inception, so it is a useful check on whether the
small-cap case is a size story or a value story.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import pv_series as PV

DFSCX_CSV = "data/dfscx_monthly_returns.csv"

PV_STATS = dict(mean=1.15, std=5.80, minimum=-23.25, maximum=23.58,
                pct_positive=62.53, skew=-0.328, excess_kurtosis=1.461)
PV_PCTILES = {1: -13.04, 5: -8.08, 25: -2.38, 50: 1.61, 75: 4.56,
              95: 9.75, 99: 13.77}

FIRST_FULL_MONTH = None      # all 427 months reconcile


def cagr(s): return float(((1 + s).prod() ** (12 / len(s)) - 1) * 100)
def mdd(s):
    c = (1 + s).cumprod()
    return float(((c / c.cummax()) - 1).min() * 100)
def cum(s): return float(((1 + s).prod() - 1) * 100)


def main() -> None:
    raw = PV.load_pv_csv(DFSCX_CSV)
    failed = PV.report("DFSCX", raw, FIRST_FULL_MONTH, PV_STATS, PV_PCTILES,
                       anchor="VEXPX", corr_min=0.85, te_ratio_max=0.45)

    print("\n" + ("REJECTED" if failed else "ACCEPTED"))
    if failed:
        sys.exit(1)

    r = raw["monthly_return"] / 100.0
    dfsvx = PV.load_pv_csv("data/dfsvx_monthly_returns.csv")["monthly_return"] / 100.0
    vfinx = PV.load_ticker("VFINX")

    print("\n--- size vs size+value: DFSCX (micro) against DFSVX (small value)")
    j = pd.concat([r.rename("micro"), dfsvx.rename("smallval"),
                   vfinx.rename("sp")], axis=1, sort=True).dropna()
    print(f"  common window {j.index.min():%Y-%m}..{j.index.max():%Y-%m}  n={len(j)}")
    for c in ("micro", "smallval", "sp"):
        print(f"    {c:9s} CAGR {cagr(j[c]):5.2f}%  maxDD {mdd(j[c]):6.1f}%  "
              f"vol {j[c].std() * np.sqrt(12) * 100:4.1f}%")

    print("\n--- the dot-com round trip, the episode the case rests on ---")
    for lab, lo, hi in [("run-up   1995-01..2000-02", "1995-01", "2000-02"),
                        ("unwind   2000-03..2002-09", "2000-03", "2002-09"),
                        ("round trip 1995-01..2002-09", "1995-01", "2002-09")]:
        print(f"  {lab}:  micro {cum(r.loc[lo:hi]):+8.1f}%   "
              f"smallval {cum(dfsvx.loc[lo:hi]):+8.1f}%   "
              f"S&P {cum(vfinx.loc[lo:hi]):+8.1f}%")

    print("\n--- what 1991-01..1993-02 adds, which DFSVX cannot see ---")
    pre = r.loc[:"1993-02"]
    jv = pd.concat([pre.rename("a"), vfinx.rename("b")], axis=1,
                   sort=True).dropna()
    print(f"  n={len(jv)}  micro {cagr(jv.a):.2f}%/yr   S&P {cagr(jv.b):.2f}%/yr"
          f"   gap {cagr(jv.a) - cagr(jv.b):+.2f}pp")

    print("\n--- full DFSCX life 1991-01..2026-07 vs the S&P over the same span")
    jf = pd.concat([r.rename("a"), vfinx.rename("b")], axis=1, sort=True).dropna()
    print(f"  DFSCX  CAGR {cagr(jf.a):.2f}%  maxDD {mdd(jf.a):6.1f}%")
    print(f"  VFINX  CAGR {cagr(jf.b):.2f}%  maxDD {mdd(jf.b):6.1f}%")
    d = jf.a - jf.b
    print(f"  gap {cagr(jf.a) - cagr(jf.b):+.2f}pp/yr   "
          f"t={d.mean() / d.std() * np.sqrt(len(d)):.2f}")


if __name__ == "__main__":
    main()
