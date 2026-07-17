"""
Pull daily price data across all tickers in the universe as far back as
Yahoo Finance provides (^GSPC goes to 1927). Outputs CSV (parquet optional
if pyarrow/fastparquet installed).

Data source: Yahoo Finance via yfinance.  auto_adjust=True ensures the 'Close'
column is total-return (split+dividend adjusted) for ETFs/stocks.

Outputs (in ./output):
  daily_prices.csv            wide: daily adjusted close per ticker
  daily_returns_by_ticker.csv long panel: every ticker, daily return + labels
  daily_coverage_summary.csv  per-series coverage + stats
  daily_README.md             methodology + coverage notes
"""
from __future__ import annotations
import os, sys, time
from datetime import datetime
import pandas as pd
import yfinance as yf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)

yf.set_tz_cache_location(os.path.join(OUT, "_yf_tz_cache"))
# Rate-limit / network resilience (per yfinance docs: exponential backoff)
try:
    yf.config.network.retries = 5
except Exception:
    pass

# Detect parquet support (optional, for efficient caching)
def _parquet_available():
    try:
        import pyarrow  # noqa
        return True
    except ImportError:
        pass
    try:
        import fastparquet  # noqa
        return True
    except ImportError:
        pass
    return False

HAS_PARQUET = _parquet_available()

# ---------------------------------------------------------------------------
# Import universe from pull_returns (shared ticker definitions + batched dl)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_returns import ALL_TICKERS, _download_batched

TICKERS = list(ALL_TICKERS.keys())
print(f"Universe: {len(TICKERS)} tickers  (parquet={'yes' if HAS_PARQUET else 'no (CSV fallback)'})")

# ---------------------------------------------------------------------------
# DOWNLOAD daily history (period='max', interval='1d')
# ---------------------------------------------------------------------------
CSV_CACHE = os.path.join(OUT, "daily_prices_cache.csv")
PQ_CACHE = os.path.join(OUT, "daily_prices.parquet")

def _load_cache():
    if HAS_PARQUET and os.path.exists(PQ_CACHE):
        print(f"Loading cached daily prices from {PQ_CACHE}")
        df = pd.read_parquet(PQ_CACHE)
        df.index = pd.to_datetime(df.index)
        return df
    if os.path.exists(CSV_CACHE):
        print(f"Loading cached daily prices from {CSV_CACHE}")
        df = pd.read_csv(CSV_CACHE, index_col=0, parse_dates=True)
        return df
    return None

def _save_cache(df):
    if HAS_PARQUET:
        df.to_parquet(PQ_CACHE, compression="zstd")
        print(f"  Saved parquet cache: {PQ_CACHE}")
    else:
        df.to_csv(CSV_CACHE, float_format="%.6f")
        print(f"  Saved CSV cache: {CSV_CACHE}")

prices = _load_cache()
if prices is None:
    prices = _download_batched(TICKERS, interval="1d", period="max")
    prices = prices.loc[~prices.index.duplicated(keep="first")]
    _save_cache(prices)

print(f"Prices shape: {prices.shape}")
print(f"Date range: {prices.index.min().date()} -> {prices.index.max().date()} ({len(prices)} days)")

total_cells = prices.notna().sum().sum()
print(f"Non-NaN cells: {total_cells:,}")

# Report empty tickers
empty = [c for c in prices.columns if prices[c].dropna().empty]
if empty:
    print(f"WARNING: no data for {len(empty)} tickers: {empty}")
    prices = prices.drop(columns=empty)

# ---------------------------------------------------------------------------
# DAILY RETURNS
# ---------------------------------------------------------------------------
returns = prices.pct_change()

# ---------------------------------------------------------------------------
# OUTPUT: wide prices (CSV)
# ---------------------------------------------------------------------------
csv_path = os.path.join(OUT, "daily_prices.csv")
print(f"\nWriting CSV: {csv_path} ...")
prices.to_csv(csv_path, float_format="%.6f")
csv_size = os.path.getsize(csv_path)
print(f"  CSV size: {csv_size / 1024 / 1024:.1f} MB")

# ---------------------------------------------------------------------------
# OUTPUT: long panel returns with metadata (CSV; parquet if available)
# ---------------------------------------------------------------------------
print("Building long daily returns panel ...")
t0 = time.time()
rows = []
for ticker in prices.columns:
    meta = ALL_TICKERS.get(ticker)
    if meta is None:
        continue
    name, asset_class, sector = meta[0], meta[1], meta[2]
    s = returns[ticker].dropna()
    for dt, r in s.items():
        if pd.isna(r):
            continue
        rows.append({
            "date": dt,
            "ticker": ticker,
            "name": name,
            "asset_class": asset_class,
            "sector": sector,
            "daily_return": r,
        })
long_panel = pd.DataFrame(rows).sort_values(["asset_class", "sector", "ticker", "date"])

# Parquet if available
if HAS_PARQUET:
    parq_path = os.path.join(OUT, "daily_returns_by_ticker.parquet")
    long_panel.to_parquet(parq_path, compression="zstd", index=False)
    print(f"   Wrote {parq_path}  rows={len(long_panel):,}")

# Always CSV
csv_returns = os.path.join(OUT, "daily_returns_by_ticker.csv")
long_panel.to_csv(csv_returns, index=False)
csvr_size = os.path.getsize(csv_returns)
elapsed = time.time() - t0
print(f"   Wrote {csv_returns}  rows={len(long_panel):,}  ({csvr_size / 1024 / 1024:.1f} MB, {elapsed:.0f}s)")

# ---------------------------------------------------------------------------
# COVERAGE SUMMARY (per ticker)
# ---------------------------------------------------------------------------
print("Building coverage summary ...")
cov_rows = []
for ticker in returns.columns:
    meta = ALL_TICKERS.get(ticker)
    if meta is None:
        continue
    name, asset_class, sector = meta[0], meta[1], meta[2]
    s = returns[ticker].dropna()
    if s.empty:
        continue
    cov_rows.append({
        "ticker": ticker,
        "name": name,
        "asset_class": asset_class,
        "sector": sector,
        "first_date": s.index.min(),
        "last_date": s.index.max(),
        "n_trading_days": len(s),
        "ann_return_pct": (s.mean() * 252) * 100,
        "ann_vol_pct": (s.std() * (252 ** 0.5)) * 100,
        "min_daily_pct": s.min() * 100,
        "max_daily_pct": s.max() * 100,
        "pct_positive_days": (s > 0).mean() * 100,
    })
cov = pd.DataFrame(cov_rows).sort_values(["asset_class", "sector", "ticker"])
cov_path = os.path.join(OUT, "daily_coverage_summary.csv")
cov.to_csv(cov_path, index=False)
print(f"Wrote {cov_path}  rows={len(cov)}")

# ---------------------------------------------------------------------------
# DAILY README
# ---------------------------------------------------------------------------
def _fmt(d):
    return d.strftime("%Y-%m-%d") if isinstance(d, pd.Timestamp) else str(d)

top10 = cov.sort_values("first_date").head(10)

readme = f"""# Daily Price & Return Data

Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
Source: Yahoo Finance via `yfinance` v{yf.__version__}. Prices are **auto-adjusted**
(split + dividend adjusted = total-return close) for ETFs/stocks.

## Universe
- Total tickers: {len(TICKERS)}
- Tickers with data: {len(prices.columns)}
- Date range: **{_fmt(prices.index.min())} -> {_fmt(prices.index.max())}** ({len(prices)} trading days)
- Non-NaN data cells: {total_cells:,}

## Longest daily histories
| Ticker | Name | Start | End | Trading Days |
|---|---|---|---|---|
"""
for _, r in top10.iterrows():
    readme += f"| {r['ticker']:6s} | {str(r['name'])[:40]:40s} | {_fmt(r['first_date'])} | {_fmt(r['last_date'])} | {r['n_trading_days']} |\n"

readme += f"""
## Files (./output)
| File | Format | Description |
|---|---|---|
| `daily_prices.csv` | CSV | Wide: daily adjusted close per ticker |
| `daily_returns_by_ticker.csv` | CSV | Long panel: every ticker's daily return + labels |
| `daily_coverage_summary.csv` | CSV | Per-series coverage + annualized stats |
"""
if HAS_PARQUET:
    readme += "| `daily_prices.parquet` | Parquet | Efficient cache (same data as CSV) |\n"
    readme += "| `daily_returns_by_ticker.parquet` | Parquet | Long panel (same data as CSV) |\n"

readme += f"""
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
"""
with open(os.path.join(OUT, "daily_README.md"), "w") as f:
    f.write(readme)
print("Wrote daily_README.md")

print("\n=== DONE ===")
print(f"Overall: {_fmt(prices.index.min())} -> {_fmt(prices.index.max())} ({len(prices)} trading days)")
print(f"Output dir: {OUT}")
print(f"Files:")
for fn in sorted(os.listdir(OUT)):
    fp = os.path.join(OUT, fn)
    if os.path.isfile(fp):
        sz = os.path.getsize(fp)
        if sz > 1024*1024:
            print(f"  {fn:40s} {sz/1024/1024:8.1f} MB")
        else:
            print(f"  {fn:40s} {sz:8d} B")
