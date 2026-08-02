"""
validate_dfsvx_series.py -- gate the user-supplied DFSVX series before use.

DFSVX (DFA US Small Cap Value) matters for open-questions Q1. The panel's US
Small Value sleeve is VISVX, which starts 1998-06 -- AFTER the dot-com bubble
began inflating. DFSVX starts 1993-03 and covers the whole run-up and unwind,
which is the single episode the small-value case rests on.

Four gates, then the two questions that actually decide whether it is usable:
does it agree with VISVX where they overlap (splice viability), and what does
the pre-1998 stretch say that the panel currently cannot see.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import pv_series as PV

DFSVX_CSV = "data/dfsvx_monthly_returns.csv"

PV_STATS = dict(mean=1.08, std=5.80, minimum=-26.60, maximum=19.66,
                pct_positive=61.35, skew=-0.537, excess_kurtosis=2.058)
PV_PCTILES = {1: -14.56, 5: -8.38, 25: -2.09, 50: 1.36, 75: 4.61,
              95: 10.00, 99: 14.87}

# DFSVX's inception month is complete, unlike DFUS -- all 401 months reconcile.
FIRST_FULL_MONTH = None

# The panel's splice bar, from build_study_panel.
SEAM_TOL_PP = 1.50
SEAM_TE_RATIO = 0.35
SEAM_MIN_OVERLAP = 24


def cagr(s: pd.Series) -> float:
    return float(((1 + s).prod() ** (12 / len(s)) - 1) * 100)


def maxdd(s: pd.Series) -> float:
    c = (1 + s).cumprod()
    return float(((c / c.cummax()) - 1).min() * 100)


def main() -> None:
    raw = PV.load_pv_csv(DFSVX_CSV)
    failed = PV.report("DFSVX", raw, FIRST_FULL_MONTH, PV_STATS, PV_PCTILES,
                       anchor="VISVX", corr_min=0.90, te_ratio_max=0.35)

    r = raw["monthly_return"] / 100.0
    visvx = PV.load_ticker("VISVX")

    print("\nTEST 4  splice viability against the panel's own bar")
    j = pd.concat([r.rename("DFSVX"), visvx.rename("VISVX")], axis=1,
                  sort=True).dropna()
    x, y = j["DFSVX"], j["VISVX"]
    mean_gap = float(abs(x.mean() - y.mean()) * 1200)
    te = float((x - y).std())
    vol = float((x.std() + y.std()) / 2)
    te_ratio = te / vol
    print(f"  overlap {j.index.min():%Y-%m}..{j.index.max():%Y-%m}  n={len(j)}"
          f"  (bar: >={SEAM_MIN_OVERLAP})")
    print(f"  mean gap {mean_gap:.2f}pp/yr  (bar: <={SEAM_TOL_PP})")
    print(f"  TE/vol   {te_ratio:.4f}      (bar: <={SEAM_TE_RATIO})")
    ok4 = (len(j) >= SEAM_MIN_OVERLAP and mean_gap <= SEAM_TOL_PP
           and te_ratio <= SEAM_TE_RATIO)
    print("  PASS -- DFSVX may extend the US Small Value sleeve before 1998-06"
          if ok4 else "  FAIL -- not spliceable; usable only as its own series")
    failed |= not ok4

    print("\n" + ("REJECTED" if failed else "ACCEPTED"))
    if failed:
        sys.exit(1)

    # ---- what the pre-1998 stretch adds, which the panel cannot currently see
    print("\n--- the window VISVX misses: 1993-03 .. 1998-05 ---")
    pre = r.loc[:"1998-05"]
    vfinx = PV.load_ticker("VFINX")
    jj = pd.concat([pre.rename("DFSVX"), vfinx.rename("VFINX")], axis=1,
                   sort=True).dropna()
    print(f"  n={len(jj)}  DFSVX {cagr(jj.DFSVX):.2f}%/yr   "
          f"VFINX {cagr(jj.VFINX):.2f}%/yr   "
          f"gap {cagr(jj.DFSVX) - cagr(jj.VFINX):+.2f}pp")

    print("\n--- dot-com, on the FULL series rather than the truncated one ---")
    for lab, lo, hi in [("run-up   1995-01..2000-02", "1995-01", "2000-02"),
                        ("unwind   2000-03..2002-09", "2000-03", "2002-09"),
                        ("round trip 1995-01..2002-09", "1995-01", "2002-09")]:
        d = r.loc[lo:hi]
        v = vfinx.loc[lo:hi]
        print(f"  {lab}:  DFSVX {((1 + d).prod() - 1) * 100:+8.1f}%   "
              f"VFINX {((1 + v).prod() - 1) * 100:+8.1f}%")

    print("\n--- full-series profile 1993-03..2026-07 ---")
    print(f"  DFSVX  CAGR {cagr(r):.2f}%  maxDD {maxdd(r):.1f}%  "
          f"vol {r.std() * np.sqrt(12) * 100:.1f}%")
    jv = pd.concat([r.rename("a"), vfinx.rename("b")], axis=1,
                   sort=True).dropna()
    print(f"  VFINX  CAGR {cagr(jv.b):.2f}%  maxDD {maxdd(jv.b):.1f}%  "
          f"vol {jv.b.std() * np.sqrt(12) * 100:.1f}%")


if __name__ == "__main__":
    main()
