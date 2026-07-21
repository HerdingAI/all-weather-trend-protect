# Four-Seasons Walk-Forward Risk Parity — Canonical Report (v3)

*Research / illustration only. Not investment advice.*

> Re-thought after two critiques. (1) **No more single 10y/8y split:** this
> uses **walk-forward cross-validation** across the full 2008–2026 multi-regime
> history (GFC, ZIRP, taper, hiking, COVID, 2022 stagflation, 2023 bank stress),
> with **four-seasons (growth × inflation) regime scoring** — Bridgewater's actual
> framework — with **stagflation weighted 2x** (the All-Weather weak spot).
> **Inflation made visible:** inflation-hedge sleeves are in the universe (TIPS, gold, silver, commodities),
> and **real returns** are reported (gold-deflated purchasing-power stress — NOT literal CPI; provide --cpi-csv for true real).

## 1. Setup

- Window: 2008-01-31 → 2026-07-31 (18.5 years, 223 months).
- Sleeves (13): US Equity, International Equity, US REIT, Preferred Stock, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, TIPS, Gold, Silver, Commodities, Currency. Inflation hedges: TIPS, Gold, Silver, Commodities.
- Walk-forward folds: 4 (expanding train min 8y, test 3y, step 3y). Trials/fold = 27485.
- Regimes: Growth = sign(US Equity 12m return); Inflation = sign(10y yield 12m Δ).
- 8/16 both-down months are stagflation (confirms stagflation = the AW weak spot).
- Constraints: long-only, no leverage, 20% cap, 10 bps/side, Ledoit-Wolf, trailing 36m, schemes ['EW', 'InvVol', 'InvVar', 'ERC', 'MinVar'].
- Score = 0.35·stagflation + 0.15·each other season + 0.10·overall Sharpe + 0.10·div ratio.

## 2. Walk-forward OOS aggregate (concatenated held-out test periods)

OOS spans **2016-01-31 → 2026-07-31** (127 months, 10.6y) — every month is out-of-sample (selected on prior data only).

| Metric | All-Weather (OOS) | Winner process (OOS) |
|---|---:|---:|
| CAGR (nominal) | 7.60% | **5.70%** |
| Ann return (net) | 7.55% | **5.77%** |
| Ann vol | 6.42% | **6.55%** |
| Net Sharpe | 1.176 | **0.881** |
| Max drawdown | -12.31% | **-13.01%** |
| Both-down ann ret | -16.42% | **-19.11%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.937 | **0.731** |
| **CAGR (real, gold-deflated stress)** | -4.82% | **-6.50%** |

- Block-bootstrap 95% CI on OOS Sharpe: [0.250, 1.576]
- **Deflated Sharpe = -0.563** (P>0 = 0.04; trials = 109940, incl. 4 folds).

## 2b. What is the portfolio? (time-averaged winner weights across folds)

The walk-forward winner is re-selected each fold, so there is no single static
portfolio. Below is the **time-averaged allocation** across folds (and the latest
fold), with investable proxies:

| Sleeve | Avg weight | Latest fold | Investable proxy |
|---|---:|---:|---|
| Currency | 20.00% | 20.00% | UUP |
| US Municipal Bonds | 20.00% |   n/a  | MUB |
| US Treasuries | 20.00% | 20.00% | IEF / TLT blend |
| US Corporate Bonds | 19.14% |   n/a  | LQD |
| Preferred Stock | 16.33% | 15.41% | PFF |
| Gold | 11.58% | 20.00% | GLD |
| US Equity | 10.81% | 12.75% | VTI (or SPY) |
| US REIT |  7.22% |   n/a  | VNQ |
| Silver |  6.71% | 11.85% | SLV |

## 3. The four seasons — per-regime OOS performance (the whole point)

Average monthly net return in each economic season (OOS):

| Season | All-Weather | Winner | Winner Sharpe |
|---|---:|---:|---:|
| GrowthUp InfUp | 0.68% | **0.29%** | — |
| GrowthUp InfDown | 1.07% | **1.02%** | — |
| GrowthDown InfDown | 0.18% | **0.85%** | — |
| GrowthDown InfUp *(stagflation / AW weak spot)* | -0.47% | **-0.35%** | -0.429 |

> A truly resilient portfolio is **positive (or flat) in all four seasons**,
> especially stagflation. If it leans on any one season, that's a hidden regime bet.

## 4. Inflation stress — does inflation eat it alive?

- Nominal CAGR (OOS): **5.70%**  →  gold-deflated real CAGR: **-6.50%**
- All-Weather nominal 7.60% → real -4.82%

> **Gold-deflated is a HARSH stress** (gold rises with inflation, so
> deflating by gold measures return in *purchasing-power-of-gold* units).
> A near-zero/negative number means inflation (as priced by gold) ate the
> nominal return. For literal CPI real returns, re-run with `--cpi-csv`.

## 5. Per-fold selections (walk-forward, fully OOS)

| Fold | TRAIN | TEST | Combo | Scheme | Train score | TEST Sharpe | TEST stag Sharpe | TEST both-down ann | TEST maxDD |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | 2008-01-31..2015-12-31 | 2016-01-31..2018-12-31 | US Equity,US REIT,Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Silver | InvVar | 86.8 | 1.022 | n/a | -10.87% | -3.59% |
| 2 | 2008-01-31..2018-12-31 | 2019-01-31..2021-12-31 | US REIT,Preferred Stock,US Treasuries,US Municipal Bonds,Gold,Silver,Currency | MinVar | 79.7 | 1.438 | n/a | -16.29% | -5.99% |
| 3 | 2008-01-31..2021-12-31 | 2022-01-31..2024-12-31 | US REIT,Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Silver | InvVol | 77.3 | 0.270 | -0.398 | -22.47% | -10.98% |
| 4 | 2008-01-31..2024-12-31 | 2025-01-31..2026-07-31 | US Equity,Preferred Stock,US Treasuries,Gold,Silver,Currency | MinVar | 84.8 | 1.629 | n/a | -24.02% | -8.16% |

## 6. Caveats

- **Inflation proxy:** the four-seasons inflation signal is the 10y yield 12m Δ
  (market inflation-expectations/rates proxy), NOT literal CPI. Real returns use
  CPI only if `--cpi-csv` is supplied; otherwise a harsh gold-deflated stress.
  **Add a CPI series for true real-return accounting** — this is the single biggest
  remaining gap.
- **History length:** modern preset uses the full ETF-era multi-sleeve set from
  ~2008 (18.6y). For the ~41y investable-as-of-1985 view, run `--preset long1985`.
- **One inflation spike in-sample (2021-22):** the stagflation corner is still
  thinly sampled; per-season Sharpe is noisy. Read the bootstrap CI.
- No vol target; no regime-conditioned/trend overlay yet (item 10).

