# Handoff — Stock_Price

## Goal
Download all ticker data as far back as Yahoo Finance provides, at the highest
granularity available (daily + monthly).

## Documentation
Full system docs live in `docs/` — start at `docs/README.md`:
- `docs/data_dictionary.md` — every output file, field-by-field
- `docs/coverage.md` — date ranges, per-ticker/asset-class/sector coverage
- `docs/methodology.md` — how values are derived (adjustment, returns, aggregation)
- `docs/nuances_and_caveats.md` — data quirks + integrity-audit triage
- `docs/scripts_reference.md` — the 3 scripts, config, reproducibility
Root `README.md` is the entry point.

## Current state (2026-07-17)
- Branch: `feat/expand-universe-daily-download` (commit 330ab25), **not yet pushed / no PR**.
- Universe: **342 tickers** (71 original asset-class + 128 individual stocks + 143 new
  mutual funds/ETFs/crypto from user-provided list). Defined in `pull_returns.py`
  (`ASSET_TICKERS` + `STOCK_SECTORS`).
- **Daily data**: `output/daily_prices.parquet` (+ CSV). 24,753 days, 1927-12-30 →
  2026-07-17, 341 tickers with data (only SPAXX empty — money market, only 1d/5d).
  2.7M data cells. Long returns panel: `daily_returns_by_ticker.parquet` (2.71M rows).
- **Monthly data**: `output/monthly_prices.csv` etc. 775 months, 1962-01 → 2026-07,
  336 tickers. 6 fail monthly `period=max`: PADMX, PAGPX, PIGLX, AUBAX, LOMMX, SPAXX.
  (5 of those DO have daily data — Yahoo quirk; monthly aggregate unavailable.)

## How to reproduce
```bash
.venv/bin/python pull_returns.py   # monthly (refresh all 342)
.venv/bin/python pull_daily.py     # daily  (uses cached parquet if present)
```
Deps: `pip install -r requirements.txt` (needs `pyarrow` for parquet).

## Architecture notes
- `_download_batched()` in `pull_returns.py` is the shared download helper (batch=50,
  3s sleep, `yf.config.network.retries=5`, 60s timeout). `pull_daily.py` imports it.
- `pull_daily.py` caches `output/daily_prices.parquet`; delete it to force re-download.
- Outputs: parquet (efficient, tracked) for daily; CSV for monthly. Large daily CSVs
  (daily_prices.csv 31MB, daily_returns_by_ticker.csv 229MB) are gitignored.

## Known caveats
- 5 tickers have daily but not monthly history (PADMX/PAGPX/PIGLX/AUBAX/LOMMX).
- SPAXX empty for both (money market).
- Broad indices (^GSPC/^DJI/^IXIC/^RUT/^VIX) are price-only (no dividends).
- ^TNX/^FVX/^TYX are yield levels, not prices — kept in prices but returns meaningless.
- 24 user-listed tickers are not on Yahoo at all (delisted): CMR, FPIDX, KBONX, PGBDX,
  PGLIX, PINVX, VAB, VCE, VCN, VDAIX, VDMIX, VEE, VFSVX, VFTSX, VFV, VFWIX, VGV,
  VHDYX, VIU, VMMXX, VSP, VTGMX, VTWSX, VXC.

## Data integrity pass (2026-07-17)
- Audited by `audit_integrity.py` (6 dimensions A-F) → `output/integrity_report.csv`,
  triage written up in `output/integrity_findings.md`.
- **Result: 0 FAIL · 27 PASS · 12 WARN — pipeline verified correct.**
- Pipeline correctness proven (D1/D2/B5/D4): returns exactly equal price pct_change;
  monthly==daily-resampled; SPY total-return (30.8×) > ^GSPC price-only (17.0×).
- All 12 WARN explained (none are bugs):
  - C2 extreme returns: 21 real market events (AAPL 2000, AIG 2008, WMB 2002, ^VIX
    spikes) + 2 ancient unadjusted splits (MCD 1968/1969 — Yahoo source gap, not patched).
  - C3 internal NaN (1,106): 99% in money market (VMRXX/VUSXX 227 each) + yield indices
    (^TNX/^FVX/^TYX) which legitimately lack daily data; rest are 1-2 isolated cells.
  - D3 share-class twin divergences: mutual-fund capital-gains-distribution timing in
    Yahoo source across Investor/Admiral share classes (corr ≥0.99, level ratios stable).
  - B3 gaps: VMRXX (money market, expected).
- No data patched; all findings documented for transparency.

## Next steps (open)
- Push branch + open PR if desired.
- Optionally: remove the 6 always-empty tickers from the universe, or re-pull them
  with explicit start/end dates instead of `period=max`.
- `datetime.utcnow()` deprecation warnings in both scripts (cosmetic).
EOF