# Data Dictionary

Field-by-field reference for every artifact in `output/`. Each entry gives:
**purpose · shape · storage · column dictionary (name · type · meaning · example) ·
sample · relationships**. File sizes are as of 2026-07-17.

Conventions used below:
- **Wide** = one row per date, one column per ticker/asset-class (a price/return matrix).
- **Long** = one row per (date, ticker) observation; the tidy/normalized form.
- **Adjusted close** = Yahoo *auto-adjusted* close = split- and dividend-adjusted = a
  **total-return** price series for ETFs/stocks/mutual funds.
- **Month-end timestamp** = the last calendar day of the month (e.g. `2026-07-31`),
  even if the market closed earlier; the value is the last *trading* day's close.
- All percentages in coverage files are stored as **percent** (e.g. `10.85` = 10.85%).
  All returns in the return panels are stored as **fractions** (e.g. `0.0129` = 1.29%).

---

## 1. `daily_prices.parquet` (and gitignored `daily_prices.csv`)

| | |
|---|---|
| Purpose | Primary daily price matrix — adjusted close for all 342 tickers. |
| Shape | **24,753 rows × 342 columns** |
| Storage | Parquet (zstd), 11.9 MB. CSV mirror 31 MB (gitignored). |
| Index | `DatetimeIndex` (UTC-naive), daily frequency, **1927-12-30 → 2026-07-17**. |
| Format | **Wide**. One column per ticker; `float64`. |

**Columns:** the first 342 tickers in `universe.csv` order (see universe.csv for names).
Each cell is the auto-adjusted close for that ticker on that trading day, or `NaN`
before the ticker's inception / on days it did not trade.

**Sample:**
```
Ticker      AGG   BITO   BND   DBC   ...   XOM
Date
1927-12-30   NaN    NaN   NaN   NaN   ...    NaN
...
2026-07-17  98.20   8.69  72.86 28.98  ...  147.36
```

**Notes**
- The index is the *union* of all tickers' trading days; early rows are entirely `NaN`
  except the longest series (`^GSPC` begins 1927-12-30).
- This is the **cache of record** for the daily layer — `pull_daily.py` reads it if
  present, otherwise downloads and writes it. Delete to force a refresh.
- `SPAXX` is an all-`NaN` column (money market, only reports 1d/5d yields — not kept).

---

## 2. `daily_returns_by_ticker.parquet` (and gitignored `.csv`)

| | |
|---|---|
| Purpose | Tidy long panel of daily simple returns with full metadata. |
| Shape | **2,714,743 rows × 6 columns** |
| Storage | Parquet, 23.7 MB. CSV mirror 229 MB (gitignored). |
| Format | **Long** (one row per ticker per trading day). |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `date` | datetime64 | Trading day | `2006-02-07` |
| `ticker` | string | Yahoo symbol | `DBC` |
| `name` | string | Instrument name | `Invesco DB Commodity Index` |
| `asset_class` | string | Asset class (see §Taxonomy) | `Commodities` |
| `sector` | string | Instrument kind **or** GICS sector (see §Taxonomy) | `ETF` |
| `daily_return` | float64 | Simple day-over-day return = `close[t]/close[t-1] − 1` (fraction) | `-0.028926` |

**Sample:**
```
        date ticker                        name asset_class sector daily_return
0 2006-02-07    DBC  Invesco DB Commodity Index  Commodities    ETF    -0.028926
1 2006-02-08    DBC  Invesco DB Commodity Index  Commodities    ETF    -0.004255
```

**Notes**
- 341 tickers (all with daily data; `SPAXX` excluded).
- First row per ticker is `NaN` (no prior close) and **dropped** — the panel starts at
  each ticker's second trading day.
- `daily_return` is `pct_change()` of the adjusted close — **total return** for
  ETFs/stocks/funds (dividends reinvested via auto-adjust), price return for indices.

---

## 3. `universe.csv`

| | |
|---|---|
| Purpose | Master ticker registry + monthly coverage flag. The catalog of *what* was pulled. |
| Shape | **342 rows × 8 columns** |
| Format | Long (one row per ticker). |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `ticker` | string | Yahoo symbol | `SPY` |
| `name` | string | Instrument name | `SPDR S&P 500 ETF` |
| `asset_class` | string | Asset class / `Equity (single stock)` / `Sector-*` | `US Equity` |
| `sector` | string | Instrument kind **or** GICS sector | `ETF` |
| `first_month` | string (YYYY-MM-DD) | First month-end with non-null monthly close | `1993-01-31` |
| `last_month` | string | Last month-end with data | `2026-07-31` |
| `n_months` | int64 | Count of non-null monthly observations | `403` |
| `present` | bool | Has any monthly data? (`False` for the 6 monthly-empty tickers) | `True` |

**Notes**
- `present=False` for exactly 6 tickers: `PADMX, PAGPX, PIGLX, AUBAX, LOMMX, SPAXX`
  (Yahoo returns no monthly history for these via `period=max`; 5 of them *do* have
  daily data — a Yahoo quirk; `SPAXX` is empty both ways).
- The 24 audited-and-excluded (not-on-Yahoo) tickers are **not** in this file at all.

---

## 4. `coverage_summary.csv` (monthly, per-ticker)

| | |
|---|---|
| Purpose | Per-ticker monthly coverage + annualized stats. |
| Shape | **336 rows × 12 columns** (tickers with monthly data only) |
| Format | Long. |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `ticker` | string | Yahoo symbol | `DBC` |
| `name` | string | Instrument name | `Invesco DB Commodity Index` |
| `asset_class` | string | Asset class | `Commodities` |
| `sector` | string | Kind / GICS sector | `ETF` |
| `first_month` | string | First month-end | `2006-03-31` |
| `last_month` | string | Last month-end | `2026-07-31` |
| `n_months` | int64 | Non-null months | `245` |
| `ann_return_pct` | float64 | Annualized return, % (CAGR from monthly compounding) | `4.002659` |
| `ann_vol_pct` | float64 | Annualized volatility, % (monthly std × √12) | `18.749508` |
| `min_month_pct` | float64 | Worst single-month return, % | `-25.081130` |
| `max_month_pct` | float64 | Best single-month return, % | `16.266259` |
| `pct_positive_months` | float64 | Share of months with return > 0, % | `51.836735` |

---

## 5. `daily_coverage_summary.csv` (daily, per-ticker)

| | |
|---|---|
| Purpose | Per-ticker daily coverage + annualized stats. |
| Shape | **341 rows × 12 columns** (tickers with daily data; `SPAXX` excluded) |
| Format | Long. |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `ticker` | string | Yahoo symbol | `DBC` |
| `name` | string | Instrument name | `Invesco DB Commodity Index` |
| `asset_class` | string | Asset class | `Commodities` |
| `sector` | string | Kind / GICS sector | `ETF` |
| `first_date` | string | First trading day | `2006-02-07` |
| `last_date` | string | Last trading day | `2026-07-17` |
| `n_trading_days` | int64 | Non-null daily observations | `5141` |
| `ann_return_pct` | float64 | Annualized return, % (252-day CAGR) | `3.970948` |
| `ann_vol_pct` | float64 | Annualized volatility, % (daily std × √252) | `19.289704` |
| `min_daily_pct` | float64 | Worst single-day return, % | `-7.944429` |
| `max_daily_pct` | float64 | Best single-day return, % | `6.874407` |
| `pct_positive_days` | float64 | Share of up days, % | `51.604746` |

**Coverage spread:** `n_trading_days` ranges 558 (newest listings) → 24,750 (`^GSPC`);
median ≈ 6,911. `first_date` 1928-01-03 → 2024-01-12; `last_date` 2022-06-17 →
2026-07-17 (a few delisted tickers end before the present).

---

## 6. `asset_class_summary.csv` (monthly, per-asset-class)

| | |
|---|---|
| Purpose | Asset-class-level coverage + annualized stats (equal-weighted across constituents). |
| Shape | **19 rows × 8 columns** |
| Format | Long (one row per asset class). |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `asset_class` | string | Asset class | `US Equity` |
| `first_month` | string | First month-end any constituent has data | `1985-02-28` |
| `last_month` | string | Last month-end | `2026-07-31` |
| `n_months` | int64 | Months in span | `498` |
| `ann_return_pct` | float64 | Equal-weighted annualized return, % | `10.856687` |
| `ann_vol_pct` | float64 | Equal-weighted annualized volatility, % | `15.153740` |
| `min_month_pct` | float64 | Worst month for the equal-weighted index, % | `-22.377860` |
| `max_month_pct` | float64 | Best month, % | `13.308724` |

**Notes**
- `Money Market` shows `0.000000` across all stats — its funds report a constant
  $1.00 NAV (yields are not captured in the price series).
- `Volatility` (`^VIX`) has extreme stats (ann vol ≈ 75%, max month +134.6%) —
  expected; VIX is a non-investable fear index, not a returnable asset.

---

## 7. `monthly_prices.csv`

| | |
|---|---|
| Purpose | Monthly adjusted-close matrix. |
| Shape | **775 rows × 337 columns** (`Date` + 336 tickers) |
| Format | **Wide**. Index = `Date` (month-end, parsed as datetime). 336 tickers = those with monthly data. |
| Range | **1962-01-31 → 2026-07-31** (775 month-ends). |

**Columns:** `Date` then one `float64` column per ticker (order = `universe.csv` order,
filtered to the 336 present tickers).

**Notes**
- Values are month-end adjusted close = last trading day's close of that month.
- Early rows are mostly `NaN` (most tickers start decades after 1962).
- `^TNX/^FVX/^TYX` columns hold **yield levels**, not prices — kept here for
  continuity but their pct_change is *not* a return (see nuances).

---

## 8. `monthly_returns_by_ticker.csv`

| | |
|---|---|
| Purpose | Tidy long panel of monthly returns with metadata. |
| Shape | **118,024 rows × 6 columns** (336 tickers) |
| Format | **Long**. |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `date` | datetime64 | Month-end timestamp | `2006-03-31` |
| `ticker` | string | Yahoo symbol | `DBC` |
| `name` | string | Instrument name | `Invesco DB Commodity Index` |
| `asset_class` | string | Asset class | `Commodities` |
| `sector` | string | Kind / GICS sector | `ETF` |
| `monthly_return` | float64 | Month-over-month return = `close[m]/close[m-1] − 1` (fraction) | `0.027909` |

---

## 9. `monthly_returns_by_asset_class.csv`

| | |
|---|---|
| Purpose | Wide matrix of equal-weighted monthly returns per asset class. |
| Shape | **638 rows × 19 columns** (`Date` + 18 asset classes) |
| Format | **Wide**. Range **1973-06-30 → 2026-07-31**. |
| Built by | `build_aggregates.py --extended` (not `pull_returns.py`) |

**Asset-class columns (18):** `US Equity, International Equity, US Bonds, US
Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Silver, US REIT,
Commodities, Digital Assets, EM Bonds, Currency, Preferred Stock,
Gold/Precious Metals, International Bonds, Money Market, World Equity`.

**Aggregation:** each month, the equal-weighted mean of constituent tickers' monthly
returns (using only tickers present that month). Cells are `NaN` where no constituent
has data that month. Excluded from the aggregates:

1. Individual stocks and sector ETFs, to avoid double-counting (they have their own
   sector files).
2. Series whose `pct_change` is not a return — the `YIELD` kind (`^TNX/^FVX/^TYX`),
   the price-only indices (`^GSPC/^DJI/^IXIC/^RUT`), and `^VIX`. Defined once in
   `pull_returns.py` §2b and applied by both the puller and the builder.

> **Changed 2026-08-01.** Was 498 × 20 spanning 1985-02 → 2026-07 with 19 classes.
> Two changes: exclusion (2) was documented but never implemented, which contaminated
> `US Treasuries` with yield levels (corr −0.51 vs corrected, −289 bps/yr) and removed
> the `Volatility` column entirely, since it was 100% `^VIX`. And history now extends
> back by compounding the daily archive, so the panel starts 1973-06 rather than
> 1985-02. Per-sleeve start dates vary widely — see `docs/coverage.md`.
>
> Companion file `coverage_asset_class_extended.csv` records each sleeve's start date
> and constituent count over time.

---

## 10. `monthly_returns_by_sector.csv`

| | |
|---|---|
| Purpose | Wide matrix of equal-weighted monthly returns per **sector**, mixing instrument kinds and GICS sectors. |
| Shape | **774 rows × 18 columns** (`Date` + 17 groupings) |
| Format | **Wide**. Range **1962-02-28 → 2026-07-31**. |

**Columns (17):** instrument kinds — `INDEX, ETF, YIELD, MUTUALFUND, STOCK,
MONEYMARKET`; plus 11 GICS sectors — `Technology, Communication Srv, Consumer
Discretionary, Consumer Staples, Healthcare, Financials, Industrials, Energy,
Materials, Utilities, Real Estate`.

**Aggregation:** equal-weighted mean across all tickers whose `sector` equals the
column label, for that month. The `STOCK` column is near-empty (only `ASA` is
tagged `STOCK`; the 128 individuals carry their GICS sector instead).

> **The GICS columns are individual stocks only — not "sector ETFs + stocks".**
> This grouping keys on `meta[2]`, which holds the *kind* for asset tickers and the
> GICS sector only for single stocks. Sector ETFs (`XLE`, `XLF`, …) carry their
> `Sector-*` label in `meta[1]`, so they land in the `ETF` column and never reach
> their own GICS column. That is also why instrument kinds appear here as if they
> were sectors. Pre-existing behaviour, documented rather than changed — the
> stocks-only view in `monthly_returns_by_sector_stocks_only.csv` is unaffected.

> **Shape changes on the next `pull_returns.py` run.** The return-series policy
> (methodology §4) now applies to this file too, so the `YIELD` and `INDEX` columns
> disappear — all three `YIELD` tickers and all five `INDEX` tickers are excluded,
> emptying both groups. Expect **15 groupings**, not 17. The committed file still
> has 17 because it predates the fix and the puller needs a network re-pull to
> regenerate; `build_aggregates.py` rebuilds only the asset-class file.

---

## 11. `monthly_returns_by_sector_stocks_only.csv`

| | |
|---|---|
| Purpose | Same as §10 but GICS sectors computed from **individual stocks only** (excludes sector ETFs). |
| Shape | **774 rows × 12 columns** (`Date` + 11 GICS sectors) |
| Format | **Wide**. Range **1962-02-28 → 2026-07-31**. |

Use this when you want the *pure single-stock* sector return without ETF overlap.

---

## 12. `integrity_report.csv`

| | |
|---|---|
| Purpose | Machine-readable audit result — one row per check. |
| Shape | **39 rows × 3 columns** |
| Format | Long. |

| Column | Type | Meaning | Example |
|---|---|---|---|
| `severity` | string | `PASS` / `WARN` / `FAIL` | `PASS` |
| `check` | string | Check ID + name (A1–F3) | `D1 panel return==price pct_change` |
| `detail` | string | Human-readable result / metrics | `0/20 sampled tickers mismatch` |

**Tally:** 27 PASS · 12 WARN · 0 FAIL. Full narrative triage in
[integrity_findings.md](../output/integrity_findings.md) and
[nuances_and_caveats.md](nuances_and_caveats.md).

---

## 13. `integrity_findings.md`

Narrative triage of the 12 warnings (which are real issues vs expected Yahoo behavior).
Not a data file — a human-readable companion to `integrity_report.csv`.

---

## 14. Supporting artifacts

| File | Purpose |
|---|---|
| `output/README.md` | Auto-generated monthly README (regenerated each `pull_returns.py` run). |
| `output/daily_README.md` | Auto-generated daily README (regenerated each `pull_daily.py` run). |
| `output/_yf_tz_cache/tkr-tz.db` | yfinance timezone cache (peewee SQLite); speeds re-pulls, safe to delete. |
| `handoff.md` | Session-continuity doc (repo root). |

---

## Taxonomy reference (`asset_class` / `sector`)

The `asset_class` and `sector` columns use a **two-layer scheme**:

- **`asset_class`** — the *what*: the economic exposure.
  - `Equity (single stock)` — the 128 individual stocks.
  - Thematic classes for funds/ETFs/indexes: `US Equity`, `International Equity`,
    `World Equity`, `US Bonds`, `US Treasuries`, `US Corporate Bonds`,
    `US Municipal Bonds`, `International Bonds`, `EM Bonds`, `Gold`, `Silver`,
    `Gold/Precious Metals`, `US REIT`, `Commodities`, `Digital Assets`, `Currency`,
    `Preferred Stock`, `Volatility`, `Money Market`.
  - `Sector-*` sub-classes for sector-specialist funds (e.g. `Sector-Energy`,
    `Sector-Healthcare`, `Sector-Semiconductors`, `Sector-Clean Energy`,
    `Sector-Homebuilders`, `Sector-Biotech`, …).

- **`sector`** — the *how* (instrument kind) **or** the GICS sector for stocks.
  - Instrument kinds: `ETF`, `MUTUALFUND`, `INDEX`, `YIELD`, `MONEYMARKET`, `STOCK`.
  - GICS sector (only for the 128 individual stocks): `Technology`,
    `Communication Srv`, `Consumer Discretionary`, `Consumer Staples`, `Healthcare`,
    `Financials`, `Industrials`, `Energy`, `Materials`, `Utilities`, `Real Estate`.
  - `STOCK` is a catch-all used for a single ticker (`ASA`); individuals otherwise
    carry their GICS sector in this column.

**Counts (universe, n=342):** ETF 87 · MUTUALFUND 115 · INDEX 5 · YIELD 3 ·
MONEYMARKET 3 · STOCK 1 · GICS-tagged stocks 128.

---

## File relationships

```
universe.csv  ────────────► catalog of all 342 tickers (metadata + present flag)
   │
   ├─► monthly_prices.csv ──pct_change──► monthly_returns_by_ticker.csv
   │         │                                   │
   │         │                                   ├─ group by asset_class ─► monthly_returns_by_asset_class.csv
   │         │                                   └─ group by sector ──────► monthly_returns_by_sector.csv
   │         │                                                              └─ stocks only ─► monthly_returns_by_sector_stocks_only.csv
   │         └─ per-ticker stats ─► coverage_summary.csv
   │                                   └─ group by asset_class ─► asset_class_summary.csv
   │
   └─► daily_prices.parquet ──pct_change──► daily_returns_by_ticker.parquet
              └─ per-ticker stats ─► daily_coverage_summary.csv

audit_integrity.py reads (1,2,3,7,8,9,10) and re-derives returns to verify ─► integrity_report.csv
```

The daily and monthly layers are **independent pulls** (separate `yf.download` calls
at different intervals) but share the **same universe**. The integrity audit confirms
they reconcile: stored monthly close == daily-resampled monthly close (check B5).