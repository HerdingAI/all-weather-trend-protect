# Handoff — Stock_Price

## Goal
Download all ticker data as far back as Yahoo Finance provides, at the highest
granularity available (daily + monthly).

## Documentation
Full system docs live in `docs/` — start at `docs/README.md`:
- `docs/data_dictionary.md` — every output file, field-by-field
- `docs/coverage.md` — date ranges, per-ticker/asset-class/sector coverage
- `docs/methodology.md` — how values are derived (adjustment, returns, aggregation)
- `docs/nuances_and_caveats.md` — data quirks + integrity-audit triage
- `docs/scripts_reference.md` — the 3 scripts, config, reproducibility
Root `README.md` is the entry point.

## Current state (2026-07-17)
- Branch: `feat/expand-universe-daily-download` (commit 330ab25), **not yet pushed / no PR**.

## Risk-parity peer-review round (2026-07-20, this branch)
A critical peer review of `risk_parity_eval.py` was written to `docs/peer-review.md`
and four methodology fixes were implemented and committed on this branch
(`3c173af`..`c12400e`):

- **Fix 1** (`3c173af`) — per-sleeve cap enforced **inside** the MinVar/ERC solver via
  exact capped-simplex projection (`project_capped_simplex`), not post-hoc clip.
- **Fix 2** (`c9ebe73`) — both-down regime + equity-correlation metric decoupled to
  **external SPY/AGG** (`--ref-mode external`, default); `--ref-mode sleeves` is the
  legacy regression guard.
- **Fix 3 + Fix 4 + cap-integrity refinement** (`23e4471`) — **LS-TSMOM** managed-futures
  scheme folded into the canonical pipeline (TRAIN/TEST/rolling, DSR, bootstrap CIs,
  §9 head-to-head); DSR **effective-N** diagnostic + caveat block; and a numerical
  refinement to Fix 1's projection (residual correction onto interior coords + drop the
  `w/w.sum()` renorm that broke the cap) — verified 0 cap-overshoot, |sum-1|~3e-16.
- **Peer-review doc** (`827a4d6`), **README + .gitignore** (`c12400e`).

Canonical report regenerated: `output/risk_parity_eval/report_eval.md` (NOT tracked —
regenerable with `.venv/bin/python risk_parity_eval.py`). Headline measured answer to
the brief ("a flavor that does well where All-Weather is weak"): the **MinVar** risk-parity
winner (OOS Sharpe 1.518, both-down −11.42%, MaxDD −5.61%, cap 20.00% = exact) **dampens**
the AW weak spot but doesn't flip it positive; **LS-TSMOM** (Sharpe 0.347, both-down
−4.82% — smallest of the three, equity corr 0.129) is the right *direction* but its edge
is **not statistically significant** (DSR −0.964, Sharpe CI [−0.482, 1.213], both-down CI
[−10.45%, +3.14%]). Effective N = 1.2 vs nominal 16,902 (DSR is conservative). Both-down
counts (external ref): TRAIN 17 / TEST 24.

**Note:** the cap-integrity refinement shifted ERC weights, which shifted the
TRAIN-selected LS-TSMOM combo and its numbers slightly between runs — the regenerated
report's numbers are authoritative; the `docs/peer-review.md` "Measured outcomes" block
matches them.

## TrendProtect flavor round (2026-07-20, this branch)
Extended `risk_parity_eval.py` to answer the next brief: *find an All-Weather
variant with higher expected return while keeping equity correlation asymmetric
(correlated up, protected down)*. Two commits on this branch (`817ae65`, `85cd3c5`):

- **Four TrendProtect flavors** as presets of one `_backtest_flavor` engine, each a
  long MinVar base leg plus overlays: **TrendGate** (gate equity sleeves to cash when
  trailing-12m < 0, gross ≤1), **RP-LS-Overlay** (+0.30 dollar-neutral LS-TSMOM overlay,
  gross 1.30), **StructShort** (permanent sleeve-level net-short US Treasuries 0.30,
  netting so gross ≤1), **TG-LS-Overlay** (gate + 0.20 LS overlay, gross 1.20).
- **Asymmetric metrics** in `compute_metrics`: `upside_beta`/`downside_beta`/
  `updown_beta_diff`/`downside_corr_eq`/`up_market_ann`/`down_market_ann` (equity
  ref = external SPY). **`--score-mode asymmetric`** = 0.30·Sharpe + 0.20·(upβ−dnβ)
  + 0.20·(−dn_corr) + 0.15·both-down + 0.15·(−maxDD); selection TRAIN-only (guard
  unchanged). **`--lev-rate 0.058`** (5.8% APR) charged monthly on gross>1.
- **Report §10** = ranked comparison menu (4 flavors + AW + MinVar winner + LS-TSMOM)
  with Upβ/Dnβ/Dn-corr/gross/lev cost/DSR/bootstrap CI + per-flavor pros/cons + verdict.
- **`docs/portfolio-flavors.md`** = full 10-flavor catalog (construction, composition,
  parameters, pros/cons, regime wins/loses) + the measured menu.

Canonical asymmetric run: `output/risk_parity_eval_asym/report_eval.md`
(regenerable: `.venv/bin/python risk_parity_eval.py --score-mode asymmetric`).
**Measured verdict (honest):** **no TrendProtect flavor beats All-Weather's 7.37%
net OOS** after the 5.8% leverage cost in this window. The flavors buy a much better
*risk* profile — **TrendGate** leads on Sharpe (1.385 vs AW 1.055), MaxDD (−4.20% vs
−12.31%), both-down (−4.50% vs −18.74%) — at ~3%/yr of return. The asymmetric goal is
**only weakly met**: the gate keeps Upβ and Dnβ **both low** (gate mostly flats
equity → combos run bond/gold/commodity-heavy) and Dnβ slightly **exceeds** Upβ
(the documented 12m lag works *against* the asymmetric shape). LS-TSMOM is the only
Upβ<0 flavor but DSR −1.22 (insignificant). Regression guard (default score,
COV-only): canonical numbers byte-identical (MinVar 1.518/−11.42%/−5.61; AW
1.055/−18.74%); new code paths are opt-in.

**Honest caveats:** StructShort = sleeve-level netting (gross ≤1, no lev cost) —
ticker-level shorting that *adds* gross is a flagged refinement, not implemented.
Trend-gate lag is a construction property, not a bug. One TRAIN/TEST split = one
regime; flavors share sleeves → DSR conservative (effective N ≪ nominal); trust the
bootstrap CI.

## TrendProtect round 2 — gate_mode=short / EW-base / asymmetric2 (2026-07-20)
Round 1's measured negative result (no flavor beat 7.37% with the asymmetric property)
diagnosed three causes: (a) the **cash-gate can't produce negative Dnβ** (it only flats
equity); (b) the **MinVar base starves equity** to ~5-10% weight → little upside to
capture and little to short; (c) the **`asymmetric` score flees equity** (the `upβ−dnβ`
term rewards a combo low in *both*). Round 2 fixes all three (uncommitted in working
tree — `risk_parity_eval.py` + `docs/portfolio-flavors.md` updated):

- **`gate_mode="short"`** — on the downside signal, *flip* the equity sleeve to net-short
  (`pos *= sign(trailing-lookback)` for equity sleeves) instead of flat. The direct lever
  for negative downside-β the brief's "long-term short a ticker" permission enables.
- **`base_mode="ew"`** — equal-weight base leg (like AW's own ~1/n) so equity keeps a real
  weight (~12-25%) — fixes the MinVar-base equity starvation.
- **`--score-mode asymmetric2`** — `0.30·pct(ann_return_net) + 0.20·pct(upside_beta)
  + 0.15·pct(−downside_beta) + 0.10·pct(−downside_corr_eq) + 0.15·pct(Sharpe)
  + 0.10·pct(−maxDD)` — rewards a high Upβ (real equity weight) AND a high net return,
  so the search keeps equity in the book instead of fleeing to diversifiers.
- **Six new flavors:** TG-Short, TG-Short-LS, TG-Short-6m (MinVar base) + EW-Short,
  EW-Short-LS, EW-Short-6m (EW base). Plus `lookback=6` per-preset override for less lag.
- **`sc` DataFrame fix:** added `ann_return_net` column to the TEST `sc` DataFrame in
  `main()` (the asymmetric2 score needs it; default/asymmetric paths unaffected).

**Canonical run:** `output/risk_parity_eval_asym2b/report_eval.md` (regenerable:
`.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --schemes
EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,
EW-Short-LS,EW-Short-6m --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir
output/risk_parity_eval_asym2b`). 36621 TRAIN trials, 13 schemes.

**Measured verdict (round 2, honest) — two findings, one per half of the brief:**
1. **One flavor beats AW's 7.37% net OOS return: the RP winner (MinVar) at 9.29%** — but
   it is plain long-only risk parity with **no** asymmetry (Dnβ 0.585 > Upβ 0.432, Dn-corr
   0.747 ≈ AW). Dropping the asymmetry constraint, return is beatable; keeping it, it is
   not (in this window).
2. **No flavor beats 7.37% *with* the asymmetric property.** In **every** flavor Dnβ ≥
   Upβ. The `gate_mode=short` lever does buy **real downside-correlation reduction**
   (TG-Short-LS Dn-corr 0.199, TG-Short 0.366 vs AW 0.793) — partial progress on
   "protected down" — but at the cost of return (3-5%) AND upside capture (Upβ also
   crushed to 0.06-0.13). The EW-Short family (real equity + short-on-downside) was the
   strongest direct test and **whipsawed to 0.37-3.14%** — the lagged short sells the
   bottom of 2018 / the 2020 COVID rebound. Every flavor's DSR is negative (edge not
   significant).

**Structural blocker (consistent across both rounds):** trailing 12m/6m momentum is
*lagging* — long into drawdown starts (eats the downside), short/flat into rally starts
(misses the upside) → Dnβ ≥ Upβ everywhere. Beating AW on return while keeping the
asymmetric shape needs a **leading/faster downside signal** (MA crossover, regime filter,
equity-below-10m-MA) that exits equity *before* the drawdown and re-enters *before* the
rally — not more TSMOM lookback tuning (that is overfitting). This is the untested lever
for round 3.

## Next steps (open) — risk parity
- A proper OOS multiple-comparison test (Holm/Bonferroni over effective-N, or DSR on the
  TRAIN max) — currently only disclosed, not implemented.
- LS-TSMOM vol-scaling (currently equal-weight base for neutrality) + a real T-bill
  collateral return (currently 0%, conservative — real adds ~1-2%/yr).
- Vol-targeting + leverage + a cash/T-bill sleeve (would let risk parity *scale* risk).
- Regime-conditioned allocation / CVaR / carry overlays.
- Push branch + open PR if desired.
- Universe: **342 tickers** (71 original asset-class + 128 individual stocks + 143 new
  mutual funds/ETFs/crypto from user-provided list). Defined in `pull_returns.py`
  (`ASSET_TICKERS` + `STOCK_SECTORS`).
- **Daily data**: `output/daily_prices.parquet` (+ CSV). 24,753 days, 1927-12-30 →
  2026-07-17, 341 tickers with data (only SPAXX empty — money market, only 1d/5d).
  2.7M data cells. Long returns panel: `daily_returns_by_ticker.parquet` (2.71M rows).
- **Monthly data**: `output/monthly_prices.csv` etc. 775 months, 1962-01 → 2026-07,
  336 tickers. 6 fail monthly `period=max`: PADMX, PAGPX, PIGLX, AUBAX, LOMMX, SPAXX.
  (5 of those DO have daily data — Yahoo quirk; monthly aggregate unavailable.)

## How to reproduce
```bash
.venv/bin/python pull_returns.py   # monthly (refresh all 342)
.venv/bin/python pull_daily.py     # daily  (uses cached parquet if present)
```
Deps: `pip install -r requirements.txt` (needs `pyarrow` for parquet).

## Architecture notes
- `_download_batched()` in `pull_returns.py` is the shared download helper (batch=50,
  3s sleep, `yf.config.network.retries=5`, 60s timeout). `pull_daily.py` imports it.
- `pull_daily.py` caches `output/daily_prices.parquet`; delete it to force re-download.
- Outputs: parquet (efficient, tracked) for daily; CSV for monthly. Large daily CSVs
  (daily_prices.csv 31MB, daily_returns_by_ticker.csv 229MB) are gitignored.

## Known caveats
- 5 tickers have daily but not monthly history (PADMX/PAGPX/PIGLX/AUBAX/LOMMX).
- SPAXX empty for both (money market).
- Broad indices (^GSPC/^DJI/^IXIC/^RUT/^VIX) are price-only (no dividends).
- ^TNX/^FVX/^TYX are yield levels, not prices — kept in prices but returns meaningless.
- 24 user-listed tickers are not on Yahoo at all (delisted): CMR, FPIDX, KBONX, PGBDX,
  PGLIX, PINVX, VAB, VCE, VCN, VDAIX, VDMIX, VEE, VFSVX, VFTSX, VFV, VFWIX, VGV,
  VHDYX, VIU, VMMXX, VSP, VTGMX, VTWSX, VXC.

## Data integrity pass (2026-07-17)
- Audited by `audit_integrity.py` (6 dimensions A-F) → `output/integrity_report.csv`,
  triage written up in `output/integrity_findings.md`.
- **Result: 0 FAIL · 27 PASS · 12 WARN — pipeline verified correct.**
- Pipeline correctness proven (D1/D2/B5/D4): returns exactly equal price pct_change;
  monthly==daily-resampled; SPY total-return (30.8×) > ^GSPC price-only (17.0×).
- All 12 WARN explained (none are bugs):
  - C2 extreme returns: 21 real market events (AAPL 2000, AIG 2008, WMB 2002, ^VIX
    spikes) + 2 ancient unadjusted splits (MCD 1968/1969 — Yahoo source gap, not patched).
  - C3 internal NaN (1,106): 99% in money market (VMRXX/VUSXX 227 each) + yield indices
    (^TNX/^FVX/^TYX) which legitimately lack daily data; rest are 1-2 isolated cells.
  - D3 share-class twin divergences: mutual-fund capital-gains-distribution timing in
    Yahoo source across Investor/Admiral share classes (corr ≥0.99, level ratios stable).
  - B3 gaps: VMRXX (money market, expected).
- No data patched; all findings documented for transparency.

## Next steps (open)
- Push branch + open PR if desired.
- Optionally: remove the 6 always-empty tickers from the universe, or re-pull them
  with explicit start/end dates instead of `period=max`.
- `datetime.utcnow()` deprecation warnings in both scripts (cosmetic).
EOF