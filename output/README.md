# Monthly Returns Across Asset Classes

Generated: 2026-07-17 21:03 UTC
Source: Yahoo Finance via `yfinance` v1.5.1. Prices are **auto-adjusted**
(split + dividend adjusted = total-return close) for ETFs/stocks, so monthly
returns are **total returns**. Broad indices (^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX) are
price-only (no dividends). ^TNX is a **yield level**, not a price -- it is kept in
`monthly_prices.csv` but excluded from return aggregations.

## Universe
- Asset-class tickers: 214  (ETFs + broad indices for longest history)
- Individual stocks: 128  (large US caps across 11 GICS sectors)
- Total series pulled: 342

## Files (./output)
| File | Description |
|---|---|
| `monthly_returns_by_ticker.csv` | Long panel: every ticker's monthly return with asset_class/sector labels |
| `monthly_returns_by_asset_class.csv` | Wide: equal-weighted monthly return per asset class |
| `monthly_returns_by_sector.csv` | Wide: equal-weighted monthly return per sector (sector ETFs + stocks) |
| `monthly_returns_by_sector_stocks_only.csv` | Wide: sector return from individual stocks only |
| `monthly_prices.csv` | Wide: monthly adjusted close per ticker |
| `universe.csv` | Ticker metadata + first/last month + month count |
| `coverage_summary.csv` | Per-series coverage + annualized return/vol + monthly min/max |
| `asset_class_summary.csv` | Asset-class-level coverage + stats |

## Coverage (as far back as Yahoo provides, monthly interval)
Overall date range: **1962-01 -> 2026-07**
(775 months)

Longest series:
- GE      GE common stock                            1962-02 -> 2026-07 (774 mo)
- IBM     IBM common stock                           1962-02 -> 2026-07 (774 mo)
- HON     HON common stock                           1962-02 -> 2026-07 (774 mo)
- WMT     WMT common stock                           1972-09 -> 2026-07 (647 mo)
- SPGI    SPGI common stock                          1973-03 -> 2026-07 (641 mo)
- EXC     EXC common stock                           1973-06 -> 2026-07 (638 mo)
- FDX     FDX common stock                           1978-05 -> 2026-07 (579 mo)
- DHR     DHR common stock                           1979-01 -> 2026-07 (571 mo)
- CMCSA   CMCSA common stock                         1980-04 -> 2026-07 (556 mo)
- T       T common stock                             1983-12 -> 2026-07 (512 mo)

## Methodology
1. Pull monthly history: `yf.download(tickers, period='max', interval='1mo', auto_adjust=True)`.
2. Monthly return = adjusted close pct_change (month-over-month). Returns indexed to
   month-end timestamps.
3. Asset-class returns = equal-weighted mean of constituent tickers' monthly returns
   each month (using available tickers). Single stocks and sector ETFs are excluded
   from the asset-class aggregate to avoid double counting; sectors get their own file.
4. Sector returns = equal-weighted mean across sector ETF + individual stocks in that
   sector. A stocks-only sector file is also produced.

## Notes / caveats
- Yahoo monthly history for indices generally starts 1985; ETFs start at inception.
  Using the longest-history index per asset class maximizes how far back we can go.
- Total-return vs price-return: ETF/stock returns include dividends; index returns
  (^GSPC etc.) are price-only and will understate total return by the dividend yield.
- Equal-weighting is used for aggregation (no market-cap weights across ETFs/indexes).
- Data is for research/illustration; not investment advice.

## Reproduce
```bash
cd /home/buntu/Stock_Price
.venv/bin/python pull_returns.py
```
