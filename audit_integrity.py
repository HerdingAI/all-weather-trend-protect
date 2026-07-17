"""
Data integrity audit for the Stock_Price dataset.

Verifies completeness, structural soundness, value sanity, and correctness
(cross-validation) of the daily + monthly outputs produced by pull_returns.py
and pull_daily.py.  Emits a PASS/WARN/FAIL report and a machine-readable
issues table at output/integrity_report.csv.

Run:  .venv/bin/python audit_integrity.py
"""
from __future__ import annotations
import os, sys, time
from datetime import datetime
import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_returns import ALL_TICKERS

# Known ground-truth sets discovered during the pull:
NOT_ON_YAHOO = {
    "CMR","FPIDX","KBONX","PGBDX","PGLIX","PINVX","VAB","VCE","VCN","VDAIX",
    "VDMIX","VEE","VFSVX","VFTSX","VFV","VFWIX","VGV","VHDYX","VIU","VMMXX",
    "VSP","VTGMX","VTWSX","VXC",
}
MONTHLY_EMPTY = {"PADMX","PAGPX","PIGLX","AUBAX","LOMMX","SPAXX"}  # fail period=max monthly

# Share-class / strategy twins expected to track near-identically.
# (ticker_a, ticker_b, expected_corr_min, max_abs_daily_return_diff_pct)
TWINS = [
    ("VFINX","VFIAX",0.999,0.50),   # Vanguard 500 Investor vs Admiral
    ("VTSMX","VTSAX",0.999,0.50),   # Total Stock Market Inv vs Adm
    ("VBMFX","VBTLX",0.999,0.30),   # Total Bond Market Inv vs Adm
    ("VGHCX","VGHAX",0.999,0.50),   # Health Care Inv vs Adm
    ("VWEHX","VWEAX",0.999,0.50),   # High Yield Corp Inv vs Adm
    ("VIVAX","VVIAX",0.999,0.50),   # Value Index Inv vs Adm
    ("NAESX","VSMAX",0.999,0.50),   # Small Cap Inv vs Adm
    # ETF vs mutual-fund same strategy
    ("VIG","VDADX",0.995,1.00),     # Dividend Appreciation ETF vs MF
    ("VYM","VHYAX",0.995,1.00),     # High Dividend Yield ETF vs MF
    ("VT","VTWAX",0.995,1.00),      # Total World ETF vs MF
]

findings = []  # (severity, check, detail)
def add(sev, check, detail):
    findings.append((sev, check, detail))
    tag = {"PASS":"✅","WARN":"⚠️ ","FAIL":"❌"}[sev]
    print(f"{tag} [{sev:4s}] {check}: {detail}")

def fmt(d): return d.strftime("%Y-%m-%d") if isinstance(d, pd.Timestamp) else str(d)

print("="*78)
print("DATA INTEGRITY AUDIT — Stock_Price")
print("="*78)

# ===========================================================================
# Load data
# ===========================================================================
print("\nLoading outputs ...")
dp = pd.read_parquet(os.path.join(OUT, "daily_prices.parquet"))
dp.index = pd.to_datetime(dp.index)
mp = pd.read_csv(os.path.join(OUT, "monthly_prices.csv"), index_col=0, parse_dates=True)
dr = pd.read_parquet(os.path.join(OUT, "daily_returns_by_ticker.parquet"))
dc = pd.read_csv(os.path.join(OUT, "daily_coverage_summary.csv"), parse_dates=["first_date","last_date"])
uni = pd.read_csv(os.path.join(OUT, "universe.csv"), parse_dates=["first_month","last_month"])
print(f"  daily_prices: {dp.shape}  | monthly_prices: {mp.shape}  | returns panel: {len(dr):,} rows")

# ===========================================================================
# A. STRUCTURAL
# ===========================================================================
print("\n--- A. STRUCTURAL ---")
# A1 index monotonic unique (daily)
if dp.index.is_monotonic_increasing:
    add("PASS","A1 daily index monotonic","yes")
else:
    add("FAIL","A1 daily index monotonic","NO — index not sorted")
if dp.index.duplicated().sum()==0:
    add("PASS","A2 daily index unique","no duplicate dates")
else:
    add("FAIL","A2 daily index unique",f"{dp.index.duplicated().sum()} duplicates")
# A2 monthly
if mp.index.is_monotonic_increasing and mp.index.duplicated().sum()==0:
    add("PASS","A3 monthly index monotonic+unique","yes")
else:
    add("FAIL","A3 monthly index","not monotonic/unique")

# A3 columns vs universe
uni_tickers = set(uni["ticker"])
dp_tickers = set(dp.columns)
missing_in_dp = uni_tickers - dp_tickers
extra_in_dp = dp_tickers - uni_tickers
if not missing_in_dp and not extra_in_dp:
    add("PASS","A4 daily cols == universe",f"{len(dp_tickers)} match {len(uni_tickers)}")
else:
    if missing_in_dp: add("FAIL","A4 daily cols < universe",f"missing {sorted(missing_in_dp)}")
    if extra_in_dp:   add("WARN","A4 daily cols > universe",f"extra {sorted(extra_in_dp)}")

# A4 returns panel schema
need_cols = {"date","ticker","name","asset_class","sector","daily_return"}
if need_cols.issubset(dr.columns):
    add("PASS","A5 returns panel schema","all required columns present")
else:
    add("FAIL","A5 returns panel schema",f"missing {need_cols - set(dr.columns)}")

# ===========================================================================
# B. COMPLETENESS
# ===========================================================================
print("\n--- B. COMPLETENESS ---")
# B1 ticker count
n_with_data = dp.notna().any().sum()
n_empty = (dp.notna().sum()==0).sum()
add("PASS" if n_with_data>=335 else "WARN","B1 daily tickers with data",
    f"{n_with_data}/{len(dp.columns)} ({n_empty} empty)")
# account for SPAXX
if n_empty==1 and set(dp.columns[dp.notna().sum()==0])=={"SPAXX"}:
    add("PASS","B2 only-expected empty ticker","SPAXX (money market, 1d/5d only)")

# B2 gap detection: day-to-day diffs within each series' active span
print("  scanning internal gaps ...")
gap_issues = []
for tk in dp.columns:
    s = dp[tk].dropna()
    if len(s) < 50: continue
    idx = s.index
    diffs = np.diff(idx.values).astype("timedelta64[D]").astype(int)
    # within active span, weekdays should be 1 or 3 (weekend); flag >7 day gaps
    big_gaps = (diffs > 7).sum()
    if big_gaps > 5:
        gap_issues.append((tk, big_gaps, diffs.max()))
if not gap_issues:
    add("PASS","B3 internal gap check","no series with >5 gaps >7 days")
else:
    worst = max(gap_issues, key=lambda x:x[1])
    add("WARN","B3 internal gaps",f"{len(gap_issues)} series with gaps; worst {worst[0]} ({worst[1]} gaps, max {worst[2]}d)")

# B3 TRUNCATION ARTIFACT: clusters of identical first_date (rate-limit/period truncation signature)
print("  scanning for truncation clusters ...")
first_dates = {}
for tk in dp.columns:
    s = dp[tk].dropna()
    if len(s): first_dates[tk] = s.index.min()
fdf = pd.Series(first_dates)
# group by exact date; flag any date with >=8 tickers starting on it (and it's recent)
clusters = fdf.groupby(fdf).agg(list).apply(lambda x: len(x))
suspicious = clusters[(clusters>=8) & (clusters.index > pd.Timestamp("2020-01-01"))]
if suspicious.empty:
    add("PASS","B4 truncation-cluster check","no suspicious shared-start clusters")
else:
    for dt, n in suspicious.items():
        tks = list(fdf[fdf==dt].index[:10])
        add("WARN","B4 truncation-cluster",f"{n} tickers start {fmt(dt)}: {tks}...")

# B5 cross-check daily vs monthly: monthly last-close == last daily close of month
print("  cross-checking daily->monthly close ...")
# build monthly close from daily (last available trading day per month)
dp_monthly = dp.resample("ME").last()  # last non-NaN per month (NaN if no data that month)
mismatches = 0
checked = 0
for tk in mp.columns:
    if tk not in dp_monthly.columns: continue
    a = mp[tk].dropna()
    b = dp_monthly[tk].dropna()
    common = a.index.intersection(b.index)
    if len(common) < 10: continue
    diff = (a.loc[common] - b.loc[common]).abs()
    rel = diff / a.loc[common].abs()
    bad = (rel > 0.02).sum()  # >2% relative diff
    checked += 1
    if bad > len(common)*0.05:
        mismatches += 1
add("PASS" if mismatches==0 else "WARN","B5 monthly==daily-resampled",
    f"{mismatches}/{checked} tickers diverge >2% on >5% of months")

# ===========================================================================
# C. VALUE SANITY
# ===========================================================================
print("\n--- C. VALUE SANITY ---")
# C1 negative / zero / extreme prices
neg = (dp < 0).sum().sum()
zero = (dp == 0).sum().sum()
huge = (dp > 1e8).sum().sum()
tiny = ((dp > 0) & (dp < 1e-4)).sum().sum()
add("PASS" if neg==0 else "FAIL","C1 negative prices",f"{neg} cells")
add("PASS" if zero==0 else "WARN","C1b zero prices",f"{zero} cells")
add("PASS" if huge==0 else "WARN","C1c extreme high prices",f"{huge} cells >1e8")
add("PASS" if tiny==0 else "WARN","C1d tiny prices",f"{tiny} cells <1e-4")

# C2 extreme daily returns (split-adjust failure signature)
rets = dp.pct_change()
# ignore the first row NaN; look at returns beyond +-50%
extreme = ((rets.abs() > 0.50) & rets.notna()).sum().sum()
if extreme == 0:
    add("PASS","C2 extreme returns","none >|50%|")
else:
    # which tickers
    per_tk = (rets.abs() > 0.50).sum()
    bad_tk = per_tk[per_tk>0].sort_values(ascending=False)
    add("WARN","C2 extreme returns",f"{extreme} cells >|50%|; top: {dict(bad_tk.head(5))}")

# C3 NaN inside active span (between first and last non-NaN)
print("  scanning internal NaNs ...")
internal_nan = 0
for tk in dp.columns:
    s = dp[tk]
    nz = s.notna()
    first = nz.idxmax() if nz.any() else None
    last = nz[::-1].idxmax() if nz.any() else None
    if first is None: continue
    span = s.loc[first:last]
    internal_nan += span.isna().sum()
add("PASS" if internal_nan==0 else "WARN","C3 internal NaN",f"{internal_nan} NaN cells inside active spans")

# ===========================================================================
# D. CROSS-VALIDATION (CORRECTNESS)
# ===========================================================================
print("\n--- D. CROSS-VALIDATION ---")
# D1 long-panel daily return == close[t]/close[t-1]-1
print("  verifying returns panel vs prices ...")
sample_tks = dr["ticker"].drop_duplicates().tolist()[:20]
mismatch = 0
for tk in sample_tks:
    sp = dp[tk].dropna()
    sr = dr[dr["ticker"]==tk].set_index("date")["daily_return"]
    sp_ret = sp.pct_change().dropna()
    common = sp_ret.index.intersection(sr.index)
    if len(common) < 50: continue
    diff = (sp_ret.loc[common] - sr.loc[common]).abs()
    if (diff > 1e-9).any():
        mismatch += 1
add("PASS" if mismatch==0 else "FAIL","D1 panel return==price pct_change",
    f"{mismatch}/{len(sample_tks)} sampled tickers mismatch")

# D2 monthly return == close ratio
mr = pd.read_csv(os.path.join(OUT, "monthly_returns_by_ticker.csv"), parse_dates=["date"])
mm = 0; mc = 0
for tk in mp.columns[:20]:
    a = mp[tk].dropna().pct_change().dropna()
    b = mr[mr["ticker"]==tk].set_index("date")["monthly_return"]
    common = a.index.intersection(b.index)
    if len(common) < 20: continue
    mc += 1
    if (a.loc[common] - b.loc[common]).abs().max() > 1e-9:
        mm += 1
add("PASS" if mm==0 else "FAIL","D2 monthly return==close ratio",f"{mm}/{mc} mismatch")

# D3 twin tracking
print("  twin/share-class tracking ...")
twin_pass = 0; twin_warn = 0; twin_na = 0
twin_results = []
for a, b, corr_min, maxdiff in TWINS:
    if a not in dp.columns or b not in dp.columns:
        twin_na += 1; continue
    sa, sb = dp[a].dropna(), dp[b].dropna()
    common = sa.index.intersection(sb.index)
    if len(common) < 100:
        twin_na += 1; continue
    ra, rb = sa.loc[common].pct_change(), sb.loc[common].pct_change()
    df = pd.concat([ra, rb], axis=1).dropna()
    corr = df.iloc[:,0].corr(df.iloc[:,1])
    ret_diff = (df.iloc[:,0] - df.iloc[:,1]).abs().max()*100
    ok = corr >= corr_min and ret_diff <= maxdiff
    twin_results.append((a,b,round(corr,4),round(ret_diff,3),ok))
    if ok: twin_pass += 1
    else:  twin_warn += 1
for a,b,c,d,ok in twin_results:
    add("PASS" if ok else "WARN","D3 twins",
        f"{a}↔{b}: corr={c} maxRetDiff={d}%  ({'ok' if ok else 'DIVERGES'})")
add("PASS" if twin_warn==0 else "WARN","D3 twins summary",
    f"{twin_pass} pass, {twin_warn} diverge, {twin_na} n/a")

# D4 SPY total-return should exceed ^GSPC price-only over long horizon (dividends)
if "SPY" in dp.columns and "^GSPC" in dp.columns:
    spy = dp["SPY"].dropna(); gspc = dp["^GSPC"].dropna()
    common = spy.index.intersection(gspc.index)
    # cumulative growth ratio over full common history
    spy_grow = spy.loc[common].iloc[-1]/spy.loc[common].iloc[0]
    gspc_grow = gspc.loc[common].iloc[-1]/gspc.loc[common].iloc[0]
    add("PASS" if spy_grow >= gspc_grow else "WARN","D4 SPY vs ^GSPC (TR>price)",
        f"SPY growth {spy_grow:.3f} vs ^GSPC {gspc_grow:.3f} over {fmt(common.min())}->{fmt(common.max())}")

# ===========================================================================
# E. COVERAGE STATS SANITY
# ===========================================================================
print("\n--- E. COVERAGE STATS SANITY ---")
bad = 0
if not ((dc["ann_vol_pct"] >= 0).all()): bad += 1
if not ((dc["pct_positive_days"] >= 0) & (dc["pct_positive_days"] <= 100)).all(): bad += 1
# ann_return should be within plausible [-50,200]% for daily series
if not ((dc["ann_return_pct"] > -60) & (dc["ann_return_pct"] < 250)).all(): bad += 1
add("PASS" if bad==0 else "FAIL","E1 coverage stats bounds",
    f"{bad} stat-bounds violations" if bad else "vol>=0, pct_pos in [0,100], ann_ret in [-60,250]")
# rows == tickers in panel
add("PASS" if len(dc)==dr["ticker"].nunique() else "WARN","E2 coverage rows==panel tickers",
    f"{len(dc)} vs {dr['ticker'].nunique()}")

# ===========================================================================
# F. KNOWN-FAILURE DOCUMENTATION
# ===========================================================================
print("\n--- F. KNOWN-FAILURES ---")
# F1 not-on-Yahoo should be absent from outputs (no junk)
present_anywhere = set(dp.columns) | set(mp.columns) | set(dc["ticker"]) | set(dr["ticker"])
junk = NOT_ON_YAHOO & present_anywhere
add("PASS" if not junk else "FAIL","F1 not-on-Yahoo absent",
    f"{len(NOT_ON_YAHOO)} expected absent; {len(junk)} wrongly present: {sorted(junk)}" if junk
    else f"{len(NOT_ON_YAHOO)} confirmed absent from all outputs")
# F2 5 of 6 monthly-empty present in daily (SPAXX empty both)
daily_only = MONTHLY_EMPTY - {"SPAXX"}
for tk in daily_only:
    if tk in dp.columns and dp[tk].notna().any() and tk not in mp.columns:
        add("PASS","F2 daily-only recovery",f"{tk}: has daily, no monthly (documented quirk)")
    else:
        add("WARN","F2 daily-only recovery",f"{tk}: unexpected state")
if "SPAXX" in dp.columns and not dp["SPAXX"].notna().any():
    add("PASS","F3 SPAXX empty (money mkt)","confirmed empty in daily")

# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "="*78)
counts = {"PASS":0,"WARN":0,"FAIL":0}
for s,_,_ in findings: counts[s]+=1
print(f"SUMMARY: {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL  (total {len(findings)})")
print("="*78)

# write report
rep = pd.DataFrame(findings, columns=["severity","check","detail"])
rep.to_csv(os.path.join(OUT, "integrity_report.csv"), index=False)
print(f"Wrote {os.path.join(OUT,'integrity_report.csv')}")

if counts["FAIL"]:
    print("\n*** FAILURES require attention ***")
    for s,c,d in findings:
        if s=="FAIL": print(f"  - {c}: {d}")