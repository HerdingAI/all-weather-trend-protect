# Scripts Reference

Three Python scripts run the system: a monthly puller, a daily puller, and an integrity
auditor. All run from the repo root with the project venv.

## Environment

| | |
|---|---|
| Python | 3.x (project venv at `.venv/`) |
| Deps | `requirements.txt`: `yfinance>=1.5`, `pandas>=3.0`, `numpy>=2.0`, `pyarrow>=15`, `requests>=2.31` |
| Install | `pip install -r requirements.txt` |
| Run | `.venv/bin/python <script>` |

`pyarrow` is required (parquet I/O for the daily layer). yfinance pulls in
`curl_cffi`, `multitasking`, `peewee`, `lxml` transitively.

---

## `pull_returns.py` — monthly layer + universe source of truth

**Role:** defines the ticker universe, exports the shared download helper, produces
all monthly outputs.

**Universe definition (in-file):**
- `ASSET_TICKERS` — dict of `{ticker: (name, asset_class, kind, notes)}` for ETFs,
  indices, mutual funds, crypto, yields, money market (≈214 entries).
- `STOCK_SECTORS` — dict of `{sector: [tickers...]}` for 128 large-cap US stocks
  across 11 GICS sectors.
- `ALL_TICKERS` — the merged list (342) used by both pullers.

**Shared helper exported:** `_download_batched(tickers, interval, period="max")` —
batched `yf.download` with rate-limit handling (see methodology §1).

**Config block (top of file):**
```python
yf.set_tz_cache_location(os.path.join(OUT, "_yf_tz_cache"))
yf.config.network.retries = 5          # exp backoff: 1s,2s,4s,8s,16s
DOWNLOAD_BATCH_SIZE = 50
INTER_BATCH_SLEEP_S = 3.0
```

**What it writes (`output/`):**
- `universe.csv` — ticker registry + `present` flag.
- `monthly_prices.csv` — wide month-end adjusted close (336 tickers).
- `monthly_returns_by_ticker.csv` — long monthly returns.
- `monthly_returns_by_asset_class.csv` — equal-weighted asset-class composites.
- `monthly_returns_by_sector.csv` — equal-weighted sector composites (ETFs + stocks).
- `monthly_returns_by_sector_stocks_only.csv` — stocks-only sector composites.
- `coverage_summary.csv` — per-ticker monthly stats.
- `asset_class_summary.csv` — per-asset-class stats.
- `README.md` — auto-generated monthly README.

**Run:** `.venv/bin/python pull_returns.py` (re-pulls all 342 tickers; not cached).

---

## `pull_daily.py` — daily layer

**Role:** daily prices + returns for the same universe. Imports `ALL_TICKERS` and
`_download_batched` from `pull_returns.py` so the two layers never diverge.

**Caching:** writes/reads `output/daily_prices.parquet` (zstd). If present, loads from
parquet (no re-download); delete the file to force a full refresh.

**Core flow:**
```python
from pull_returns import ALL_TICKERS, _download_batched
if os.path.exists(PRICES_CACHE):
    prices = pd.read_parquet(PRICES_CACHE)
else:
    prices = _download_batched(TICKERS, interval="1d", period="max")
    prices.to_parquet(PRICES_CACHE, compression="zstd")
# pct_change -> melt to long -> join metadata -> write returns panel + coverage + README
```

**What it writes (`output/`):**
- `daily_prices.parquet` (+ gitignored `daily_prices.csv`) — wide daily adjusted close.
- `daily_returns_by_ticker.parquet` (+ gitignored `.csv`) — long daily returns panel.
- `daily_coverage_summary.csv` — per-ticker daily stats.
- `daily_README.md` — auto-generated daily README.

**Run:** `.venv/bin/python pull_daily.py`.

---

## `audit_integrity.py` — verification layer (read-only on data)

**Role:** independently re-derives returns from prices and cross-checks all stored
panels. **Never writes data** — only `output/integrity_report.csv`.

**Inputs:** `daily_prices.parquet`, `daily_returns_by_ticker.parquet`,
`monthly_prices.csv`, `monthly_returns_by_ticker.csv`,
`monthly_returns_by_asset_class.csv`, `daily_coverage_summary.csv`, `universe.csv`.

**Six audit dimensions:**
| Dim | Checks |
|---|---|
| A — Structural | A1 daily index monotonic · A2 unique · A3 monthly index · A4 cols == universe · A5 panel schema |
| B — Completeness | B1 tickers with data · B2 expected-empty (SPAXX) · B3 internal gaps · B4 truncation clusters · B5 monthly == daily-resampled |
| C — Value sanity | C1 negative/zero/extreme prices · C2 returns > |50%| · C3 internal NaN |
| D — Cross-validation | D1 panel return == price pct_change · D2 monthly return == close ratio · D3 share-class twin tracking · D4 SPY TR > ^GSPC price |
| E — Coverage stats | E1 stat bounds · E2 row counts consistent |
| F — Known-failures | F1 not-on-Yahoo absent · F2 daily-only recovery · F3 SPAXX empty |

**Embedded ground-truth sets:**
- `NOT_ON_YAHOO` — 24 delisted tickers that must be absent from all outputs.
- `MONTHLY_EMPTY` — 6 tickers expected to have no monthly data.
- `TWINS` — 10 share-class / strategy pairs with expected correlation + max-return-diff
  thresholds (used by D3).

**Output:** `output/integrity_report.csv` (39 rows: severity, check, detail) and a
printed summary. Latest run: **27 PASS · 12 WARN · 0 FAIL**.

**Run:** `.venv/bin/python audit_integrity.py`.

---

## Reproduction recipes

```bash
# Fresh full rebuild (slowest, most accurate)
rm -f output/daily_prices.parquet        # drop daily cache to force re-download
.venv/bin/python pull_returns.py        # monthly (always re-pulls)
.venv/bin/python pull_daily.py          # daily  (now re-downloads too)
.venv/bin/python audit_integrity.py     # verify

# Refresh monthly only (daily cached)
.venv/bin/python pull_returns.py

# Just re-verify without pulling
.venv/bin/python audit_integrity.py
```

## Known cosmetic issues (not fixed)
- `datetime.utcnow()` deprecation warnings in both pullers' README generation —
  cosmetic, does not affect data.
- A `pandas.concat` sort warning during batch merge — cosmetic; output is explicitly
  re-sorted after concat.

## Git policy
- Tracked: parquet (daily), all monthly CSVs, universe, coverage, summaries, reports,
  the three scripts, `requirements.txt`, `.gitignore`, `handoff.md`, `docs/`.
- Gitignored: large daily CSVs (`daily_prices.csv`, `daily_returns_by_ticker.csv`),
  `__pycache__/`, `.venv/`. Regenerate the CSVs anytime via `pull_daily.py`.