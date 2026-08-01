"""
audit_study_data.py -- data-readiness audit for the drawdown-ladder study.

WHY THIS EXISTS
---------------
The study kept discovering data defects one at a time, mid-analysis: the
Treasury yield-level contamination, the broken 2026-05 return chain, and then
gold futures failing as a bullion proxy. Each was found only when it happened
to matter. This audit front-loads that discovery: it checks every series the
study could use, against every requirement the study has, and produces one
go/no-go table.

The proxy test uses a CONTROL to set the bar rather than an arbitrary
threshold. GLD and IAU are genuinely the same asset (physical gold trusts), so
their agreement -- corr 0.9998, ~7 bps/month, 0.11 pp/yr -- is what "same
exposure" actually looks like in this data. A proposed proxy is graded against
that standard. GC=F failed it badly (corr 0.909, 96 bps/month, 184 bps/yr of
phantom return from continuous-futures roll artifacts) and is excluded.

Run:  .venv/bin/python audit_study_data.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
TICKER_CSV = os.path.join(OUT, "monthly_returns_by_ticker.csv")
DAILY_PQ = os.path.join(OUT, "daily_returns_by_ticker.parquet")

# The exposures the study needs, each as (label, preferred ETF, proxy chain
# oldest-last). The proxy is only used if it PASSES the control-calibrated test.
EXPOSURES = [
    ("US total market",     "VTI",  ["VFINX", "FFIDX"]),
    ("US large cap",        "SPY",  ["VFINX"]),
    ("US small cap",        "IWM",  ["NAESX"]),
    ("US small value",      "VBR",  ["VISVX"]),
    ("Intl developed",      "EFA",  ["VTRIX"]),
    ("Emerging markets",    "EEM",  []),
    ("World ex-US",         "VXUS", ["VGTSX"]),
    ("Long treasuries",     "TLT",  ["VUSTX"]),
    ("Interm treasuries",   "IEF",  ["VFITX"]),
    ("Short treasuries",    "SHY",  ["VFISX"]),
    ("TIPS",                "TIP",  ["VIPSX"]),
    ("US aggregate bonds",  "BND",  ["VBMFX"]),
    ("Corporate bonds",     "LQD",  ["FBNDX"]),
    ("High yield",          "HYG",  ["VWEHX"]),
    ("Municipal bonds",     "MUB",  ["VWITX"]),
    ("Gold bullion",        "GLD",  ["IAU"]),
    ("Precious-metals eq",  "GDX",  ["FSAGX", "ASA", "INIVX"]),
    ("Silver",              "SLV",  []),
    ("Commodities",         "DBC",  ["PCRIX"]),
    ("US REIT",             "VNQ",  ["VGSIX"]),
]

# Calibrated on the GLD/IAU control: two vehicles for the same exposure.
CONTROL = dict(corr=0.9998, mad_bps=7.2, ret_pp=0.11)

# Grading uses tracking error SCALED BY THE ASSET'S OWN VOLATILITY, not raw
# correlation. Correlation is a poor test for low-volatility series: short
# Treasuries score corr 0.963 against SHY while differing by 11 bps/month and
# 0.18 pp/yr -- economically the same exposure, statistically "different" only
# because there is so little variance to correlate. Scaling by volatility asks
# the question that matters: how large is the disagreement relative to the
# moves the asset actually makes?
PASS = dict(te_ratio=0.30, ret_pp=1.00)

CRISES = {
    "1973-74 bear":  ("1973-01-31", "1974-12-31"),
    "Volcker 80-82": ("1980-01-31", "1982-12-31"),
    "Black Monday":  ("1987-09-30", "1987-12-31"),
    "Dot-com":       ("2000-03-31", "2002-10-31"),
    "GFC":           ("2007-11-30", "2009-03-31"),
    "COVID":         ("2020-01-31", "2020-03-31"),
    "2022 both-down": ("2022-01-31", "2022-10-31"),
}


def load() -> pd.DataFrame:
    d = pd.read_csv(TICKER_CSV, parse_dates=["date"]).dropna(subset=["monthly_return"])
    w = d.pivot_table(index="date", columns="ticker", values="monthly_return")
    w.index = w.index.to_period("M").to_timestamp("M")
    return w.sort_index()


def compare(a: pd.Series, b: pd.Series) -> dict | None:
    """Agreement between two series over their overlap."""
    j = pd.concat([a, b], axis=1).dropna()
    if len(j) < 24:
        return None
    x, y = j.iloc[:, 0], j.iloc[:, 1]
    te = float((x - y).std() * np.sqrt(12) * 100)          # ann. tracking error, %
    vol = float(y.std() * np.sqrt(12) * 100)                # ann. vol of the ETF, %
    return {
        "n": len(j),
        "corr": float(x.corr(y)),
        "mad_bps": float((x - y).abs().mean() * 1e4),
        "ret_pp": float(abs(x.mean() - y.mean()) * 1200),
        "te_pct": te,
        "vol_pct": vol,
        "te_ratio": te / vol if vol > 0 else float("inf"),
        "worst_bps": float((x - y).abs().max() * 1e4),
    }


def grade(c: dict | None) -> str:
    if c is None:
        return "NO-OVERLAP"
    if c["te_ratio"] <= PASS["te_ratio"] and c["ret_pp"] <= PASS["ret_pp"]:
        return "PASS"
    return "FAIL"


def main() -> int:
    w = load()
    print("=" * 78)
    print("DATA-READINESS AUDIT — drawdown-ladder study")
    print("=" * 78)
    print(f"\nPanel: {w.shape[1]} tickers, {str(w.index.min())[:7]} -> {str(w.index.max())[:7]}")
    print(f"\nControl (GLD vs IAU, same exposure): corr {CONTROL['corr']}, "
          f"{CONTROL['mad_bps']} bps/mo, {CONTROL['ret_pp']} pp/yr")
    print(f"Pass bar: tracking error <= {PASS['te_ratio']:.0%} of the asset's own "
          f"volatility, and <= {PASS['ret_pp']:.2f} pp/yr return difference")

    # ---------------- 1. coverage + proxy validity ----------------
    print("\n" + "-" * 78)
    print("1. EXPOSURE COVERAGE AND PROXY VALIDITY")
    print("-" * 78)
    print(f"{'exposure':20s} {'ETF':6s} {'etf from':9s} {'proxy':7s} {'proxy from':10s} "
          f"{'TE/vol':>7s} {'pp/yr':>6s} {'corr':>6s}  verdict")
    rows = []
    for label, etf, chain in EXPOSURES:
        if etf not in w.columns:
            print(f"{label:20s} {etf:6s} MISSING")
            rows.append(dict(exposure=label, etf=etf, usable_from=None, note="ETF absent"))
            continue
        e = w[etf].dropna()
        best, best_c, best_g = None, None, "n/a"
        for p in chain:
            if p not in w.columns:
                continue
            c = compare(w[p], e)
            g = grade(c)
            if g == "PASS" and (best is None or w[p].dropna().index.min() < w[best].dropna().index.min()):
                best, best_c, best_g = p, c, g
            if best is None:
                best, best_c, best_g = p, c, g          # keep for reporting
        if best is None:
            print(f"{label:20s} {etf:6s} {str(e.index.min())[:7]:9s} {'--':7s} "
                  f"{'--':10s} {'':>6s} {'':>7s} {'':>6s}  ETF-ONLY")
            rows.append(dict(exposure=label, etf=etf,
                             usable_from=e.index.min(), proxy=None, verdict="ETF-ONLY"))
            continue
        p = w[best].dropna()
        usable = p.index.min() if best_g == "PASS" else e.index.min()
        cc = best_c or {}
        print(f"{label:20s} {etf:6s} {str(e.index.min())[:7]:9s} {best:7s} "
              f"{str(p.index.min())[:7]:10s} "
              f"{cc.get('te_ratio', float('nan')):7.2f} "
              f"{cc.get('ret_pp', float('nan')):6.2f} {cc.get('corr', float('nan')):6.3f}"
              f"  {best_g}")
        rows.append(dict(exposure=label, etf=etf, proxy=best, verdict=best_g,
                         usable_from=usable, **{k: cc.get(k) for k in
                                                ("corr", "mad_bps", "ret_pp", "te_ratio",
                                                 "te_pct", "vol_pct", "worst_bps")}))

    cov = pd.DataFrame(rows)

    # ---------------- 2. what is investable per window ----------------
    print("\n" + "-" * 78)
    print("2. USABLE EXPOSURES BY ANALYSIS WINDOW")
    print("-" * 78)
    ok = cov[cov["usable_from"].notna()].copy()
    for start in ("1973-01", "1986-01", "1996-01", "2000-01", "2005-01"):
        s = pd.Timestamp(start)
        avail = ok[ok["usable_from"] <= s]
        print(f"\n  from {start}: {len(avail)} exposures")
        print("    " + ", ".join(sorted(avail["exposure"])) if len(avail) else "    (none)")

    # ---------------- 3. crisis coverage ----------------
    print("\n" + "-" * 78)
    print("3. CRISIS COVERAGE (how many exposures have data through each event)")
    print("-" * 78)
    for name, (a, b) in CRISES.items():
        s = pd.Timestamp(a)
        n = int((ok["usable_from"] <= s).sum())
        flag = "" if n >= 6 else "   <-- THIN"
        print(f"  {name:16s} {a[:7]}..{b[:7]}   {n:2d} exposures{flag}")

    # ---------------- 4. series integrity ----------------
    print("\n" + "-" * 78)
    print("4. SERIES INTEGRITY (interior gaps, extreme values)")
    print("-" * 78)
    tick = sorted({e for _, e, _ in EXPOSURES} | {p for _, _, c in EXPOSURES for p in c})
    bad = 0
    for t in tick:
        if t not in w.columns:
            continue
        s = w[t]
        f, l = s.first_valid_index(), s.last_valid_index()
        gaps = int(s.loc[f:l].isna().sum())
        ext = s.loc[f:l].dropna()
        n_ext = int((ext.abs() > 0.5).sum())
        if gaps or n_ext:
            bad += 1
            print(f"  {t:7s} interior gaps={gaps:3d}  months |r|>50%={n_ext}")
    if not bad:
        print("  no interior gaps and no |monthly return| > 50% in any study series")

    cov.to_csv(os.path.join(OUT, "study_data_readiness.csv"), index=False)
    print(f"\nWrote {os.path.join(OUT, 'study_data_readiness.csv')}")
    print("\n=== DONE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
