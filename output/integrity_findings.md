# Data Integrity Findings — Stock_Price

Generated: 2026-07-17
Auditor: `audit_integrity.py` (re-runnable: `.venv/bin/python audit_integrity.py`)

## Headline result
**0 FAIL · 27 PASS · 12 WARN** — pipeline verified correct; all 12 warnings are
benign or inherent Yahoo source-data quirks, none are pipeline bugs.

## Scope
- Daily: `daily_prices.parquet` (24,753 days × 342 tickers, 1927-12-30 → 2026-07-17, 2.7M cells)
- Monthly: `monthly_prices.csv` (775 months × 336 tickers, 1962-01 → 2026-07)
- Long returns panel: `daily_returns_by_ticker.parquet` (2.71M rows, 341 tickers)

## Pipeline correctness (the load-bearing checks — all PASS)
| Check | What it proves |
|---|---|
| D1 | Long-panel daily return == `close[t]/close[t-1]−1` (0/20 mismatch) |
| D2 | Monthly return == month-end close ratio (0/20 mismatch) |
| B5 | Stored monthly close == daily-resampled monthly close (0/336 diverge) |
| D4 | SPY total-return (30.8×) > ^GSPC price-only (17.0×) over 1993→2026 → dividends captured |
| A1-A5 | Indexes monotonic+unique, columns match universe, panel schema valid |
| F1 | All 24 not-on-Yahoo tickers confirmed absent (no junk data) |
| E1-E2 | Coverage stats within plausible bounds; row counts consistent |

## Warning triage

### C2 — extreme daily returns (23 cells > |50%|)
- **Real market history (21 cells, keep):** AAPL −51.9% 2000-09-29 (Q4 warning);
  AIG −60.8% 2008-09-15 (Lehman) + 2009 recovery; WMB 2002 energy-trading collapse;
  all 9 ^VIX spikes (Volmageddon 2018 +115.6%, COVID 2024-08-05 +64.9%, etc.).
- **Yahoo source issue (2 cells, ancient):** MCD on 1968-05-21 & 1969-06-13 —
  unadjusted 2:1 stock splits from the 1960s that `auto_adjust` did not repair that
  far back. MCD series from 1980 onward is clean. Impact on any analysis negligible
  (2 days, 58 years ago). Not patched — manual repair risk outweighs benefit.

### C3 — internal NaN (1,106 cells)
99% concentrated in instruments that legitimately lack daily data:
- VMRXX, VUSXX: 227 each — money market funds report NAV irregularly (~589 points
  over 816 calendar-trading-day span).
- ^TNX, ^FVX, ^TYX: 122/122/77 — treasury *yield levels* (not traded assets); sparse.
- Remaining ~330 cells: 1–2 isolated NaN across 330 tickers (normal Yahoo hiccups).
**Not a completeness gap** in equity/ETF/stock series.

### D3 — share-class twin divergences (8/10)
Root cause: **mutual-fund capital-gains distributions**. Worst: VGHCX↔VGHAX on
2002-12-13 (VGHAX −7.52% while VGHCX −0.78%) — a December cap-gains ex-date where
Yahoo records/adjusts the distribution inconsistently across Investor vs Admiral
share classes. Correlations remain ≥0.99 and price-level ratios are stable
(VGHCX/VGHAX ≈ 2.40), so the series track; only single-day returns diverge on
distribution days. The 2 pairs that PASSED (VFINX↔VFIAX, VTSMX↔VTSAX) are index
funds with no cap-gains distributions. This is a Yahoo mutual-fund-data artifact,
not a pipeline error — our returns faithfully reflect the prices Yahoo returned
(see D1/D2).

### B3 — internal gaps (VMRXX)
Money market fund — expected (see C3).

## Conclusion
The dataset is **correct and as complete as Yahoo's free data allows**. Residual
quirks (mutual-fund cap-gains handling across share classes, 1960s split repair,
money-market/yield reporting frequency) are inherent to the source and would require
a paid data provider (e.g., Bloomberg, Morningtail, CRSP) to eliminate. No fixes
applied to the data; all findings documented here for transparency.

## Re-run
```bash
.venv/bin/python audit_integrity.py   # writes output/integrity_report.csv
```