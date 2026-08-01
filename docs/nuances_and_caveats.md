# Nuances & Caveats

Read this before trusting any edge case. The dataset is **correct** (the integrity
audit verifies the pipeline math) but Yahoo's free data carries inherent quirks that
no client-side fix can fully eliminate. Each is documented so you can decide whether it
matters for your analysis.

## Integrity verdict (summary)

`audit_integrity.py` → **0 FAIL · 27 PASS · 12 WARN**. The 12 warnings are triaged
below; **none indicate pipeline corruption**. The load-bearing correctness checks all
pass:

| Check | What it proves |
|---|---|
| D1 | Long-panel daily return == `close[t]/close[t-1]−1` (0/20 sampled mismatch) |
| D2 | Monthly return == month-end close ratio (0/20 mismatch) |
| B5 | Stored monthly close == daily-resampled monthly close (0/336 diverge) |
| D4 | SPY total-return (30.8×) > `^GSPC` price-only (17.0×) over 1993→2026 → dividends captured |
| A1-A5 | Indexes monotonic+unique; columns match universe; panel schema valid |
| F1 | All 24 not-on-Yahoo tickers confirmed absent (no junk data) |

Full machine-readable results: `output/integrity_report.csv`. Narrative triage:
`output/integrity_findings.md`.

---

## Nuance 1 — Total-return vs price-return

- **ETFs / stocks / mutual funds**: returns are **total returns** (dividends
  reinvested via `auto_adjust=True`).
- **Broad indices `^GSPC, ^DJI, ^IXIC, ^RUT, ^VIX`**: **price-only**. Yahoo has no
  total-return index level for these, so their returns understate total return by the
  dividend yield. Do not compare `^GSPC` cumulative growth to SPY without accounting
  for this (SPY should grow faster — and does: 30.8× vs 17.0×).
- **Implication**: for any long-horizon equity return comparison, prefer the ETF
  (`SPY, VTI, VOO`) over the index (`^GSPC`).

## Nuance 2 — Yield series are not prices

`^TNX` (10y), `^FVX` (5y), `^TYX` (30y) are **Treasury yield levels**, not tradeable
prices. They are kept in `monthly_prices.csv` / `daily_prices.parquet` for continuity,
but:
- Their `pct_change` is **not a return** (a yield doubling is not a 100% gain).
- They are **excluded** from asset-class and sector return aggregations
  (`pull_returns.py` §2b) — but see the warning below: this was documented long
  before it was true.
- They have sparse daily data (122 / 122 / 77 internal NaN) because Yahoo does not
  report a yield every trading day in its history.

Using them as a signal is fine and intended: `risk_parity_seasons.py` reads the 12-month
change in the `^TNX` *level* as its inflation-regime proxy. It is only *return
aggregation* that must exclude them.

If you want Treasury *return* series, use the bond ETFs / Vanguard treasury funds
instead (`VGIT, VGLT, VGSH, VFITX, VFIUX, VSBSX, VUSTX`, etc.).

> ⚠️ **This exclusion was fiction until 2026-08-01.** The line above claimed it for a
> long time; the code never did it. Yields were averaged into `US Treasuries`, and
> because yields move opposite to bond prices the sleeve did not merely get noisier —
> it *inverted*. The published series correlates **−0.51** with the corrected one and
> understates return by **289 bps/yr** (2.24% vs 5.13%). Its first 16 months
> (1985-02 → 1986-05) were pure artifact: no total-return Treasury fund exists in the
> data before `VUSTX` (1986-06), so the sleeve was 100% yield changes over that span.
>
> Consequences worth knowing when reading older analysis:
> - Any risk-parity result published before 2026-08-01 rests on the contaminated sleeve.
>   The canonical winner allocated 20% to it — the cap binding exactly, which
>   `docs/peer-review.md` §2a read as "the cap, not the optimizer, was allocating."
>   An artificially low-volatility bond series is a sufficient explanation for that.
> - The corrected sleeve starts 1986-06, so it no longer spans a window beginning 1985.
>   That is why the `long1986` seasons preset exists.

## Nuance 3 — Money market funds read as 0% return

`VMRXX, VUSXX, SPAXX` (and `SPAXX`'s siblings) report a **~constant $1.00 NAV**. The
*yield* is distributed as a separate dividend line that `actions=False` does not pull,
so the price-derived return is **~0%**. The `Money Market` asset class therefore shows
`0.00` for all stats. Additionally these report NAV irregularly (227 internal NaN each
for VMRXX/VUSXX). This is expected; money market *yield* is not recoverable from this
dataset.

## Nuance 4 — Mutual-fund share-class divergence on cap-gains days

Investor vs Admiral share classes of the same Vanguard fund (e.g. `VGHCX`↔`VGHAX`,
`VWEHX`↔`VWEAX`) should track near-identically. They do (correlation ≥ 0.99), **except
on December capital-gains-distribution ex-dates**, where Yahoo records/adjusts the
distribution inconsistently across share classes — producing a one-day return
divergence of several percent (worst: VGHCX↔VGHAX on 2002-12-13, VGHAX −7.52% while
VGHCX −0.78%).

- The price **levels** stay in the correct ratio (e.g. VGHCX/VGHAX ≈ 2.40 stable), so
  the series track in level; only single-day returns diverge on distribution days.
- This is a **Yahoo source-data artifact**, not a pipeline error — our returns
  faithfully reflect the prices Yahoo returned (D1/D2 confirm).
- Index-fund share classes with *no* cap-gains distributions (e.g. `VFINX`↔`VFIAX`,
  `VTSMX`↔`VTSAX`) do **not** show this — confirming the cause.

**Implication**: if you compare share-class returns day-by-day, expect a handful of
December divergences on actively managed funds. Aggregate over monthly+ horizons and
they vanish.

## Nuance 5 — Two ancient unadjusted splits (MCD, 1968-69)

`MCD` shows −50.7% on 1968-05-21 and −50.1% on 1969-06-13. These are **2:1 stock
splits from the 1960s that Yahoo's `auto_adjust` did not repair** that far back (the
MCD series from 1980 onward is clean). 2 cells, 58 years ago.

- Not patched: manually re-adjusting 1960s split data risks introducing errors for
  negligible gain.
- **Implication**: ignore MCD daily returns before ~1980, or drop the 2 cells. Any
  analysis starting 1980+ is unaffected.

## Nuance 6 — Extreme daily returns that are REAL

Several tickers have single-day moves > |50%|. These are genuine market history, not
errors:
- `AAPL` −51.9% on 2000-09-29 (Apple's Q4 earnings warning — a famous crash).
- `AIG` −60.8% on 2008-09-15 (Lehman day) and +60%/+63% days in 2009 (crisis rebound
  around its 1:20 reverse split).
- `WMB` −61% / +101% in July 2002 (Williams Companies energy-trading collapse near
  bankruptcy).
- `^VIX` 9 days > |50%|, incl. **+115.6% on 2018-02-05 (Volmageddon)** and
  **+64.9% on 2024-08-05** (the yen-carry unwind).

Do not filter these out — they are the events you most likely want to study.

## Nuance 7 — Period truncation artifact (and why we avoid it)

Using `period="5y"` (or any fixed window) instead of `period="max"` silently truncates
history: an old mutual fund that inceptioned in 1984 will appear to start 2021-07-19
because that is 5 years before the pull date. This was a real trap during development.
We use **`period="max"` everywhere**, which the audit confirms produces no truncation
clusters (check B4). If you ever re-pull with a different `period`, expect every
long-history ticker to be cut to that window.

## Nuance 8 — Equal-weighting, not market-cap weighting

Asset-class and sector composites are **equal-weighted** across constituents (Yahoo's
free feed lacks reliable historical market-cap/shares-outstanding for a mixed
ETF+mutual-fund+index universe). Consequences:
- The composites are **style composites**, not investable benchmarks.
- A small illiquid ETF contributes as much as a giant one.
- Sector composites mix sector ETFs with individual stocks (use
  `monthly_returns_by_sector_stocks_only.csv` for pure single-stock sector returns).

## Nuance 9 — Daily vs monthly are independent pulls

Daily and monthly data come from **separate `yf.download` calls** at different
intervals. Yahoo exposes different start dates per interval (daily reaches 1927 for
`^GSPC`; monthly reaches 1962 for old stocks). The audit (B5) confirms the two layers
reconcile: the stored monthly close equals the daily-resampled monthly close for all
336 tickers. So monthly is *derivable* from daily, but they are stored independently
and were pulled independently — small rounding/last-trading-day differences are
possible in principle but not observed.

## Nuance 10 — 6 tickers have daily but not monthly data

`PADMX, PAGPX, PIGLX, AUBAX, LOMMX` have daily history but Yahoo returns *no* monthly
history for them via `period=max` (a Yahoo quirk, not a pipeline bug). `SPAXX` is empty
both ways. These 6 are flagged `present=False` in `universe.csv` and excluded from all
monthly outputs. Their daily data is present in `daily_prices.parquet`.

## Nuance 11 — Index timestamp = month-end calendar day

Monthly rows are timestamped to the **last calendar day of the month**
(e.g. `2026-07-31`) even when the market's last trading day was earlier (e.g. a Friday
the 29th). The *value* is that last trading day's close. When joining monthly to
external data on date, align to month-end, not to the actual trading day.

## Nuance 12 — Re-pulls may shift slightly

Yahoo occasionally revises split/dividend metadata, so an adjusted-close value pulled
today may differ slightly from one pulled months ago. This is normal for free feeds.
Pin a snapshot (the committed parquet) if you need bit-for-bit reproducibility.

---

## What is NOT fixable from this stack

To eliminate the residual quirks (cap-gains share-class handling, 1960s split repair,
money-market/yield reporting frequency, index total-return) you would need a **paid
data provider** — e.g. Bloomberg, CRSP, Morningstar Direct, or ICE/BAML. The current
dataset is the most complete and correct version achievable from Yahoo Finance free
data, and its quirks are fully documented above.