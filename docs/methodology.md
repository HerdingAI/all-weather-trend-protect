# Methodology

How every value in the dataset is derived, from Yahoo API call to final file.

## 1. Data acquisition

| Parameter | Monthly | Daily |
|---|---|---|
| Library | `yfinance` v1.5.1 | same |
| Call | `yf.download(...)` | `yf.download(...)` |
| `interval` | `1mo` | `1d` |
| `period` | `max` | `max` |
| `auto_adjust` | `True` | `True` |
| `actions` | `False` | `False` |
| `group_by` | `column` | `column` |
| `threads` | `True` | `True` |
| `ignore_tz` | `True` | `True` |
| `timeout` | 60 s | 60 s |

`period="max"` is **critical**: using a shorter window (e.g. `5y`) silently truncates
old mutual-fund history, making a fund that inceptioned in 1984 appear to start in
2021. `max` returns the true full history back to inception.

### Batching & rate-limit handling
All downloads go through `_download_batched()` (defined in `pull_returns.py`, imported
by `pull_daily.py`):
- **Batch size = 50 tickers** per `yf.download` call.
- **3 s sleep** between batches.
- **`yf.config.network.retries = 5`** — exponential backoff 1 s → 2 s → 4 s → 8 s → 16 s.
- **60 s per-request timeout.**
- **TZ cache** (`yf.set_tz_cache_location(output/_yf_tz_cache)`) so Yahoo's per-ticker
  timezone lookup is cached across runs instead of re-fetched (a common rate-limit
  trigger).

Per-batch frames are concatenated column-wise, deduplicated on index (`keep="first"`),
and sorted.

## 2. Price adjustment (what "adjusted close" means)

`auto_adjust=True` makes Yahoo return a single **Close** series that is:
- **Split-adjusted** — all historical prices scaled for stock splits so the series is
  continuous.
- **Dividend-adjusted** — dividends are reinvested into the price.

For ETFs, stocks, and mutual funds this makes Close a **total-return** price: the
pct_change of this series *is* the total return (price change + reinvested dividends).

**Exceptions (price-only, dividends NOT captured):**
- Broad indices `^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX` — Yahoo does not provide total-return
  index levels for these, so their returns understate total return by the dividend
  yield. Verified by audit D4: SPY (total-return) grew 30.8× vs `^GSPC` (price-only)
  17.0× over 1993→2026.
- `^TNX, ^FVX, ^TYX` — these are **yield levels** (10y/5y/30y Treasury yields), not
  prices. They are kept in the price matrices for continuity, but their pct_change is
  *not a return* and they are excluded from asset-class/sector return aggregations
  (see §4 for the exclusion rule and the bug that preceded it).
- Money market funds (`VMRXX, VUSXX`, etc.) — report a ~constant $1.00 NAV; their
  "return" is ~0 because the *yield* is paid as a separate dividend line that
  `actions=False` does not pull. Money Market therefore shows 0% everywhere.

## 3. Return computation

- **Daily return** = `close[t] / close[t-1] − 1` (simple, not log). Computed via
  `pct_change()` on the wide price matrix, then melted to long form. The first
  observation per ticker (no prior close) is `NaN` and dropped.
- **Monthly return** = month-end adjusted close pct_change, `close[m] / close[m-1] − 1`.
  Monthly timestamps are normalized to the month-end (last calendar day of the month).
- Both are stored as **fractions** (0.01 = 1%), not percentages.

## 4. Aggregation

### Asset-class returns (`monthly_returns_by_asset_class.csv`)
Each month: **equal-weighted mean** of constituent tickers' monthly returns, using
only the tickers that have data that month.
- Constituents = tickers whose `asset_class` matches the column (thematic funds/ETFs/indexes).
- **Excluded from asset-class aggregates:**
  1. The 128 individual stocks and sector ETFs — to avoid double-counting (they are
     represented in the sector files instead).
  2. **Series whose pct_change is not a return** — the `YIELD` kind (`^TNX, ^FVX, ^TYX`),
     the price-only indices (`^GSPC, ^DJI, ^IXIC, ^RUT`), and `^VIX`. The rule lives in
     one place, `pull_returns.py` §2b (`NON_RETURN_KINDS` / `NON_RETURN_TICKERS` /
     `is_return_series`), and is applied by both the puller and `build_aggregates.py`.
- Result: a time-varying equal-weighted index per asset class; cells are `NaN` when no
  constituent exists that month. Coverage therefore *expands* as more tickers inception
  over time (e.g. Digital Assets starts 2015, Money Market 2023).

> **Corrected 2026-08-01 — exclusion (2) was documented here but never implemented.**
> Until then the aggregation excluded only stocks and sector ETFs, so yield levels were
> averaged into `US Treasuries` as if they were returns. Yields move opposite to bond
> prices, so this inverted the sleeve rather than merely adding noise:
>
> | `US Treasuries` | Ann return | Ann vol | First month | corr vs corrected |
> |---|---:|---:|---|---:|
> | As published (contaminated) | 2.24% | 5.43% | 1985-02 | −0.51 |
> | Corrected (funds only) | 5.13% | 6.70% | 1986-06 | — |
>
> The first month moves because no total-return Treasury fund exists in the data before
> `VUSTX` (1986-06): 1985-02 → 1986-05 had been **entirely** yield changes. `US Equity`
> was affected immaterially (corr 1.000, ~5 bps/yr — four price-only indices diluted
> among 71 funds). The `Volatility` sleeve was 100% `^VIX` and is therefore **gone** from
> the aggregates; it was already excluded by default downstream (`--include-volatility`),
> since a volatility index is not a holdable return stream.
>
> Every risk-parity report published before 2026-08-01 rests on the contaminated series.

### Sector returns (`monthly_returns_by_sector.csv`)
Equal-weighted mean across all tickers tagged with that `sector` value (instrument kind
or GICS sector). The GICS-sector columns combine **sector ETFs + individual stocks**.
A stocks-only variant (`monthly_returns_by_sector_stocks_only.csv`) drops the ETFs.

**Why equal-weight, not market-cap?** Yahoo's free feed does not provide reliable
historical shares-outstanding / market-cap for the universe, so cap-weighting across
mixed ETFs + mutual funds + indices is not well-defined here. Equal-weight is
transparent, reproducible, and the natural choice for a broad research panel. (Treat
the asset-class/sector series as *style composites*, not investable benchmarks.)

## 5. Annualized statistics (coverage files)

| Stat | Formula |
|---|---|
| `ann_return_pct` (monthly) | `(∏(1+r))^(12/n) − 1`, × 100 |
| `ann_vol_pct` (monthly) | `std(monthly_returns) × √12 × 100` |
| `ann_return_pct` (daily) | `(∏(1+r))^(252/n) − 1`, × 100 |
| `ann_vol_pct` (daily) | `std(daily_returns) × √252 × 100` |
| `min/max_*_pct` | extreme single-period return × 100 |
| `pct_positive_*` | share of periods with return > 0, × 100 |

- Trading-days-per-year = **252** (daily); months-per-year = **12** (monthly).
- Annualized return is the **geometric (CAGR)** form, compounded from the per-period
  returns — robust to varying history lengths across tickers.
- Annualized vol uses the sqrt-of-time scaling (assumes IID daily/monthly returns).

## 6. File naming convention

- `*_by_ticker` → long panel, one row per (period, ticker).
- `*_by_asset_class` / `*_by_sector` → wide aggregated matrix.
- `*_prices` → wide price matrix.
- `coverage_summary` / `asset_class_summary` → per-unit stats.
- `daily_*` → daily granularity; bare `monthly_*` → monthly.

## 7. Reproducibility & freshness

- **Deterministic given Yahoo's data**: same `yf.download(period=max)` calls return the
  same history (Yahoo occasionally revises splits/dividends, so a re-pull months later
  may shift a few adjusted-close values).
- **Daily caching**: `pull_daily.py` writes `daily_prices.parquet` and reuses it on
  subsequent runs. Delete the file to force a full re-download. The CSV mirrors are
  regenerated from the parquet each run.
- **Monthly is not cached** — `pull_returns.py` re-pulls every run. Re-running is the
  refresh mechanism.
- **Integrity audit is read-only** — `audit_integrity.py` never writes data, only
  `integrity_report.csv`.