# Stock_Price — System Documentation

A self-contained research dataset of **daily + monthly prices and returns** for **342
tickers** spanning US & international equities, bonds, treasuries, municipals, REITs,
commodities, gold/silver, digital assets, currencies, preferred stock, volatility,
money market, and 128 large-cap US individual stocks across 11 GICS sectors.

- **Source:** Yahoo Finance via `yfinance` v1.5.1
- **Granularity:** daily (highest available) + monthly
- **History:** as far back as Yahoo provides — daily back to **1927-12-30** (^GSPC),
  monthly back to **1962-01**; through **2026-07-17** (daily) / **2026-07-31** (monthly)
- **Adjustment:** auto-adjusted close (split + dividend adjusted = **total-return close**)
  for ETFs/stocks/mutual funds; broad indices are price-only
- **Integrity:** audited — **0 FAIL · 27 PASS · 12 WARN (all benign)** — see
  [nuances_and_caveats.md](nuances_and_caveats.md)

---

## Documentation map

| Document | What it covers |
|---|---|
| [data_dictionary.md](data_dictionary.md) | **Every output file**: purpose, shape, columns (name · type · meaning · example), sample rows, relationships between files |
| [coverage.md](coverage.md) | Date ranges, per-ticker / per-asset-class / per-sector coverage, longest histories, cell counts |
| [methodology.md](methodology.md) | How data is pulled, adjusted, returns computed, aggregated, annualized; equal-weighting; what is excluded |
| [nuances_and_caveats.md](nuances_and_caveats.md) | Data quirks, known issues, the integrity-audit triage, what is *not* fixable from Yahoo |
| [scripts_reference.md](scripts_reference.md) | The 3 scripts (`pull_returns.py`, `pull_daily.py`, `audit_integrity.py`), config, reproducibility, env |

Start at **data_dictionary.md** to learn the files; **methodology.md** to understand
how values are derived; **nuances_and_caveats.md** before trusting any edge case.

---

## System architecture (one-glance)

```
pull_returns.py  ──(monthly, period=max, interval=1mo)──►  output/monthly_*.csv
       │                                                    output/universe.csv
       │                                                    output/coverage_summary.csv
       │                                                    output/asset_class_summary.csv
       │  defines ALL_TICKERS + _download_batched()  ◄── shared download helper
       ▼
pull_daily.py  ──(daily, period=max, interval=1d, cached)──►  output/daily_prices.parquet
                                                               output/daily_returns_by_ticker.parquet
                                                               output/daily_coverage_summary.csv
       ▼
audit_integrity.py  ──(reads all outputs)──►  output/integrity_report.csv
                                              output/integrity_findings.md
```

- `pull_returns.py` is the **source of truth for the universe** (`ASSET_TICKERS` +
  `STOCK_SECTORS` → `ALL_TICKERS`) and exports the shared `_download_batched()` helper.
- `pull_daily.py` imports the universe + helper from `pull_returns.py` so the two
  never drift apart.
- `audit_integrity.py` independently re-derives returns from prices and cross-checks
  the stored panels — it is the verification layer, not a data producer.

---

## Quick start

```bash
cd /home/buntu/Stock_Price
pip install -r requirements.txt          # yfinance, pandas, numpy, pyarrow, requests

.venv/bin/python pull_returns.py         # monthly outputs  (refresh all 342 tickers)
.venv/bin/python pull_daily.py           # daily outputs    (uses cached parquet if present)
.venv/bin/python audit_integrity.py      # integrity report (PASS/WARN/FAIL)
```

Daily download caches `output/daily_prices.parquet`; delete it to force a full re-pull.
Large CSVs (`daily_prices.csv` 31 MB, `daily_returns_by_ticker.csv` 229 MB) are
gitignored — the **parquet** equivalents hold identical data at ~1/10th the size and
are tracked. Regenerate CSVs anytime by re-running `pull_daily.py`.

---

## Universe at a glance

| Bucket | Count |
|---|---|
| Total tickers defined | 342 |
| Tickers with monthly data | 336 |
| Tickers with daily data | 341 |
| Monthly-empty (daily-only or fully empty) | 6 — `PADMX, PAGPX, PIGLX, AUBAX, LOMMX, SPAXX` |
| Individual stocks (11 GICS sectors) | 128 |
| Mutual funds | 115 |
| ETFs | 87 |
| Broad indices (`^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX`) | 5 |
| Treasury yield series (`^TNX, ^FVX, ^TYX`) | 3 |
| Money market funds | 3 |
| Audited & excluded (not on Yahoo / delisted) | 24 — see nuances |

**Asset classes (19):** US Equity, International Equity, World Equity, US Bonds,
US Treasuries, US Corporate Bonds, US Municipal Bonds, International Bonds, EM Bonds,
Gold, Silver, Gold/Precious Metals, US REIT, Commodities, Digital Assets, Currency,
Preferred Stock, Volatility, Money Market — plus `Equity (single stock)` for the 128
individuals and `Sector-*` sub-classes for sector-specialist funds.

---

## Provenance & license

Data sourced from Yahoo Finance via the open-source `yfinance` library for
**research / illustration purposes only**. Not investment advice. Yahoo's free feeds
carry no SLA and contain the quirks documented in nuances_and_caveats.md; a paid
provider (Bloomberg, CRSP, Morningstar) would be required to eliminate them.