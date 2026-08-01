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
    # splice_allowed=False: the audit's anchor for this exposure is GDX, which is
    # absent from the dataset, so FSAGX/ASA were never graded. Splicing on an
    # equivalence test that never ran is exactly what the seam check exists to
    # stop -- and this exposure carried 6-19% weight in the published ladder.
    ("PM Equity",         "FSAGX", ["ASA"],   False),
]

SEAM_TOL_PP = 1.00        # max |mean return| gap across a splice seam, pp/yr
SEAM_TE_RATIO = 0.30      # max tracking error as a share of the pair's own vol
SEAM_MIN_OVERLAP = 24     # months of overlap needed to judge a seam at all


def stitch(parts: list[tuple[str, pd.Series]]) -> tuple[pd.Series, list]:
    """Splice a chain of vehicles into one series, NEWEST FIRST.

    `parts` is ordered newest-first: [(etf, series), (proxy, series), ...].
    The newer vehicle wins every month it covers; each older one supplies only
    the earlier span the newer ones do not reach.

    This used to run oldest-first and keep only months the accumulating series
    lacked, which inverted the intent: the OLD PROXY overwrote the ETF on every
    overlapping month. The panel's "US Total Market" matched VFINX at 0.00
    bps/month and VTI at 34.04 for VTI's entire life, and every published number
    downstream was computed on proxies rather than the funds they were named
    after.

    Each join is checked on BOTH mean return and tracking error relative to the
    pair's own volatility -- a mean-only test lets two series with equal averages
    and different risk splice cleanly, which is precisely the substitution the
    seam exists to prevent.
    """
    series, used = None, []
    for tk, s in parts:
        s = s.dropna()
        if series is None:
            series = s.copy()
            used.append((tk, s.index.min(), s.index.max()))
            continue

        ov = series.index.intersection(s.index)
        if len(ov) < SEAM_MIN_OVERLAP:
            raise SystemExit(
                f"splice {tk}: only {len(ov)} overlapping months (need "
                f"{SEAM_MIN_OVERLAP}) -- too little evidence to judge the seam. "
                "Refusing to splice an unvalidated join.")
        x, y = series[ov], s[ov]
        mean_gap = float(abs(x.mean() - y.mean()) * 1200)
        te = float((x - y).std())
        vol = float((x.std() + y.std()) / 2)
        te_ratio = te / vol if vol > 0 else float("inf")
        if mean_gap > SEAM_TOL_PP or te_ratio > SEAM_TE_RATIO:
            raise SystemExit(
                f"splice {tk}: seam differs by {mean_gap:.2f} pp/yr and "
                f"TE/vol {te_ratio:.2f} over {len(ov)} shared months "
                f"(tolerances {SEAM_TOL_PP} pp/yr, {SEAM_TE_RATIO}). "
                "Refusing to splice.")

        older = s[~s.index.isin(series.index)]
        series = pd.concat([series, older]).sort_index()
        used.append((tk, older.index.min() if len(older) else None,
                     older.index.max() if len(older) else None))
    return series, used


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

        # parts is already newest-first (ETF, then progressively older proxies)
        series, used = stitch(parts)
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

    # Two exposures resolving to the same underlying fund would let the search
    # treat one asset as two independent ones and double-count its slot. This
    # happened: US Total Market and US Large Cap were byte-identical over all
    # 498 months because both fell back to VFINX for their whole history.
    cols_l = list(panel.columns)
    dupes = []
    for i, a in enumerate(cols_l):
        for b in cols_l[i + 1:]:
            j = pd.concat([panel[a], panel[b]], axis=1).dropna()
            if len(j) >= 24 and (j.iloc[:, 0] - j.iloc[:, 1]).abs().max() < 1e-12:
                dupes.append((a, b, len(j)))
    if dupes:
        raise SystemExit(
            "DUPLICATE COLUMNS: " + "; ".join(f"{a} == {b} over {n} months"
                                              for a, b, n in dupes)
            + "\nRefusing to write a panel that presents one asset as two.")
    print("  all columns pairwise distinct")

    # Every spliced exposure must follow its ETF wherever the ETF exists.
    w = load_ticker_panel()
    for label, etf, _p, _ok in EXPOSURES:
        if label not in panel.columns or etf not in w.columns:
            continue
        e = w[etf].dropna()
        ov = panel.index.intersection(e.index)
        if len(ov) < 12:
            continue
        d = float((panel.loc[ov, label] - e.loc[ov]).abs().max())
        if d > 1e-12:
            raise SystemExit(
                f"{label} diverges from {etf} by {d:.2e} on months where {etf} "
                "exists -- the proxy is winning the overlap. Refusing to write.")
    print("  every exposure follows its ETF where the ETF exists")

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
