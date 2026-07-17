# Handoff — Stock_Price

## Goal
Download all ticker data as far back as Yahoo Finance provides, at the highest
granularity available (daily + monthly).

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

## Next steps (open)
- Push branch + open PR if desired.
- Optionally: remove the 6 always-empty tickers from the universe, or re-pull them
  with explicit start/end dates instead of `period=max`.
- `datetime.utcnow()` deprecation warnings in both scripts (cosmetic).
EOF