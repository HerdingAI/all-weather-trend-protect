# Coverage

How much data we have, how far back, and where the gaps are. All figures as of
2026-07-17.

## Top-level coverage

| Layer | Series with data | Date range | Periods | Data cells (non-NaN) |
|---|---|---|---|---|
| Daily prices | 341 / 342 | 1927-12-30 → 2026-07-17 | 24,753 trading days | 2,715,796 |
| Daily returns (long) | 341 | (same, minus 1st day each) | 2,714,743 rows | — |
| Monthly prices | 336 / 342 | 1962-01-31 → 2026-07-31 | 775 month-ends | — |
| Monthly returns (long) | 336 | 1962-02-28 → 2026-07-31 | 118,024 rows | — |
| Asset-class composite | 18 classes | 1973-06-30 → 2026-07-31 | 638 months | — |
| Sector composite | 17 groups | 1962-02-28 → 2026-07-31 | 774 months | — |

The daily layer reaches **1927** because `^GSPC` has daily history back to 1927-12-30.
The monthly layer starts **1962** because that is where Yahoo's monthly history for
the oldest stocks (GE, IBM, HON, etc.) begins. (Daily and monthly pulls are separate
`yf.download` calls; Yahoo exposes different start dates per interval.)

## Per-ticker coverage (daily)

- `n_trading_days`: min **558** (recent listings) · median **~6,911** · max **24,750**
  (`^GSPC`).
- `first_date`: 1928-01-03 (`^GSPC`) → 2024-01-12 (newest listings).
- `last_date`: 2022-06-17 → 2026-07-17. A handful of tickers end *before* the present
  (delisted / merged); most run to today.

### Longest daily histories
| Ticker | Name | Start | End | Trading days |
|---|---|---|---|---|
| ^GSPC | S&P 500 Index | 1928-01-03 | 2026-07-17 | 24,750 |
| IBM | IBM common stock | 1962-01-03 | 2026-07-17 | 16,241 |
| AEP, HON, XOM, DIS, GE, JNJ, BA | large caps | 1962-01-03 | 2026-07-17 | 16,241 |
| LMT | Lockheed Martin | 1962-01-03 | 2026-07-17 | 16,239 |

## Per-ticker coverage (monthly)

### Longest monthly histories
| Ticker | Name | Start | End | Months |
|---|---|---|---|---|
| GE / IBM / HON | large caps | 1962-02 | 2026-07 | 774 |
| WMT | Walmart | 1972-09 | 2026-07 | 647 |
| SPGI | S&P Global | 1973-03 | 2026-07 | 641 |
| EXC | Exelon | 1973-06 | 2026-07 | 638 |
| FDX | FedEx | 1978-05 | 2026-07 | 579 |
| DHR | Danaher | 1979-01 | 2026-07 | 571 |
| CMCSA | Comcast LILA | 1980-04 | 2026-07 | 556 |
| T | AT&T | 1983-12 | 2026-07 | 512 |

## Per-asset-class coverage (monthly)

| Asset class | First month | Months | Ann return % | Ann vol % |
|---|---|---|---|---|
| US Equity | 1973-06 | 638 | 10.30 | 15.29 |
| World Equity | 1973-06 | 638 | 10.23 | 20.05 |
| Gold/Precious Metals | 1978-02 | 582 | 13.34 | 34.38 |
| US Corporate Bonds | 1980-02 | 558 | 6.93 | 6.08 |
| US Municipal Bonds | 1980-02 | 558 | 4.70 | 4.47 |
| International Equity | 1983-06 | 518 | 8.08 | 17.47 |
| US Treasuries | 1986-06 | 482 | 5.12 | 6.70 |
| US Bonds | 1987-01 | 475 | 5.02 | 4.19 |
| US REIT | 1996-06 | 362 | 10.39 | 19.51 |
| Commodities | 2002-08 | 288 | 5.14 | 21.78 |
| Gold | 2004-12 | 260 | 11.24 | 17.17 |
| Silver | 2006-05 | 243 | 11.57 | 32.56 |
| Currency | 2007-04 | 232 | 2.00 | 7.72 |
| Preferred Stock | 2007-04 | 232 | 4.83 | 15.51 |
| EM Bonds | 2008-01 | 223 | 5.16 | 11.42 |
| International Bonds | 2009-02 | 210 | 2.06 | 6.19 |
| Digital Assets | 2015-06 | 134 | 88.59 | 115.08 |
| Money Market | 2023-10 | 30 | 0.00 | 0.00 |

> **Rebuilt 2026-08-01** by `build_aggregates.py --extended`. Two changes from the
> figures published earlier:
>
> 1. **Yield levels are no longer averaged in as returns.** `US Treasuries` was
>    2.24% / 5.43% starting 1985-02; that series was contaminated by `^TNX/^FVX/^TYX`
>    and correlates −0.51 with the corrected one. It now starts **1986-06**, the
>    inception of the first real total-return Treasury fund in the dataset (`VUSTX`).
>    The **Volatility (^VIX)** row is gone entirely — a volatility index is a level,
>    not a holdable return stream, so the sleeve no longer exists.
> 2. **History extends backwards**, by compounding the daily archive rather than
>    relying on Yahoo's monthly interval (which begins ~1985 for these instruments).
>    Equity reaches 1973, gold/PM 1978, corporates and munis 1980 — bringing the
>    Volcker shock and the 1980-82 bond bear into the sample.
>
> Start dates now differ sharply per sleeve, so a portfolio's usable window is set by
> its *latest*-starting sleeve. See `output/coverage_asset_class_extended.csv` for
> per-sleeve constituent counts over time.

## Universe composition (n = 342)

**By instrument kind (`sector`):**
| Kind | Count |
|---|---|
| MUTUALFUND | 115 |
| ETF | 87 |
| Individual stocks (GICS-tagged) | 128 |
| INDEX | 5 |
| YIELD | 3 |
| MONEYMARKET | 3 |
| STOCK (catch-all, `ASA`) | 1 |

**By asset class (top, n=342):**
`Equity (single stock)` 128 · `US Equity` 73 · `International Equity` 26 ·
`US Treasuries` 19 · `US Bonds` 18 · `US Corporate Bonds` 12 · `US Municipal Bonds` 7
· `International Bonds` 7 · `Commodities` 5 · `US REIT` 4 · `World Equity` 4 · plus
`Sector-*` sub-classes and singletons (Gold 2, Silver 1, Digital Assets 3, Money Market
3, Currency 1, Preferred Stock 1, Volatility 1, Gold/Precious Metals 3, EM Bonds 1).

**Individual stocks by GICS sector (128):**
Technology 19 · Financials 17 · Industrials 15 · Healthcare 14 · Consumer Discretionary
12 · Consumer Staples 11 · Energy 10 · Communication Srv 8 · Real Estate 8 · Materials
7 · Utilities 7.

## Tickers without full coverage

### 6 monthly-empty tickers (`present=False`)
`PADMX, PAGPX, PIGLX, AUBAX, LOMMX, SPAXX` — Yahoo returns no monthly history via
`period=max` for these. **5 of 6 still have daily data** (`SPAXX` is empty both ways —
money market, only 1d/5d yields).

### 24 audited-and-excluded tickers (not in any output)
Delisted / not on Yahoo: `CMR, FPIDX, KBONX, PGBDX, PGLIX, PINVX, VAB, VCE, VCN,
VDAIX, VDMIX, VEE, VFSVX, VFTSX, VFV, VFWIX, VGV, VHDYX, VIU, VMMXX, VSP, VTGMX,
VTWSX, VXC`. These came from the user-supplied 171-ticker audit list; they were
verified absent and intentionally left out of the universe.

## Gap profile (from integrity audit)

- **Internal NaN: 1,106 cells** across the daily matrix, but 99% concentrated:
  - `VMRXX`, `VUSXX`: 227 each — money market funds report NAV irregularly.
  - `^TNX`, `^FVX`, `^TYX`: 122 / 122 / 77 — yield levels, sparse.
  - Remaining ~330 cells: 1–2 isolated NaN across 330 tickers (normal Yahoo hiccups).
- **No structural gaps** in equity/ETF/stock series beyond these expected cases.
- **No truncation clusters** — the `period=max` choice means no rate-limit-induced
  shared-start-date artifacts (check B4 PASS).