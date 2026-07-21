# Four-Seasons Walk-Forward Risk Parity — Canonical Report (v3)

*Research / illustration only. Not investment advice.*

> **Long-history preset (1985–2026, ~41y).** Uses the asset-class series that
> exist back to 1985 (equities, treasuries, corporates, munis, gold via the
> VGPMX/gold-futures TR proxy) — the investable-as-of-1985 universe — and walks
> forward across ~41 years of regimes (1987 crash, 1994 bond crash, 1998 LTCM,
> 2000 dot-com, 2008 GFC, ZIRP, 2013 taper, 2020 COVID, 2022 stagflation).
> **Inflation made visible:** inflation-hedge sleeves are in the universe (gold via the long proxy),
> and **real returns** are reported (gold-deflated purchasing-power stress — NOT literal CPI; provide --cpi-csv for true real).

## 1. Setup

- Window: 1985-02-28 → 2026-07-31 (41.4 years, 498 months).
- Sleeves (7): US Equity, International Equity, World Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold/Precious Metals. Inflation hedges: Gold/Precious Metals.
- Walk-forward folds: 8 (expanding train min 10y, test 4y, step 4y). Trials/fold = 145.
- Regimes: Growth = sign(US Equity 12m return); Inflation = sign(10y yield 12m Δ).
- 11/36 both-down months are stagflation (confirms stagflation = the AW weak spot).
- Constraints: long-only, no leverage, 20% cap, 10 bps/side, Ledoit-Wolf, trailing 36m, schemes ['EW', 'InvVol', 'InvVar', 'ERC', 'MinVar'].
- Score = 0.35·stagflation + 0.15·each other season + 0.10·overall Sharpe + 0.10·div ratio.

## 2. Walk-forward OOS aggregate (concatenated held-out test periods)

OOS spans **1995-02-28 → 2026-07-31** (371 months, 30.9y) — every month is out-of-sample (selected on prior data only).

| Metric | All-Weather (OOS) | Winner process (OOS) |
|---|---:|---:|
| CAGR (nominal) | 6.53% | **6.27%** |
| Ann return (net) | 6.58% | **6.43%** |
| Ann vol | 6.87% | **8.12%** |
| Net Sharpe | 0.957 | **0.792** |
| Max drawdown | -19.06% | **-25.14%** |
| Both-down ann ret | -20.22% | **-28.84%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.906 | **0.887** |
| **CAGR (real, gold-deflated stress)** | -0.38% | **-0.34%** |

- Block-bootstrap 95% CI on OOS Sharpe: [0.376, 1.214]
- **Deflated Sharpe = 0.144** (P>0 = 0.77; trials = 1160, incl. 8 folds).

## 2b. What is the portfolio? (time-averaged winner weights across folds)

The walk-forward winner is re-selected each fold, so there is no single static
portfolio. Below is the **time-averaged allocation** across folds (and the latest
fold), with investable proxies:

| Sleeve | Avg weight | Latest fold | Investable proxy |
|---|---:|---:|---|
| US Corporate Bonds | 20.00% | 20.00% | LQD |
| US Municipal Bonds | 20.00% | 20.00% | MUB |
| US Treasuries | 20.00% | 20.00% | IEF / TLT blend |
| US Equity | 17.76% | 12.63% | VTI (or SPY) |
| World Equity | 15.54% | 14.75% | ACWI / MSCI World TR index |
| International Equity | 14.82% |   n/a  | VXUS (or VEA) |
| Gold/Precious Metals | 13.58% | 12.63% | VGPMX / gold-futures TR index (pre-GLD proxy) |

## 3. The four seasons — per-regime OOS performance (the whole point)

Average monthly net return in each economic season (OOS):

| Season | All-Weather | Winner | Winner Sharpe |
|---|---:|---:|---:|
| GrowthUp InfUp | 0.72% | **0.61%** | — |
| GrowthUp InfDown | 0.73% | **0.80%** | — |
| GrowthDown InfDown | -0.05% | **0.08%** | — |
| GrowthDown InfUp *(stagflation / AW weak spot)* | -0.81% | **-0.90%** | -0.918 |

> A truly resilient portfolio is **positive (or flat) in all four seasons**,
> especially stagflation. If it leans on any one season, that's a hidden regime bet.

## 4. Inflation stress — does inflation eat it alive?

- Nominal CAGR (OOS): **6.27%**  →  gold-deflated real CAGR: **-0.34%**
- All-Weather nominal 6.53% → real -0.38%

> **Gold-deflated is a HARSH stress** (gold rises with inflation, so
> deflating by gold measures return in *purchasing-power-of-gold* units).
> A near-zero/negative number means inflation (as priced by gold) ate the
> nominal return. For literal CPI real returns, re-run with `--cpi-csv`.

## 5. Per-fold selections (walk-forward, fully OOS)

| Fold | TRAIN | TEST | Combo | Scheme | Train score | TEST Sharpe | TEST stag Sharpe | TEST both-down ann | TEST maxDD |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | 1985-02-28..1994-12-31 | 1995-02-28..1998-12-31 | US Equity,International Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds | MinVar | 66.8 | 1.317 | n/a | -40.00% | -8.77% |
| 2 | 1985-02-28..1998-12-31 | 1999-02-28..2002-12-31 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds | ERC | 75.7 | 0.604 | n/a | -28.25% | -8.80% |
| 3 | 1985-02-28..2002-12-31 | 2003-02-28..2006-12-31 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds | ERC | 69.7 | 2.330 | n/a | -23.36% | -3.01% |
| 4 | 1985-02-28..2006-12-31 | 2007-02-28..2010-12-31 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds | InvVar | 63.9 | 0.457 | n/a | -40.10% | -25.14% |
| 5 | 1985-02-28..2010-12-31 | 2011-02-28..2014-12-31 | US Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 66.4 | 0.241 | n/a | -22.64% | -10.19% |
| 6 | 1985-02-28..2014-12-31 | 2015-02-28..2018-12-31 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 68.5 | 0.534 | n/a | -20.90% | -6.98% |
| 7 | 1985-02-28..2018-12-31 | 2019-02-28..2022-12-31 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 67.8 | 0.533 | -0.834 | -35.17% | -16.06% |
| 8 | 1985-02-28..2022-12-31 | 2023-02-28..2026-07-31 | US Equity,World Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | MinVar | 66.2 | 1.328 | n/a | -23.97% | -6.55% |

## 6. Caveats

- **Inflation proxy:** the four-seasons inflation signal is the 10y yield 12m Δ
  (market inflation-expectations/rates proxy), NOT literal CPI. Real returns use
  CPI only if `--cpi-csv` is supplied; otherwise a harsh gold-deflated stress.
  **Add a CPI series for true real-return accounting** — this is the single biggest
  remaining gap.
- **History length:** the long1985 preset uses the asset-class series that exist
  back to 1985 (~41y) — the investable-as-of-1985 set. Sleeves that only start in
  the ETF era (TIPS 2004, GLD 2004, DBC 2006, UUP 2007, EM bonds 2008) are NOT in
  this preset; run `--preset modern` for the richer 2008+ universe. 1871 is not
  available for these sleeves.
- **One inflation spike in-sample (2021-22):** the stagflation corner is still
  thinly sampled; per-season Sharpe is noisy. Read the bootstrap CI.
- No vol target; no regime-conditioned/trend overlay yet (item 10).

