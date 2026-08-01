"""
Pull monthly returns across asset classes (and individual stocks grouped into
asset classes / sectors) as far back as Yahoo Finance provides.

Data source: Yahoo Finance via yfinance.  yfinance v1.5+ returns *auto-adjusted*
prices by default, so the 'Close' column is a total-return (split+dividend
adjusted) close for ETFs/stocks -- the right basis for monthly returns.

Outputs (in ./output):
  monthly_returns_by_ticker.csv     long panel: every ticker, monthly return, labels
  monthly_returns_by_asset_class.csv wide: asset-class equal-weighted monthly returns
  monthly_returns_by_sector.csv     wide: GICS sector equal-weighted monthly returns (stocks)
  monthly_prices.csv                wide: monthly adjusted close per ticker
  coverage_summary.csv              per-series coverage + stats (start,end,n,mean,std,min,max)
  universe.csv                      the ticker universe with metadata
  README.md                         methodology + coverage notes
"""
from __future__ import annotations
import os, sys, time, json
from datetime import datetime
import pandas as pd
import yfinance as yf

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Rate-limit / network resilience configuration
# Yahoo will 401/429 or silently empty responses if hit too hard.
# ---------------------------------------------------------------------------
yf.set_tz_cache_location(os.path.join(OUT, "_yf_tz_cache"))
try:
    yf.config.network.retries = 5          # exponential backoff: 1s,2s,4s,8s,16s
except Exception:
    pass  # older yfinance versions
DOWNLOAD_BATCH_SIZE = 50                   # tickers per yf.download() call
INTER_BATCH_SLEEP_S = 3.0                  # pause between batches


def _download_batched(tickers, interval, period="max"):
    """Download history in chunks to respect Yahoo rate limits.
    Returns a wide DataFrame indexed by date, one column per ticker."""
    chunks = [tickers[i:i+DOWNLOAD_BATCH_SIZE] for i in range(0, len(tickers), DOWNLOAD_BATCH_SIZE)]
    print(f"\nDownloading {len(tickers)} tickers in {len(chunks)} batches "
          f"(batch={DOWNLOAD_BATCH_SIZE}, sleep={INTER_BATCH_SLEEP_S}s, retries={getattr(yf.config,'network',None) and getattr(yf.config.network,'retries','?')}) ...", flush=True)
    frames = []
    for i, chunk in enumerate(chunks, 1):
        t0 = time.time()
        data = yf.download(
            tickers=chunk,
            period=period,
            interval=interval,
            auto_adjust=True,
            actions=False,
            group_by="column",
            threads=True,
            progress=False,
            ignore_tz=True,
            timeout=60,
        )
        elapsed = time.time() - t0
        if isinstance(data.columns, pd.MultiIndex):
            close = data["Close"].copy()
        else:
            close = data.to_frame(name=chunk[0]) if data.ndim == 1 else data.copy()
        close.index = pd.to_datetime(close.index)
        # normalize to month-end for monthly, else keep as-is
        if interval == "1mo":
            close.index = close.index.to_period("M").to_timestamp("M")
        close = close.sort_index()
        frames.append(close)
        n_cols = len(close.columns)
        print(f"  batch {i}/{len(chunks)}: {len(chunk)} tk -> {n_cols} cols, {len(close)} rows ({elapsed:.0f}s)", flush=True)
        if i < len(chunks):
            time.sleep(INTER_BATCH_SLEEP_S)
    if not frames:
        raise SystemExit("All batches returned empty")
    # Outer-join on date index so tickers with different histories align
    merged = pd.concat(frames, axis=1).sort_index()
    merged = merged.loc[~merged.index.duplicated(keep="first")]
    return merged

# ---------------------------------------------------------------------------
# 1-2. UNIVERSE + RETURN-SERIES POLICY
#     Moved to universe.py so consumers that only need the ticker list do
#     not have to import this module (which configures yfinance).
# ---------------------------------------------------------------------------
from universe import (  # noqa: E402,F401
    ASSET_TICKERS, STOCK_SECTORS, STOCKS, ALL_TICKERS,
    NON_RETURN_KINDS, NON_RETURN_TICKERS, is_return_series,
    aggregatable_groups, equal_weight,
)

# ---------------------------------------------------------------------------
# 3. DOWNLOAD  monthly history (period='max', interval='1mo')
#    Uses _download_batched() to respect Yahoo rate limits.
# ---------------------------------------------------------------------------
def download_all(tickers: list[str]) -> pd.DataFrame:
    """Download monthly adjusted close for all tickers. Returns wide DataFrame
    indexed by month-end date with one column per ticker (adjusted close)."""
    return _download_batched(tickers, interval="1mo", period="max")

# ---------------------------------------------------------------------------
# 3b. PIPELINE ENTRY POINT
#     Everything below runs ONLY as a script. Previously this executed at
#     import time, so `import pull_returns` triggered a full Yahoo download
#     and overwrote every monthly CSV -- pull_daily.py imports this module,
#     and so does build_aggregates.py (for the universe + return policy).
# ---------------------------------------------------------------------------
def main() -> None:
    prices = download_all(list(ALL_TICKERS.keys()))
    print("Raw prices shape:", prices.shape)
    print("Date range:", prices.index.min(), "->", prices.index.max())

    # Drop tickers that came back entirely empty
    empty = [c for c in prices.columns if prices[c].dropna().empty]
    if empty:
        print("WARNING: no data for", empty)
        prices = prices.drop(columns=empty)

    # ---------------------------------------------------------------------------
    # 4. MONTHLY RETURNS  (pct change of adjusted close). Yields/VIX levels kept as-is
    #    in prices but NOT used in return aggregation.
    # ---------------------------------------------------------------------------
    returns = prices.pct_change()

    # ---------------------------------------------------------------------------
    # 5. LONG PANEL with metadata
    # ---------------------------------------------------------------------------
    rows = []
    for ticker in prices.columns:
        meta = ALL_TICKERS.get(ticker)
        if meta is None:
            continue
        name, asset_class, sector = meta[0], meta[1], meta[2]
        s = returns[ticker].dropna()
        for dt, r in s.items():
            rows.append({
                "date": dt,
                "ticker": ticker,
                "name": name,
                "asset_class": asset_class,
                "sector": sector,
                "monthly_return": r,
            })
    long_panel = pd.DataFrame(rows).sort_values(["asset_class","sector","ticker","date"])
    long_panel.to_csv(os.path.join(OUT, "monthly_returns_by_ticker.csv"), index=False)
    print("Wrote monthly_returns_by_ticker.csv rows=", len(long_panel))

    # ---------------------------------------------------------------------------
    # 6. ASSET-CLASS LEVEL  equal-weighted monthly return across constituents
    #    (average of available tickers' returns each month within the asset class)
    # ---------------------------------------------------------------------------
    # Shared with build_aggregates.py via universe.py, so a live re-pull and an
    # offline rebuild cannot drift apart.
    ac_groups = aggregatable_groups(ALL_TICKERS, returns.columns)
    ac_wide = equal_weight(returns, ac_groups)
    ac_wide.to_csv(os.path.join(OUT, "monthly_returns_by_asset_class.csv"))
    print("Wrote monthly_returns_by_asset_class.csv shape=", ac_wide.shape)

    # Sector level (from sector ETFs + individual stocks)
    sec_groups = {}
    for ticker, meta in ALL_TICKERS.items():
        name, asset_class, sector = meta[0], meta[1], meta[2]
        if ticker not in returns.columns:
            continue
        if not is_return_series(ticker, meta):
            continue  # yield/price-only levels are not returns -- see §2b
        sec = sector
        if not sec:
            continue
        # NOTE: `sector` here is meta[2], which holds the *kind* for asset tickers
        # and the GICS sector only for single stocks -- so this strip never fires
        # (the "Sector-" values live in meta[1]) and the composite columns are
        # kinds (ETF/MUTUALFUND/...) alongside real GICS sectors.
        if sec.startswith("Sector-"):
            sec = sec.replace("Sector-","")
        sec_groups.setdefault(sec, []).append(ticker)
    sec_wide = pd.DataFrame(index=returns.index)
    for sec, tks in sec_groups.items():
        sub = returns[tks]
        sec_wide[sec] = sub.mean(axis=1, skipna=True)
    sec_wide = sec_wide.dropna(how="all").sort_index()
    sec_wide.to_csv(os.path.join(OUT, "monthly_returns_by_sector.csv"))
    print("Wrote monthly_returns_by_sector.csv shape=", sec_wide.shape)

    # Stock-only sector aggregation (so sector returns reflect single stocks only)
    stock_sec = {}
    for ticker, (name, asset_class, sector) in STOCKS.items():
        if ticker not in returns.columns:
            continue
        stock_sec.setdefault(sector, []).append(ticker)
    stock_sec_wide = pd.DataFrame(index=returns.index)
    for sec, tks in stock_sec.items():
        sub = returns[tks]
        stock_sec_wide[sec] = sub.mean(axis=1, skipna=True)
    stock_sec_wide = stock_sec_wide.dropna(how="all").sort_index()
    stock_sec_wide.to_csv(os.path.join(OUT, "monthly_returns_by_sector_stocks_only.csv"))
    print("Wrote monthly_returns_by_sector_stocks_only.csv shape=", stock_sec_wide.shape)

    # ---------------------------------------------------------------------------
    # 7. PRICES (wide) + UNIVERSE + COVERAGE SUMMARY
    # ---------------------------------------------------------------------------
    prices.to_csv(os.path.join(OUT, "monthly_prices.csv"))

    uni_rows = []
    for ticker, meta in ALL_TICKERS.items():
        name, asset_class, sector = meta[0], meta[1], meta[2]
        if ticker in prices.columns:
            s = prices[ticker].dropna()
            first = s.index.min(); last = s.index.max(); n = len(s)
        else:
            first=last=pd.NaT; n=0
        uni_rows.append({"ticker":ticker,"name":name,"asset_class":asset_class,
                         "sector":sector,"first_month":first,"last_month":last,
                         "n_months":n,"present":ticker in prices.columns})
    uni = pd.DataFrame(uni_rows)
    uni.to_csv(os.path.join(OUT, "universe.csv"), index=False)

    cov_rows = []
    for ticker in returns.columns:
        meta = ALL_TICKERS.get(ticker)
        if meta is None: continue
        name, asset_class, sector = meta[0], meta[1], meta[2]
        s = returns[ticker].dropna()
        if s.empty:
            continue
        cov_rows.append({
            "ticker":ticker,"name":name,"asset_class":asset_class,"sector":sector,
            "first_month":s.index.min(),"last_month":s.index.max(),"n_months":len(s),
            "ann_return_pct": (s.mean()*12)*100,
            "ann_vol_pct": (s.std()* (12**0.5))*100,
            "min_month_pct": s.min()*100,
            "max_month_pct": s.max()*100,
            "pct_positive_months": (s>0).mean()*100,
        })
    cov = pd.DataFrame(cov_rows).sort_values(["asset_class","sector","ticker"])
    cov.to_csv(os.path.join(OUT, "coverage_summary.csv"), index=False)
    print("Wrote coverage_summary.csv rows=", len(cov))

    # Asset-class level coverage stats
    ac_cov_rows = []
    for ac, tks in ac_groups.items():
        s = ac_wide[ac].dropna()
        if s.empty: continue
        ac_cov_rows.append({"asset_class":ac,"first_month":s.index.min(),"last_month":s.index.max(),
                            "n_months":len(s),"ann_return_pct":(s.mean()*12)*100,
                            "ann_vol_pct":(s.std()*(12**0.5))*100,
                            "min_month_pct":s.min()*100,"max_month_pct":s.max()*100})
    pd.DataFrame(ac_cov_rows).to_csv(os.path.join(OUT, "asset_class_summary.csv"), index=False)

    # ---------------------------------------------------------------------------
    # 8. README
    # ---------------------------------------------------------------------------
    def _fmt(d): return d.strftime("%Y-%m") if isinstance(d, pd.Timestamp) else str(d)
    readme = f"""# Monthly Returns Across Asset Classes

Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
Source: Yahoo Finance via `yfinance` v{yf.__version__}. Prices are **auto-adjusted**
(split + dividend adjusted = total-return close) for ETFs/stocks, so monthly
returns are **total returns**. Broad indices (^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX) are
price-only (no dividends). ^TNX is a **yield level**, not a price -- it is kept in
`monthly_prices.csv` but excluded from return aggregations.

## Universe
- Asset-class tickers: {len(ASSET_TICKERS)}  (ETFs + broad indices for longest history)
- Individual stocks: {len(STOCKS)}  (large US caps across {len(STOCK_SECTORS)} GICS sectors)
- Total series pulled: {len(ALL_TICKERS)}

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
Overall date range: **{_fmt(prices.index.min())} -> {_fmt(prices.index.max())}**
({len(prices)} months)

Longest series:
"""
    top10 = cov.sort_values("first_month").head(10)
    for _,r in top10.iterrows():
        readme += f"- {r['ticker']:7s} {r['name'][:42]:42s} {_fmt(r['first_month'])} -> {_fmt(r['last_month'])} ({r['n_months']} mo)\n"

    readme += """
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
.venv/bin/python pull_returns.py
```
"""
    with open(os.path.join(OUT,"README.md"),"w") as f:
        f.write(readme)
    print("Wrote README.md")

    print("\n=== DONE ===")
    print("Overall:", _fmt(prices.index.min()), "->", _fmt(prices.index.max()), f"({len(prices)} months)")
    print("Output dir:", OUT)


if __name__ == "__main__":
    main()
