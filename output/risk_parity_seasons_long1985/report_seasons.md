# Four-Seasons Walk-Forward Risk Parity — Canonical Report (v3)

*Research / illustration only. Not investment advice.*

> **Long-history preset `long1985` (1985–2026, ~41y).** Uses the asset-class series that exist across the whole
> window — the investable-as-of-then universe (equities, corporates, munis,
> gold via the VGPMX/gold-futures TR proxy, plus treasuries where they reach
> back far enough) — and walks forward across the regimes it spans (1980-82
> Volcker where included, 1987 crash, 1994 bond crash, 1998 LTCM, 2000 dot-com,
> 2008 GFC, ZIRP, 2013 taper, 2020 COVID, 2022 stagflation).
> **Inflation made visible:** inflation-hedge sleeves are in the universe (Gold/Precious Metals),
> and **real returns** are reported (gold-deflated purchasing-power stress — NOT literal CPI; provide --cpi-csv for true real).

## 1. Setup

- Window: 1985-02-28 → 2026-07-31 (41.4 years, 498 months).
- Sleeves (6): US Equity, International Equity, World Equity, US Corporate Bonds, US Municipal Bonds, Gold/Precious Metals. Inflation hedges: Gold/Precious Metals.
- Walk-forward folds: 8 (expanding train min 10y, test 4y, step 4y). Trials/fold = 35.
- Regimes: Growth = sign(US Equity 12m return); Inflation = sign(10y yield 12m Δ).
- 11/36 both-down months are stagflation (confirms stagflation = the AW weak spot).
- Constraints: long-only, no leverage, 20% cap, 10 bps/side, Ledoit-Wolf, trailing 36m, schemes ['EW', 'InvVol', 'InvVar', 'ERC', 'MinVar'].
- Score = 0.35·stagflation + 0.15·each other season + 0.10·overall Sharpe + 0.10·div ratio.

## 2. Walk-forward OOS aggregate (concatenated held-out test periods)

OOS spans **1995-02-28 → 2026-07-31** (371 months, 30.9y) — every month is out-of-sample (selected on prior data only).

| Metric | All-Weather (OOS) | Winner process (OOS) |
|---|---:|---:|
| CAGR (nominal) | 7.27% | **8.09%** |
| Ann return (net) | 7.32% | **8.56%** |
| Ann vol | 7.49% | **12.27%** |
| Net Sharpe | 0.978 | **0.698** |
| Max drawdown | -20.31% | **-31.95%** |
| Both-down ann ret | -26.04% | **-37.52%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.779 | **0.836** |
| **CAGR (real, gold-deflated stress)** | 0.64% | **1.92%** |

- Block-bootstrap 95% CI on OOS Sharpe: [0.321, 1.072]
- **Deflated Sharpe = 0.125** (P>0 = 0.75; trials = 280, incl. 8 folds).

## 2b. What is the portfolio? (time-averaged winner weights across folds)

The walk-forward winner is re-selected each fold, so there is no single static
portfolio. Below is the **time-averaged allocation** across folds (and the latest
fold), with investable proxies:

| Sleeve | Avg weight | Latest fold | Investable proxy |
|---|---:|---:|---|
| US Corporate Bonds | 20.00% | 20.00% | LQD |
| US Municipal Bonds | 20.00% | 20.00% | MUB |
| US Equity | 20.00% | 20.00% | VTI (or SPY) |
| World Equity | 19.20% | 20.00% | ACWI / MSCI World TR index |
| Gold/Precious Metals | 18.99% | 20.00% | VGPMX / gold-futures TR index (pre-GLD proxy) |
| International Equity | 14.50% |   n/a  | VXUS (or VEA) |

## 3. The four seasons — per-regime OOS performance (the whole point)

Average monthly net return in each economic season (OOS):

| Season | All-Weather | Winner | Winner Sharpe |
|---|---:|---:|---:|
| GrowthUp InfUp | 0.45% | **0.71%** | — |
| GrowthUp InfDown | 0.91% | **1.03%** | — |
| GrowthDown InfDown | 0.58% | **0.45%** | — |
| GrowthDown InfUp *(stagflation / AW weak spot)* | -1.10% | **-1.21%** | -0.936 |

> A truly resilient portfolio is **positive (or flat) in all four seasons**,
> especially stagflation. If it leans on any one season, that's a hidden regime bet.

## 4. Inflation stress — does inflation eat it alive?

- Nominal CAGR (OOS): **8.09%**  →  gold-deflated real CAGR: **1.92%**
- All-Weather nominal 7.27% → real 0.64%

> **Gold-deflated is a HARSH stress** (gold rises with inflation, so
> deflating by gold measures return in *purchasing-power-of-gold* units).
> A near-zero/negative number means inflation (as priced by gold) ate the
> nominal return. For literal CPI real returns, re-run with `--cpi-csv`.

## 5. Per-fold selections (walk-forward, fully OOS)

| Fold | TRAIN | TEST | Combo | Scheme | Train score | TEST Sharpe | TEST stag Sharpe | TEST both-down ann | TEST maxDD |
|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | 1985-02-28..1994-12-31 | 1995-02-28..1998-12-31 | US Equity,International Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 62.6 | 0.852 | n/a | -35.38% | -15.33% |
| 2 | 1985-02-28..1998-12-31 | 1999-02-28..2002-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 72.1 | 0.718 | n/a | -27.44% | -13.33% |
| 3 | 1985-02-28..2002-12-31 | 2003-02-28..2006-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 74.3 | 1.532 | n/a | -44.85% | -7.76% |
| 4 | 1985-02-28..2006-12-31 | 2007-02-28..2010-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 69.4 | 0.565 | n/a | -50.43% | -31.95% |
| 5 | 1985-02-28..2010-12-31 | 2011-02-28..2014-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 68.6 | 0.090 | n/a | -31.66% | -13.04% |
| 6 | 1985-02-28..2014-12-31 | 2015-02-28..2018-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 69.0 | 0.335 | n/a | -30.69% | -12.06% |
| 7 | 1985-02-28..2018-12-31 | 2019-02-28..2022-12-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 69.0 | 0.489 | -0.860 | -49.35% | -21.41% |
| 8 | 1985-02-28..2022-12-31 | 2023-02-28..2026-07-31 | US Equity,World Equity,US Corporate Bonds,US Municipal Bonds,Gold/Precious Metals | InvVar | 68.4 | 1.321 | n/a | -29.71% | -8.10% |

## 6. Caveats

- **Inflation proxy:** the four-seasons inflation signal is the 10y yield 12m Δ
  (market inflation-expectations/rates proxy), NOT literal CPI. Real returns use
  CPI only if `--cpi-csv` is supplied; otherwise a harsh gold-deflated stress.
  **Add a CPI series for true real-return accounting** — this is the single biggest
  remaining gap.
- **History length:** the `long1985` preset uses the asset-class series that exist back to 1985 (~41y); ETF-era sleeves that inception later are excluded from it. Run `--preset modern` for the richer 2008+ universe.
- **One inflation spike in-sample (2021-22):** the stagflation corner is still
  thinly sampled; per-season Sharpe is noisy. Read the bootstrap CI.
- No vol target; no regime-conditioned/trend overlay yet (item 10).

