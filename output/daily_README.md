# Daily Price & Return Data

Generated: 2026-07-17 20:56 UTC
Source: Yahoo Finance via `yfinance` v1.5.1. Prices are **auto-adjusted**
(split + dividend adjusted = total-return close) for ETFs/stocks.

## Universe
- Total tickers: 342
- Tickers with data: 341
- Date range: **1927-12-30 -> 2026-07-17** (24753 trading days)
- Non-NaN data cells: 2,715,796

## Longest daily histories
| Ticker | Name | Start | End | Trading Days |
|---|---|---|---|---|
| ^GSPC  | S&P 500 Index                            | 1928-01-03 | 2026-07-17 | 24750 |
| IBM    | IBM common stock                         | 1962-01-03 | 2026-07-17 | 16241 |
| LMT    | LMT common stock                         | 1962-01-03 | 2026-07-17 | 16239 |
| AEP    | AEP common stock                         | 1962-01-03 | 2026-07-17 | 16241 |
| HON    | HON common stock                         | 1962-01-03 | 2026-07-17 | 16241 |
| XOM    | XOM common stock                         | 1962-01-03 | 2026-07-17 | 16241 |
| DIS    | DIS common stock                         | 1962-01-03 | 2026-07-17 | 16241 |
| GE     | GE common stock                          | 1962-01-03 | 2026-07-17 | 16241 |
| JNJ    | JNJ common stock                         | 1962-01-03 | 2026-07-17 | 16241 |
| BA     | BA common stock                          | 1962-01-03 | 2026-07-17 | 16241 |

## Files (./output)
| File | Format | Description |
|---|---|---|
| `daily_prices.csv` | CSV | Wide: daily adjusted close per ticker |
| `daily_returns_by_ticker.csv` | CSV | Long panel: every ticker's daily return + labels |
| `daily_coverage_summary.csv` | CSV | Per-series coverage + annualized stats |
| `daily_prices.parquet` | Parquet | Efficient cache (same data as CSV) |
| `daily_returns_by_ticker.parquet` | Parquet | Long panel (same data as CSV) |

## Reproduce
```bash
.venv/bin/python pull_daily.py
```

## Notes
- ^GSPC daily history starts **1927-12-30** — the longest series available.
- Broad indices (^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX) are price-only (no dividends).
- ^TNX, ^FVX, ^TYX are **yield levels**, not prices — kept in prices but returns are meaningless.
- Daily returns are simple pct_change (day-over-day).
- Annualized return/vol assumes 252 trading days/year.
- Data is for research purposes only; not investment advice.
