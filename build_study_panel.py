"""
build_study_panel.py -- assemble the one monthly panel the ladder study runs on.

Each exposure is a SPLICE: the longest validated proxy up to the ETF's
inception, then the ETF itself. Splicing is only allowed where the proxy passed
the equivalence test in audit_study_data.py, graded against the GLD/IAU control
(two vehicles for the same exposure: corr 0.9998, 7 bps/month). Where the proxy
FAILED, the exposure simply starts at ETF inception -- a shorter history is
better than a history of the wrong asset.

Gold comes from data/gold_monthly_returns.csv, validated separately by
validate_gold_series.py: it tracks GLD at 3.7 bps/month (tighter than IAU does)
and independently reproduces 53 of 54 annual returns from a second site.

Every series here is a TOTAL RETURN. Provenance is written alongside the panel
so any number in the study can be traced to the ticker that produced it.

Run:  .venv/bin/python build_study_panel.py
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
TICKER_CSV = os.path.join(OUT, "monthly_returns_by_ticker.csv")
GOLD_CSV = os.path.join(HERE, "data", "gold_monthly_returns.csv")
PANEL_CSV = os.path.join(OUT, "study_panel.csv")
PROV_CSV = os.path.join(OUT, "study_panel_provenance.csv")

# (exposure, ETF, [proxies oldest-last], splice_allowed)
# splice_allowed=False -> the proxy failed equivalence; use the ETF only.
EXPOSURES = [
    ("US Total Market",   "VTI",  ["VFINX"],  True),
    ("US Large Cap",      "SPY",  ["VFINX"],  True),
    ("US Small Cap",      "IWM",  ["NAESX"],  True),
    ("US Small Value",    "VBR",  ["VISVX"],  True),
    ("Intl Developed",    "EFA",  ["VTRIX"],  True),
    ("World ex-US",       "VXUS", ["VGTSX"],  True),
    ("Emerging Markets",  "EEM",  [],         False),
    ("Long Treasuries",   "TLT",  ["VUSTX"],  True),
    ("Interm Treasuries", "IEF",  [],         False),
    ("Short Treasuries",  "SHY",  [],         False),
    ("TIPS",              "TIP",  ["VIPSX"],  True),
    ("US Aggregate Bonds", "BND", ["VBMFX"],  True),
    ("Corporate Bonds",   "LQD",  [],         False),
    ("High Yield",        "HYG",  [],         False),
    ("Municipal Bonds",   "MUB",  [],         False),
    ("Commodities",       "DBC",  [],         False),
    ("US REIT",           "VNQ",  ["VGSIX"],  True),
    ("Silver",            "SLV",  [],         False),
    ("PM Equity",         "FSAGX", ["ASA"],   True),
]

SEAM_TOL_PP = 1.00      # max |mean return| gap across a splice seam, pp/yr


def load_ticker_panel() -> pd.DataFrame:
    d = pd.read_csv(TICKER_CSV, parse_dates=["date"]).dropna(subset=["monthly_return"])
    w = d.pivot_table(index="date", columns="ticker", values="monthly_return")
    w.index = w.index.to_period("M").to_timestamp("M")
    return w.sort_index()


def load_gold() -> pd.Series:
    d = pd.read_csv(GOLD_CSV, comment="#")
    months = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]
    rec = {}
    for _, row in d.iterrows():
        y = int(row["year"])
        for i, m in enumerate(months, start=1):
            if pd.notna(row[m]):
                ts = pd.Timestamp(year=y, month=i, day=1) + pd.offsets.MonthEnd(0)
                rec[ts] = row[m] / 100.0
    s = pd.Series(rec).sort_index()
    # Gold was pegged until Aug 1971; pre-1972 months are an administered price,
    # not a market, so they are excluded rather than silently modelled as returns.
    return s[s.index >= "1972-01-01"].rename("Gold")


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    w = load_ticker_panel()
    cols, prov = {}, []

    for label, etf, proxies, splice_ok in EXPOSURES:
        if etf not in w.columns:
            print(f"  SKIP {label}: {etf} absent")
            continue
        etf_s = w[etf].dropna()
        parts = [(etf, etf_s)]

        if splice_ok:
            for p in proxies:
                if p not in w.columns:
                    continue
                ps = w[p].dropna()
                if ps.index.min() < parts[-1][1].index.min():
                    parts.append((p, ps))

        # Stitch oldest-first: each older series covers only months the newer
        # ones do not, so the ETF always wins where it exists.
        series, used = None, []
        for tk, s in reversed(parts):
            if series is None:
                series = s.copy()
                used.append((tk, s.index.min(), s.index.max()))
            else:
                new = s[~s.index.isin(series.index)]
                seam = None
                ov = series.index.intersection(s.index)
                if len(ov) >= 24:
                    seam = float(abs(series[ov].mean() - s[ov].mean()) * 1200)
                    if seam > SEAM_TOL_PP:
                        raise SystemExit(
                            f"{label}: splice seam {tk} vs existing differs by "
                            f"{seam:.2f} pp/yr over {len(ov)} shared months "
                            f"(tolerance {SEAM_TOL_PP}). Refusing to splice.")
                series = pd.concat([series, new]).sort_index()
                used.append((tk, new.index.min() if len(new) else None,
                             new.index.max() if len(new) else None))
        cols[label] = series
        span = f"{str(series.index.min())[:7]}->{str(series.index.max())[:7]}"
        chain = " then ".join(t for t, _, _ in reversed(used))
        prov.append(dict(exposure=label, span=span, n_months=len(series),
                         chain=chain, spliced=len(used) > 1))

    gold = load_gold()
    cols["Gold"] = gold
    prov.append(dict(exposure="Gold",
                     span=f"{str(gold.index.min())[:7]}->{str(gold.index.max())[:7]}",
                     n_months=len(gold), chain="external series (validated vs GLD)",
                     spliced=False))

    panel = pd.DataFrame(cols).sort_index()
    panel.index.name = "Date"
    return panel, pd.DataFrame(prov)


def main() -> int:
    print("=" * 78)
    print("BUILD STUDY PANEL")
    print("=" * 78)
    panel, prov = build()

    print(f"\nPanel: {panel.shape[0]} months x {panel.shape[1]} exposures "
          f"({str(panel.index.min())[:7]} -> {str(panel.index.max())[:7]})\n")
    print(f"{'exposure':20s} {'span':18s} {'n':>5s}  chain")
    for _, r in prov.sort_values("span").iterrows():
        print(f"{r.exposure:20s} {r.span:18s} {r.n_months:5d}  {r.chain}")

    # integrity: no interior gaps, no absurd values
    print("\nIntegrity:")
    bad = 0
    for c in panel.columns:
        s = panel[c]
        f, l = s.first_valid_index(), s.last_valid_index()
        gaps = int(s.loc[f:l].isna().sum())
        ext = int((s.loc[f:l].dropna().abs() > 0.6).sum())
        if gaps or ext:
            bad += 1
            print(f"  {c}: interior gaps={gaps}, |r|>60% months={ext}")
    if not bad:
        print("  no interior gaps; no |monthly return| > 60%")

    print("\nExposures available from each start:")
    for y in (1972, 1986, 1996, 2000, 2005, 2008):
        s = pd.Timestamp(f"{y}-01-31")
        n = [c for c in panel.columns if panel[c].first_valid_index() is not None
             and panel[c].first_valid_index() <= s]
        print(f"  {y}: {len(n):2d}  {', '.join(sorted(n))}")

    panel.to_csv(PANEL_CSV)
    prov.to_csv(PROV_CSV, index=False)
    print(f"\nWrote {PANEL_CSV}")
    print(f"Wrote {PROV_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
