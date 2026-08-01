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

- Window: 1986-06-30 → 2026-07-31 (40.1 years, 482 months).
- Sleeves (7): US Equity, International Equity, World Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold/Precious Metals. Inflation hedges: Gold/Precious Metals.
- Walk-forward folds: 8 (expanding train min 10y, test 4y, step 4y). Trials/fold = 145.
- Regimes: Growth = sign(US Equity 12m return); Inflation = sign(10y yield 12m Δ).
- 11/36 both-down months are stagflation (confirms stagflation = the AW weak spot).
- Constraints: long-only, no leverage, 20% cap, 10 bps/side, Ledoit-Wolf, trailing 36m, schemes ['EW', 'InvVol', 'InvVar', 'ERC', 'MinVar'].
- Score = 0.35·stagflation + 0.15·each other season + 0.10·overall Sharpe + 0.10·div ratio.

## 2. Walk-forward OOS aggregate (concatenated held-out test periods)

OOS spans **1996-06-30 → 2026-07-31** (355 months, 29.6y) — every month is out-of-sample (selected on prior data only).

| Metric | All-Weather (OOS) | Winner process (OOS) |
|---|---:|---:|
| CAGR (nominal) | 6.81% | **5.98%** |
| Ann return (net) | 6.89% | **6.20%** |
| Ann vol | 7.58% | **8.64%** |
| Net Sharpe | 0.909 | **0.718** |
| Max drawdown | -20.31% | **-24.46%** |
| Both-down ann ret | -26.04% | **-28.16%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.783 | **0.846** |
| **CAGR (real, gold-deflated stress)** | -0.41% | **-1.57%** |

- Block-bootstrap 95% CI on OOS Sharpe: [0.350, 1.140]
- **Deflated Sharpe = 0.055** (P>0 = 0.61; trials = 1160, incl. 8 folds).

## 2b. What is the portfolio? (time-averaged winner weights across folds)

The walk-forward winner is re-selected each fold, so there is no single static
portfolio. Below is the **time-averaged allocation** across folds (and the latest
fold), with investable proxies:

| Sleeve | Avg weight | Latest fold | Investable proxy |
|---|---:|---:|---|
| US Corporate Bonds | 20.00% | 20.00% | LQD |
| US Municipal Bonds | 20.00% | 20.00% | MUB |
| US Treasuries | 20.00% | 20.00% | IEF / TLT blend |
| US Equity | 20.00% | 20.00% | VTI (or SPY) |
| World Equity | 16.51% |   n/a  | ACWI / MSCI World TR index |
| Gold/Precious Metals | 11.06% | 20.00% | VGPMX / gold-futures TR index (pre-GLD proxy) |

## 3. The four seasons — per-regime OOS performance (the whole point)

Average monthly net return in each economic season (OOS):

| Season | All-Weather | Winner | Winner Sharpe |
|---|---:|---:|---:|
| GrowthUp InfUp | 0.39% | **0.42%** | — |
| GrowthUp InfDown | 0.87% | **0.84%** | — |
| GrowthDown InfDown | 0.64% | **0.39%** | — |
| GrowthDown InfUp *(stagflation / AW weak spot)* | -0.68% | **-0.86%** | -0.729 |

> A truly resilient portfolio is **positive (or flat) in all four seasons**,
> especially stagflation. If it leans on any one season, that's a hidden regime bet.

## 4. Inflation stress — does inflation eat it alive?

- Nominal CAGR (OOS): **5.98%**  →  gold-deflated real CAGR: **-1.57%**
- All-Weather nominal 6.81% → real -0.41%

> **Gold-deflated is a HARSH stress** (gold rises with inflation, so
> deflating by gold measures return in *purchasing-power-of-gold* units).
> A near-zero/negative number means inflation (as priced by gold) ate the
> nominal return. For literal CPI real returns, re-run with `--cpi-csv`.

## 5. Per-fold selections (walk-forward, fully OOS)

| Fold | TRAIN | TEST | Combo | Scheme | Train score | TEST Sharpe | TEST stag Sharpe | TEST both-down ann | TEST maxDD |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | 1986-06-30..1996-04-30 | 1996-06-30..2000-04-30 | US Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVol | 68.9 | 0.344 | n/a | -24.83% | -12.51% |
| 2 | 1986-06-30..2000-04-30 | 2000-06-30..2004-04-30 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | ERC | 74.3 | 1.092 | n/a | -25.84% | -7.55% |
| 3 | 1986-06-30..2004-04-30 | 2004-06-30..2008-04-30 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 77.3 | 2.117 | n/a | -12.29% | -2.72% |
| 4 | 1986-06-30..2008-04-30 | 2008-06-30..2012-04-30 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 68.6 | 0.457 | n/a | -42.93% | -21.53% |
| 5 | 1986-06-30..2012-04-30 | 2012-06-30..2016-04-30 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 70.1 | 0.848 | n/a | -15.80% | -5.68% |
| 6 | 1986-06-30..2016-04-30 | 2016-06-30..2020-04-30 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds | InvVol | 71.3 | 0.760 | n/a | -29.49% | -9.11% |
| 7 | 1986-06-30..2020-04-30 | 2020-06-30..2024-04-30 | US Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVol | 68.4 | 0.230 | -0.528 | -33.14% | -20.18% |
| 8 | 1986-06-30..2024-04-30 | 2024-06-30..2026-07-31 | US Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVol | 68.9 | 1.512 | n/a | -24.14% | -8.97% |

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

