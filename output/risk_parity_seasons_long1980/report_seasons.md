# Four-Seasons Walk-Forward Risk Parity — Canonical Report (v3)

*Research / illustration only. Not investment advice.*

> **Long-history preset `long1980` (1980–2026, ~46y).** Uses the asset-class series that exist across the whole
> window — the investable-as-of-then universe (equities, corporates, munis,
> gold via the VGPMX/gold-futures TR proxy, plus treasuries where they reach
> back far enough) — and walks forward across the regimes it spans (1980-82
> Volcker where included, 1987 crash, 1994 bond crash, 1998 LTCM, 2000 dot-com,
> 2008 GFC, ZIRP, 2013 taper, 2020 COVID, 2022 stagflation).
> **Inflation made visible:** inflation-hedge sleeves are in the universe (Gold/Precious Metals),
> and **real returns** are reported (gold-deflated purchasing-power stress — NOT literal CPI; provide --cpi-csv for true real).

## 1. Setup

- Window: 1980-02-29 → 2026-07-31 (46.4 years, 558 months).
- Sleeves (5): US Equity, World Equity, US Corporate Bonds, US Municipal Bonds, Gold/Precious Metals. Inflation hedges: Gold/Precious Metals.
- Walk-forward folds: 10 (expanding train min 10y, test 4y, step 4y). Trials/fold = 30.
- Regimes: Growth = sign(US Equity 12m return); Inflation = sign(10y yield 12m Δ).
- 17/54 both-down months are stagflation (confirms stagflation = the AW weak spot).
- Constraints: long-only, no leverage, 20% cap, 10 bps/side, Ledoit-Wolf, trailing 36m, schemes ['EW', 'InvVol', 'InvVar', 'ERC', 'MinVar'].
- Score = 0.35·stagflation + 0.15·each other season + 0.10·overall Sharpe + 0.10·div ratio.

## 2. Walk-forward OOS aggregate (concatenated held-out test periods)

OOS spans **1990-02-28 → 2026-07-31** (429 months, 35.8y) — every month is out-of-sample (selected on prior data only).

| Metric | All-Weather (OOS) | Winner process (OOS) |
|---|---:|---:|
| CAGR (nominal) | 7.32% | **7.00%** |
| Ann return (net) | 7.36% | **7.37%** |
| Ann vol | 7.39% | **10.86%** |
| Net Sharpe | 0.996 | **0.679** |
| Max drawdown | -20.31% | **-28.03%** |
| Both-down ann ret | -26.15% | **-30.15%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.773 | **0.791** |
| **CAGR (real, gold-deflated stress)** | 1.83% | **2.58%** |

- Block-bootstrap 95% CI on OOS Sharpe: [0.371, 1.060]
- **Deflated Sharpe = 0.143** (P>0 = 0.80; trials = 300, incl. 10 folds).

## 2b. What is the portfolio? (time-averaged winner weights across folds)

The walk-forward winner is re-selected each fold, so there is no single static
portfolio. Below is the **time-averaged allocation** across folds (and the latest
fold), with investable proxies:

| Sleeve | Avg weight | Latest fold | Investable proxy |
|---|---:|---:|---|
| US Corporate Bonds | 24.50% | 25.00% | LQD |
| US Municipal Bonds | 24.50% | 25.00% | MUB |
| US Equity | 24.50% | 25.00% | VTI (or SPY) |
| Gold/Precious Metals | 24.37% | 25.00% | VGPMX / gold-futures TR index (pre-GLD proxy) |
| World Equity | 23.33% |   n/a  | ACWI / MSCI World TR index |

## 3. The four seasons — per-regime OOS performance (the whole point)

Average monthly net return in each economic season (OOS):

| Season | All-Weather | Winner | Winner Sharpe |
|---|---:|---:|---:|
| GrowthUp InfUp | 0.39% | **0.53%** | — |
| GrowthUp InfDown | 0.94% | **0.95%** | — |
| GrowthDown InfDown | 0.60% | **0.39%** | — |
| GrowthDown InfUp *(stagflation / AW weak spot)* | -0.45% | **-0.80%** | -0.708 |

> A truly resilient portfolio is **positive (or flat) in all four seasons**,
> especially stagflation. If it leans on any one season, that's a hidden regime bet.

## 4. Inflation stress — does inflation eat it alive?

- Nominal CAGR (OOS): **7.00%**  →  gold-deflated real CAGR: **2.58%**
- All-Weather nominal 7.32% → real 1.83%

> **Gold-deflated is a HARSH stress** (gold rises with inflation, so
> deflating by gold measures return in *purchasing-power-of-gold* units).
> A near-zero/negative number means inflation (as priced by gold) ate the
> nominal return. For literal CPI real returns, re-run with `--cpi-csv`.

## 5. Per-fold selections (walk-forward, fully OOS)

| Fold | TRAIN | TEST | Combo | Scheme | Train score | TEST Sharpe | TEST stag Sharpe | TEST both-down ann | TEST maxDD |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | 1980-02-29..1989-12-31 | 1990-02-28..1993-12-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 70.8 | 1.176 | -0.387 | -22.56% | -8.13% |
| 2 | 1980-02-29..1993-12-31 | 1994-02-28..1997-12-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 69.2 | 0.537 | n/a | -25.26% | -8.08% |
| 3 | 1980-02-29..1997-12-31 | 1998-02-28..2001-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 68.2 | 0.474 | n/a | -27.27% | -19.30% |
| 4 | 1980-02-29..2001-12-31 | 2002-02-28..2005-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds | EW | 65.0 | 1.282 | n/a | -23.24% | -10.18% |
| 5 | 1980-02-29..2005-12-31 | 2006-02-28..2009-12-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 64.2 | 0.489 | n/a | -48.18% | -28.03% |
| 6 | 1980-02-29..2009-12-31 | 2010-02-28..2013-12-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 64.2 | 0.454 | n/a | -25.02% | -13.73% |
| 7 | 1980-02-29..2013-12-31 | 2014-02-28..2017-12-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 64.2 | 0.604 | n/a | -28.67% | -12.66% |
| 8 | 1980-02-29..2017-12-31 | 2018-02-28..2021-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds | EW | 65.0 | 0.823 | n/a | -30.06% | -13.02% |
| 9 | 1980-02-29..2021-12-31 | 2022-02-28..2025-12-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 66.7 | 0.927 | -0.476 | -29.99% | -19.33% |
| 10 | 1980-02-29..2025-12-31 | 2026-02-28..2026-07-31 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | EW | 64.2 | -0.247 | n/a | -89.79% | -9.11% |

## 6. Caveats

- **Inflation proxy:** the four-seasons inflation signal is the 10y yield 12m Δ
  (market inflation-expectations/rates proxy), NOT literal CPI. Real returns use
  CPI only if `--cpi-csv` is supplied; otherwise a harsh gold-deflated stress.
  **Add a CPI series for true real-return accounting** — this is the single biggest
  remaining gap.
- **History length:** the `long1980` preset uses the asset-class series that exist back to 1980 (~46y); ETF-era sleeves that inception later are excluded from it. Run `--preset modern` for the richer 2008+ universe.
- **One inflation spike in-sample (2021-22):** the stagflation corner is still
  thinly sampled; per-season Sharpe is noisy. Read the bootstrap CI.
- No vol target; no regime-conditioned/trend overlay yet (item 10).

