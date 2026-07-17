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

yf.set_tz_cache_location(os.path.join(OUT, "_yf_tz_cache"))

# ---------------------------------------------------------------------------
# 1. ASSET-CLASS UNIVERSE
#    Each entry: ticker -> (name, asset_class, kind, notes)
#    kind in {ETF, INDEX, FUTURES, YIELD}
#    For broad indices we include both the investable ETF and the long-history
#    index so we get the longest possible monthly history per asset class.
# ---------------------------------------------------------------------------
ASSET_TICKERS = {
    # ---- US Equity ----
    "^GSPC":  ("S&P 500 Index",                 "US Equity",            "INDEX",   "S&P 500 price index; monthly back to ~1985"),
    "SPY":    ("SPDR S&P 500 ETF",              "US Equity",            "ETF",     "S&P 500 total return; since 1993"),
    "VTI":    ("Vanguard Total US Market ETF",  "US Equity",            "ETF",     "CRSP US total market; since 2001"),
    "QQQ":    ("Invesco Nasdaq-100 ETF",        "US Equity",            "ETF",     "Nasdaq-100; since 1999"),
    "^IXIC":  ("Nasdaq Composite Index",        "US Equity",            "INDEX",   "Nasdaq composite; back to ~1985"),
    "^DJI":   ("Dow Jones Industrial Avg",      "US Equity",            "INDEX",   "Dow 30; back to ~1985"),
    "IWM":    ("iShares Russell 2000 ETF",      "US Equity",            "ETF",     "US small cap; since 2000"),
    "^RUT":   ("Russell 2000 Index",            "US Equity",            "INDEX",   "US small cap index; back to ~1985"),
    "SPHB":   ("Invesco S&P 500 High Beta ETF", "US Equity",            "ETF",     "high-beta slice; since 2011"),
    # ---- International / Emerging Equity ----
    "EFA":    ("iShares MSCI EAFE ETF",         "International Equity", "ETF",     "developed ex-US; since 2001"),
    "VEA":    ("Vanguard FTSE Developed ETF",  "International Equity", "ETF",     "developed ex-US; since 2007"),
    "VWO":    ("Vanguard Emerging Markets ETF","International Equity", "ETF",     "emerging markets; since 2005"),
    "EEM":    ("iShares MSCI Emerging ETF",    "International Equity", "ETF",     "emerging markets; since 2003"),
    "VXUS":   ("Vanguard Total Intl Stock ETF","International Equity", "ETF",     "ex-US total; since 2011"),
    # ---- Fixed Income ----
    "AGG":    ("iShares Core US Aggregate Bond","US Bonds",            "ETF",     "investment-grade agg; since 2003"),
    "BND":    ("Vanguard Total Bond Market",   "US Bonds",             "ETF",     "broad US bonds; since 2007"),
    "IEF":    ("iShares 7-10yr Treasury",      "US Treasuries",        "ETF",     "intermediate treasuries; since 2002"),
    "TLT":    ("iShares 20+yr Treasury Bond",   "US Treasuries",        "ETF",     "long treasuries; since 2002"),
    "SHY":    ("iShares 1-3yr Treasury",        "US Treasuries",        "ETF",     "short treasuries; since 2002"),
    "LQD":    ("iShares IG Corporate Bond",     "US Corporate Bonds",   "ETF",     "investment-grade corp; since 2002"),
    "HYG":    ("iShares High Yield Corp Bond",  "US Corporate Bonds",   "ETF",     "high yield; since 2007"),
    "TIP":    ("iShares TIPS Bond",             "US Bonds",             "ETF",     "inflation-protected treasuries; since 2003"),
    "MUB":    ("iShares National Muni Bond",    "US Municipal Bonds",   "ETF",     "tax-exempt munis; since 2007"),
    "^TNX":   ("CBOE 10yr Treasury Yield",      "US Treasuries",        "YIELD",   "yield LEVEL (not a price); back to ~1985"),
    # ---- Real Assets ----
    "GLD":    ("SPDR Gold Shares",             "Gold",                 "ETF",     "gold; since 2004"),
    "IAU":    ("iShares Gold Trust",           "Gold",                 "ETF",     "gold; since 2005"),
    "SLV":    ("iShares Silver Trust",         "Silver",               "ETF",     "silver; since 2006"),
    "VNQ":    ("Vanguard Real Estate ETF",      "US REIT",              "ETF",     "US REITs; since 2004"),
    "IYR":    ("iShares US Real Estate ETF",   "US REIT",              "ETF",     "US real estate; since 2000"),
    "DBC":    ("Invesco DB Commodity Index",   "Commodities",          "ETF",     "broad commodities; since 2006"),
    "GSG":    ("iShares S&P GSCI Commodity",   "Commodities",          "ETF",     "broad commodities; since 2006"),
    "PDBC":   ("Invesco Optimum Yield Commodity","Commodities",        "ETF",     "broad commodities; since 2014"),
    # ---- Sector Equity ETFs (also feed 'asset class = sector equity') ----
    "XLE":    ("Energy Select Sector SPDR",    "Sector-Energy",        "ETF",     "energy sector; since 1998"),
    "XLF":    ("Financial Select Sector SPDR", "Sector-Financials",    "ETF",     "financials; since 1998"),
    "XLK":    ("Technology Select Sector SPDR","Sector-Technology",    "ETF",     "technology; since 1998"),
    "XLV":    ("Health Care Select Sector SPDR","Sector-Healthcare",   "ETF",     "healthcare; since 1998"),
    "XLY":    ("Consumer Discretionary SPDR",  "Sector-Cons Disc",     "ETF",     "consumer discretionary; since 1998"),
    "XLP":    ("Consumer Staples Select SPDR","Sector-Cons Staples",  "ETF",     "consumer staples; since 1998"),
    "XLI":    ("Industrial Select Sector SPDR","Sector-Industrials",  "ETF",     "industrials; since 1998"),
    "XLB":    ("Materials Select Sector SPDR", "Sector-Materials",    "ETF",     "materials; since 1998"),
    "XLU":    ("Utilities Select Sector SPDR", "Sector-Utilities",    "ETF",     "utilities; since 1998"),
    "XLRE":   ("Real Estate Select Sector SPDR","Sector-Real Estate", "ETF",     "real estate sector; since 2015"),
    "XLC":    ("Communication Services SPDR",  "Sector-Comm Services","ETF",     "comm services; since 2018"),
    # ---- Alternatives / risk ----
    "^VIX":   ("CBOE Volatility Index",        "Volatility",           "INDEX",   "VIX level; since 1990"),
}

# ---------------------------------------------------------------------------
# 2. INDIVIDUAL STOCK UNIVERSE  (large caps across GICS sectors)
#    Sector labels are GICS sectors. These get grouped into 'asset class = Equity'
#    and also aggregated by sector.
# ---------------------------------------------------------------------------
STOCK_SECTORS = {
    "Technology":          ["AAPL","MSFT","NVDA","AVGO","ORCL","ADBE","CRM","INTC","AMD","CSCO","QCOM","TXN","IBM","NOW","INTU"],
    "Communication Srv":   ["GOOGL","META","VZ","TMUS","CMCSA","T"],
    "Consumer Discretionary":["AMZN","TSLA","HD","MCD","NKE","SBUX","LOW","BKNG","F","GM"],
    "Consumer Staples":    ["WMT","KO","PEP","PG","COST","MDLZ","CL","TGT"],
    "Healthcare":          ["JNJ","UNH","LLY","PFE","ABBV","MRK","TMO","ABT","DHR","BMY"],
    "Financials":          ["JPM","BAC","WFC","GS","MS","BLK","V","MA","AXP","SCHW","CB"],
    "Industrials":         ["BA","CAT","GE","HON","UPS","UNP","RTX","DE","LMT"],
    "Energy":              ["XOM","CVX","COP","SLB","EOG","PSX","MPC"],
    "Materials":           ["LIN","APD","NEM","FCX","DOW"],
    "Utilities":           ["NEE","DUK","SO","AEP","EXC"],
    "Real Estate":         ["PLD","AMT","CCI","EQIX","SPG","PSA"],
}

STOCKS = {}
for sector, tickers in STOCK_SECTORS.items():
    for t in tickers:
        STOCKS[t] = (f"{t} common stock", "Equity (single stock)", sector)

ALL_TICKERS = {**ASSET_TICKERS, **STOCKS}

# ---------------------------------------------------------------------------
# 3. DOWNLOAD  monthly history (period='max', interval='1mo')
# ---------------------------------------------------------------------------
def download_all(tickers: list[str]) -> pd.DataFrame:
    """Download monthly adjusted close for all tickers. Returns wide DataFrame
    indexed by month-end date with one column per ticker (adjusted close)."""
    print(f"\nDownloading {len(tickers)} tickers (period=max, interval=1mo) ...", flush=True)
    # yfinance download: group_by='column' gives MultiIndex (field, ticker)
    data = yf.download(
        tickers=tickers,
        period="max",
        interval="1mo",
        auto_adjust=True,     # Close == total-return adjusted close
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
        ignore_tz=True,
    )
    if data.empty:
        raise SystemExit("yf.download returned empty data")
    # Extract the 'Close' field
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        close = data.to_frame(name=tickers[0]) if data.ndim == 1 else data.copy()
    close.index = pd.to_datetime(close.index)
    # normalize index to month-end
    close.index = close.index.to_period("M").to_timestamp("M")
    return close.sort_index()

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
ac_groups = {}
for ticker, meta in ALL_TICKERS.items():
    name, asset_class, sector = meta[0], meta[1], meta[2]
    if ticker not in returns.columns:
        continue
    if asset_class.startswith("Sector-") or asset_class == "Equity (single stock)":
        continue  # single stocks + sector ETFs handled separately
    ac_groups.setdefault(asset_class, []).append(ticker)

ac_wide = pd.DataFrame(index=returns.index)
for ac, tks in ac_groups.items():
    sub = returns[tks]
    ac_wide[ac] = sub.mean(axis=1, skipna=True)
ac_wide = ac_wide.dropna(how="all").sort_index()
ac_wide.to_csv(os.path.join(OUT, "monthly_returns_by_asset_class.csv"))
print("Wrote monthly_returns_by_asset_class.csv shape=", ac_wide.shape)

# Sector level (from sector ETFs + individual stocks)
sec_groups = {}
for ticker, meta in ALL_TICKERS.items():
    name, asset_class, sector = meta[0], meta[1], meta[2]
    if ticker not in returns.columns:
        continue
    sec = sector
    if not sec:
        continue
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
cd /home/buntu/Stock_Price
.venv/bin/python pull_returns.py
```
"""
with open(os.path.join(OUT,"README.md"),"w") as f:
    f.write(readme)
print("Wrote README.md")

print("\n=== DONE ===")
print("Overall:", _fmt(prices.index.min()), "->", _fmt(prices.index.max()), f"({len(prices)} months)")
print("Output dir:", OUT)
