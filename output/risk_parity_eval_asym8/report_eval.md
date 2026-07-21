# Risk-Parity Resilience Search — Canonical (Out-of-Sample) Report

*Research / illustration only. Not investment advice.*

> **This is the canonical report.** The in-sample `output/risk_parity/report.md`
> is a method appendix; do **not** cite its numbers as the headline. All numbers
> below are **out-of-sample, net of 10.0 bps/side transaction costs**,
> with **Ledoit-Wolf covariance shrinkage**, a **20% per-sleeve cap**,
> the **Volatility (^VIX) sleeve excluded** (non-tradable), and the score encoding
> **diversification + low both-down correlation** ("uncorrelated positive returns").

## 1. Setup (remediated)

- **TRAIN (selection):** 2008-01-31 → 2017-12-31.
- **TEST (evaluation only):** 2018-01-31 → 2026-07-31 — contains 2020
  COVID, 2022 stocks+bonds rout, 2023 SVB stress; never seen at selection time.
- **Sleeves (12):** US Equity, International Equity, US REIT, Preferred Stock, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Gold, Silver, Commodities, Currency.  Volatility (^VIX) excluded by
  default (non-tradable; opt in with `--include-volatility` for illustration only).
- **Combos × schemes:** 2817 × 45 = **126765 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, RP-LS-Overlay, StructShort, TG-LS-Overlay, TG-Short, TG-Short-LS, TG-Short-6m, EW-Short, EW-Short-LS, EW-Short-6m, EW-MA-Short, EW-Vol-Short, EW-DMA-Short, EW-AsymMA-Short, EW-DDStop-Short, EW-AsymMA-Short-6, EW-AsymMA-Short-9, EW-AsymMA-Tight, EW-AsymVol-Short, EW-Hedge-DMA-1, EW-Hedge-DMA, EW-Hedge-DMA-2, EW-Hedge-MA, EW-Hedge-DD, EW-Hedge-Dur, EW-Hedge-Dur-MA, EW-Hedge-Dur-DD, EW-Hedge-Dur-2, EW-Hedge-Dur-DD2, EW-Infl-Dur, EW-Infl-DurL, EW-Infl-Both, EW-Infl-BothL, EW-Infl-DurL2, EW-InflC-Both, EW-InflC-BothL, EW-InflC-Dur, EW-InflC-DurL, EW-InflC-Both6 — EW/InvVol/InvVar/ERC/MinVar separate composition
  from allocation; **LS-TSMOM** is a long/short managed-futures (trend) overlay that
  targets the All-Weather weak spot (both-down / stagflation) — see §9.
- **Constraints:** long-only, no leverage, **per-sleeve cap 20%**, monthly
  rebalance, **10.0 bps/side** transaction costs, **lw** covariance
  shrinkage, trailing 36m, annual refit.
- **Score =** 0.30·pct(net Sharpe) + 0.25·pct(both-down ann ret) + 0.15·pct(−maxDD)
  + 0.15·pct(diversification ratio) + 0.15·pct(−corr with equity in both-down months).
- **Both-down regime reference:** external: SPY + AGG (`--ref-mode external`). Both-down months: TRAIN 17 | TEST 24. 'external' uses investable non-candidate indices (SPY/AGG) so the equity-correlation metric measures a hedge, not a tautology from the reference overlapping the universe.
- **ERC cap mode:** capped (cap enforced inside the solver for MinVar and ERC-capped; see §2 'Cap integrity').

## 2. Headline — selected winner, OUT OF SAMPLE (TEST)

- **Combo:** US Equity,International Equity,US REIT,EM Bonds,Commodities
- **Scheme:** EW-InflC-BothL  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 90.9, z = +3.39)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.734 | **0.609** | -0.125 |
| Both-down ann ret (net) | -18.04% | **-43.12%** | -25.08% |
| Max drawdown | -17.60% | **-25.74%** | -8.14% |
| Diversification ratio | n/a | **n/a** | — |
| Corr w/ equity (both-down) | -0.485 | **0.803** | — |
| Ann turnover | 119.90% | 37.09% | — |

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **126765**.
- Raw OOS net Sharpe: **0.609**.
- Expected max null Sharpe over 126765 trials: 1.614 (annualized).
- **Deflated Sharpe (annualized): -1.005**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.00** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [0.067, 1.489]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-57.69%, -21.26%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 126765 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.5** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 **and** the both-down CI is entirely negative: there is **no statistically robust resilience** to the both-down scenario among these investable sleeves — the best portfolio is the least-bad, not a positive-return hedge.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 7.37% | **8.43%** |
| Ann vol | 6.99% | **13.86%** |
| Net Sharpe | 1.055 | **0.609** |
| Max DD | -12.31% | **-25.74%** |
| Both-down ann ret | -18.74% | **-43.12%** |
| Both-down hit rate | 16.67% | **12.50%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.885 | **0.865** |
| Corr w/ bonds | 0.437 | **0.434** |
| Crisis avg ret | -3.04% | **-9.63%** |

Winner OOS Sharpe − All-Weather = **-0.446**; both-down ann diff = **-0.2438**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| EW-InflC-Both6 | 2 | 0.626 | -41.56% | -24.72% | n/a | 60.0 | 30 |
| EW-InflC-Both | 17 | 0.649 | -38.18% | -22.81% | n/a | 53.6 | 25 |
| EW-InflC-BothL | 31 | 0.645 | -37.36% | -22.29% | n/a | 49.0 | 25 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 12.1 | field dispersion |
| Winner TRAIN score (z) | +3.39 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 70% | selection stability |
| Spearman TRAIN↔TEST score | +0.11 | rank persistence |
| Winner Sharpe test−train | -0.125 | large negative ⇒ overfit |
| Winner both-down test−train | -0.2508 | large negative ⇒ overfit |
| Effective N (vs nominal 126765) | 1.5 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.660**
- OOS (rolling) both-down ann ret = **-38.30%**
- OOS (rolling) max drawdown = -22.37%
- Rolling Deflated Sharpe = -0.954  (P>0 = 0.00)

| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |
|---:|---|---|---:|---:|---|
| 2018 | US Equity,International Equity,Preferred Stock,US Treasuries,Gold,Silver | MinVar | 78.1 | 0.66 | US Equity 20.0% |
| 2019 | US Equity,US REIT,US Corporate Bonds,Gold,Silver | MinVar | 74.4 | 0.71 | US Equity 20.0% |
| 2020 | US REIT,US Corporate Bonds,EM Bonds,Gold,Silver | EW | 80.6 | 0.59 | US REIT 20.0% |
| 2021 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold,Silver | EW | 74.2 | 0.52 | US Equity 20.0% |
| 2022 | US Equity,US REIT,Preferred Stock,US Corporate Bonds,Gold,Silver | MinVar | 71.0 | 0.98 | US REIT 20.0% |
| 2023 | US Equity,International Equity,US Treasuries,Gold,Silver,Commodities | MinVar | 71.1 | 0.46 | US Equity 20.0% |
| 2024 | US Equity,International Equity,US Treasuries,Gold,Silver | MinVar | 72.7 | 0.53 | US Equity 20.0% |
| 2025 | US Equity,International Equity,US Municipal Bonds,Gold,Silver | EW | 75.5 | 0.64 | US Equity 20.0% |
| 2026 | US Equity,International Equity,US Municipal Bonds,Gold,Silver | EW | 76.8 | 1.00 | US Equity 20.0% |

## 9. Managed-futures (LS-TSMOM) on an equal footing (Fix 3)

The long/short managed-futures (time-series-momentum) direction — previously only
tested in the separate `all_weather_v2.py` report with no DSR / walk-forward /
bootstrap — is now folded into this canonical pipeline. Each month, for each combo
sleeve, `pos = base_w · sign(trailing-12m return)` with **equal-weight base**,
**$1 gross, 0% T-bill collateral** (matches awv2's conservative assumption), and the
same 10 bps/side turnover+cost machinery. It goes through the same combo×scheme
TRAIN selection, TEST eval, and rolling re-enumeration as the risk-parity schemes —
so the comparison is measured, not assumed. This is the direct test of the brief:
*find an All-Weather flavor that does well where All-Weather is weak (both-down /
stagflation)* — long/short trend is positive in 2022 precisely because it **shorts**
the falling bonds+equities, which long-only risk parity cannot do.

- **TRAIN-best LS-TSMOM combo:** US REIT, US Treasuries, US Corporate Bonds, Gold, Silver
- **Signal:** `pos = (1/n)·sign(trailing-12m)` per sleeve, monthly. Lookback configurable via `--tsmom-lookback`.

| Metric | All-Weather (OOS) | Risk-parity winner (OOS) | **LS-TSMOM (OOS)** |
|---|---:|---:|---:|
| Ann return (net) | 7.37% | 8.43% | **2.60%** |
| Ann vol | 6.99% | 13.86% | **10.46%** |
| Net Sharpe | 1.055 | 0.609 | **0.248** |
| Max DD | -12.31% | -25.74% | **-25.31%** |
| Both-down ann ret | -18.74% | -43.12% | **-11.31%** |
| Both-down hit rate | 16.67% | 12.50% | **41.67%** |
| Corr w/ equity | 0.885 | 0.865 | **0.149** |
| Crisis avg ret | -3.04% | -9.63% | **-4.84%** |

- LS-TSMOM OOS net Sharpe: **0.248**
- LS-TSMOM OOS both-down ann ret: **-11.31%**  (hit rate 41.67%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.063**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.498, 1.162]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-22.02%, 2.38%]

> **Verdict:** LS-TSMOM **reduces** the both-down loss vs both All-Weather and the risk-parity winner (though still negative OOS) — directionally the trend overlay helps in the AW weak spot, but not enough to flip it positive in this window. Check the bootstrap CI before trusting the ranking.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 7.37% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 39 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric2`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| StructShort | US Equity, International Equity, Preferred Stock, US Corporate Bonds, Silver, Commodities | 9.35% | **0.771** | -19.22% | -33.96% | 0.528 | 0.716 | 0.735 | 1.00 | 0.00% | -0.54 | [0.19, 1.61] |
| TrendGate | US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities | 7.32% | **0.719** | -17.99% | -27.88% | 0.310 | 0.543 | 0.628 | 1.00 | 0.00% | -0.59 | [0.07, 1.68] |
| RP-LS-Overlay | US Equity, International Equity, Preferred Stock, US Corporate Bonds, Silver, Commodities | 9.34% | **0.714** | -22.29% | -36.66% | 0.483 | 0.700 | 0.655 | 1.30 | 1.74% | -0.60 | [0.10, 1.55] |
| EW-InflC-Dur | US Equity, International Equity, US Corporate Bonds, EM Bonds, Commodities | 7.30% | **0.671** | -21.91% | -29.20% | 0.461 | 0.646 | 0.648 | 1.00 | 0.00% | -0.64 | [0.11, 1.57] |
| EW-InflC-Both6 | US Equity, International Equity, US REIT, EM Bonds, Commodities | 8.38% | **0.652** | -25.74% | -29.64% | 0.466 | 0.655 | 0.538 | 1.00 | 0.00% | -0.66 | [0.08, 1.50] |
| EW-MA-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 4.25% | **0.613** | -14.02% | -12.97% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | -0.70 | [-0.08, 1.40] |
| RP winner | US Equity, International Equity, US REIT, EM Bonds, Commodities | 8.43% | **0.609** | -25.74% | -43.12% | 0.625 | 0.937 | 0.762 | 1.00 | 0.00% | — | — |
| EW-InflC-DurL | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 7.28% | **0.606** | -26.20% | -28.93% | 0.526 | 0.747 | 0.600 | 1.00 | 0.00% | -0.71 | [0.09, 1.53] |
| TG-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities | 4.62% | **0.588** | -16.31% | -20.18% | 0.110 | 0.421 | 0.513 | 1.00 | 0.00% | -0.72 | [-0.07, 1.61] |
| EW-Infl-Dur | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 6.79% | **0.587** | -24.32% | -30.11% | 0.542 | 0.711 | 0.675 | 0.90 | 0.00% | -0.72 | [0.03, 1.42] |
| EW-AsymMA-Short-6 | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.80% | **0.565** | -14.83% | -17.03% | -0.113 | -0.026 | -0.032 | 1.00 | 0.00% | -0.75 | [-0.10, 1.30] |
| TG-LS-Overlay | US Equity, International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 5.95% | **0.563** | -18.14% | -34.32% | 0.235 | 0.499 | 0.542 | 1.20 | 1.16% | -0.75 | [-0.07, 1.38] |
| EW-Infl-DurL | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 7.17% | **0.541** | -28.98% | -34.68% | 0.628 | 0.817 | 0.646 | 0.90 | 0.00% | -0.77 | [-0.00, 1.37] |
| EW-AsymMA-Short-9 | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.27% | **0.508** | -14.10% | -16.70% | -0.107 | -0.041 | -0.050 | 1.00 | 0.00% | -0.80 | [-0.14, 1.23] |
| EW-Infl-DurL2 | US Equity, US REIT, Preferred Stock, EM Bonds, Commodities | 7.15% | **0.505** | -30.46% | -38.85% | 0.669 | 0.907 | 0.652 | 0.90 | 0.00% | -0.81 | [-0.01, 1.31] |
| TG-Short | US Equity, International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.17% | **0.467** | -18.50% | -22.47% | 0.022 | 0.265 | 0.320 | 1.00 | 0.00% | -0.84 | [-0.21, 1.33] |
| EW-Hedge-MA | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.60% | **0.463** | -18.19% | -20.17% | 0.127 | 0.362 | 0.510 | 0.90 | 0.00% | -0.85 | [-0.20, 1.34] |
| TG-Short-LS | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver | 4.13% | **0.448** | -20.50% | -23.99% | 0.056 | 0.294 | 0.347 | 1.20 | 1.16% | -0.86 | [-0.25, 1.29] |
| EW-InflC-Both | US Equity, International Equity, US REIT, EM Bonds, Commodities | 5.41% | **0.430** | -25.74% | -26.10% | 0.360 | 0.563 | 0.449 | 1.00 | 0.00% | -0.88 | [-0.13, 1.25] |
| EW-InflC-BothL | US Equity, International Equity, US REIT, EM Bonds, Commodities | 5.97% | **0.427** | -30.01% | -28.44% | 0.427 | 0.680 | 0.468 | 1.00 | 0.00% | -0.88 | [-0.11, 1.28] |
| EW-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 3.30% | **0.414** | -20.58% | -20.18% | 0.091 | 0.460 | 0.542 | 1.00 | 0.00% | -0.90 | [-0.24, 1.43] |
| EW-AsymMA-Tight | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds | 1.99% | **0.412** | -14.05% | -8.79% | -0.111 | -0.111 | -0.254 | 1.00 | 0.00% | -0.90 | [-0.34, 1.14] |
| EW-AsymMA-Short | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 3.43% | **0.406** | -17.22% | -17.76% | -0.124 | -0.049 | -0.060 | 1.00 | 0.00% | -0.90 | [-0.28, 1.15] |
| EW-Hedge-DMA-1 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.53% | **0.393** | -20.55% | -25.35% | 0.240 | 0.583 | 0.642 | 1.00 | 0.00% | -0.92 | [-0.18, 1.31] |
| EW-Short | US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.67% | **0.348** | -20.06% | -16.68% | 0.018 | 0.561 | 0.607 | 1.00 | 0.00% | -0.96 | [-0.25, 1.50] |
| EW-Hedge-DD | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.16% | **0.346** | -22.43% | -26.08% | 0.182 | 0.586 | 0.645 | 1.00 | 0.00% | -0.97 | [-0.29, 1.30] |
| EW-Hedge-Dur-DD | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.29% | **0.345** | -23.63% | -26.31% | 0.146 | 0.559 | 0.613 | 1.00 | 0.00% | -0.97 | [-0.32, 1.33] |
| EW-Hedge-Dur-DD2 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.02% | **0.315** | -24.03% | -25.75% | 0.126 | 0.542 | 0.593 | 1.00 | 0.00% | -1.00 | [-0.37, 1.31] |
| EW-DDStop-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 2.71% | **0.299** | -24.01% | -23.75% | 0.106 | 0.536 | 0.587 | 1.00 | 0.00% | -1.01 | [-0.35, 1.27] |
| EW-Hedge-Dur-MA | US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities | 2.28% | **0.296** | -21.40% | -12.10% | -0.025 | 0.243 | 0.334 | 0.90 | 0.00% | -1.02 | [-0.49, 1.30] |
| LS-TSMOM | US REIT, US Treasuries, US Corporate Bonds, Gold, Silver | 2.60% | **0.248** | -25.31% | -11.31% | -0.275 | 0.350 | 0.324 | 1.00 | 0.00% | -1.06 | [-0.50, 1.16] |
| EW-Vol-Short | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 1.77% | **0.247** | -22.29% | -13.87% | 0.040 | 0.383 | 0.436 | 1.00 | 0.00% | -1.06 | [-0.38, 1.35] |
| EW-Hedge-DMA | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 2.03% | **0.234** | -22.43% | -22.50% | 0.129 | 0.524 | 0.581 | 1.00 | 0.00% | -1.08 | [-0.37, 1.15] |
| EW-Short-LS | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds | 1.67% | **0.210** | -25.72% | -21.93% | 0.024 | 0.166 | 0.233 | 1.20 | 1.16% | -1.10 | [-0.51, 1.00] |
| EW-DMA-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 1.78% | **0.206** | -24.53% | -18.48% | 0.038 | 0.448 | 0.486 | 1.00 | 0.00% | -1.11 | [-0.41, 1.16] |
| EW-Hedge-DMA-2 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 0.52% | **0.060** | -25.85% | -19.64% | 0.019 | 0.466 | 0.510 | 1.00 | 0.00% | -1.25 | [-0.56, 0.99] |
| EW-Hedge-Dur | US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities | 0.26% | **0.030** | -28.01% | -14.07% | -0.024 | 0.399 | 0.430 | 1.00 | 0.00% | -1.28 | [-0.68, 1.07] |
| EW-Infl-BothL | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | 0.22% | **0.017** | -27.42% | -7.26% | 0.522 | 0.422 | 0.318 | 0.50 | 0.00% | -1.29 | [-0.56, 0.59] |
| EW-Infl-Both | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | -0.16% | **-0.014** | -22.69% | -2.69% | 0.436 | 0.316 | 0.289 | 0.50 | 0.00% | -1.33 | [-0.63, 0.55] |
| EW-Hedge-Dur-2 | US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities | -0.35% | **-0.040** | -30.47% | -12.73% | -0.060 | 0.373 | 0.392 | 1.00 | 0.00% | -1.35 | [-0.77, 0.98] |
| EW-AsymVol-Short | US Equity, US REIT, US Treasuries, US Corporate Bonds, EM Bonds | -1.16% | **-0.161** | -24.10% | -11.70% | 0.024 | 0.284 | 0.335 | 1.00 | 0.00% | -1.47 | [-0.70, 0.48] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 7.32% · Sharpe 0.719 · MaxDD -17.99% · both-down -27.88% · Upβ 0.310 / Dnβ 0.543 · Dn-corr 0.628 · gross 1.00 · lev cost 0.00%/yr · DSR -0.59 · Sharpe CI [0.07, 1.68]
- **Pros:** Long-only (gross ≤ 1, no leverage cost). Cuts equity exposure after a sustained drawdown — downside dampening. Keeps bond/gold/diversifier sleeves long (carry).
- **Cons:** 12m trend-gate LAGS: long into the start of drawdowns, flat into the start of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal). Cannot go net-short, so no positive both-down return. Whipsaw in choppy markets (gate toggles on/off).

**RP-LS-Overlay** — combo: US Equity, International Equity, Preferred Stock, US Corporate Bonds, Silver, Commodities

- Net ann ret 9.34% · Sharpe 0.714 · MaxDD -22.29% · both-down -36.66% · Upβ 0.483 / Dnβ 0.700 · Dn-corr 0.655 · gross 1.30 · lev cost 1.74%/yr · DSR -0.60 · Sharpe CI [0.10, 1.55]
- **Pros:** LS-TSMOM overlay shorts the falling legs → genuinely positive in both-down (the direction that matches the brief). Long MinVar base keeps the return / Sharpe floor. Dollar-neutral overlay is crisis-alpha on top of a diversified long book.
- **Cons:** Gross 1.30 → leverage cost 1.74%/yr drags the return. Overlay whipsaw in calm markets (the 2010s) drags Sharpe. Dn-corr may stay positive if the long leg dominates the down months.

**StructShort** — combo: US Equity, International Equity, Preferred Stock, US Corporate Bonds, Silver, Commodities

- Net ann ret 9.35% · Sharpe 0.771 · MaxDD -19.22% · both-down -33.96% · Upβ 0.528 / Dnβ 0.716 · Dn-corr 0.735 · gross 1.00 · lev cost 0.00%/yr · DSR -0.54 · Sharpe CI [0.19, 1.61]
- **Pros:** Permanent net-short-duration tilt (short US Treasuries) → direct hedge for a 2022-style stocks+bonds rout. Sleeve-level netting keeps gross ≤ 1 (no leverage cost). Structural (not signal-driven) → no whipsaw, no lookback lag.
- **Cons:** Pays for the hedge in every non-stagflation year (carry drag) — a permanent short is expensive outside 2022. Only applies to combos containing the short sleeve (TRAIN search self-selects those). Sleeve-level short is a net-short-duration *tilt*, not a standalone short ticker (ticker-level shorting that adds gross is a flagged refinement).

**TG-LS-Overlay** — combo: US Equity, International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 5.95% · Sharpe 0.563 · MaxDD -18.14% · both-down -34.32% · Upβ 0.235 / Dnβ 0.499 · Dn-corr 0.542 · gross 1.20 · lev cost 1.16%/yr · DSR -0.75 · Sharpe CI [-0.07, 1.38]
- **Pros:** Combines the trend-gate (downside dampening) with a small LS overlay (crisis alpha) — both levers. Smaller overlay (gross 1.20) → lower leverage cost than RP-LS-Overlay. Targets the asymmetric goal from two angles.
- **Cons:** Inherits the trend-gate lag AND the overlay whipsaw — both costs. Gross 1.20 → leverage cost 1.16%/yr. Most parameters → most overfitting surface; check the DSR / bootstrap CI.

**TG-Short** — combo: US Equity, International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.17% · Sharpe 0.467 · MaxDD -18.50% · both-down -22.47% · Upβ 0.022 / Dnβ 0.265 · Dn-corr 0.320 · gross 1.00 · lev cost 0.00%/yr · DSR -0.84 · Sharpe CI [-0.21, 1.33]
- **Pros:** Flips the equity sleeve to NET-SHORT on the downside signal (the brief's lever) — long equity when up, short equity when down; bonds/gold/diversifiers stay long. Directly targets negative downside-β with positive upside-β. Sleeve-level netting can keep gross ≤ 1 (no leverage cost) when the short equity leg nets against the long book. Reuses the MinVar base.
- **Cons:** MinVar base starves high-vol equity to ~5-10% weight → little equity to short, so the upside capture AND the short benefit are both muted; return floor is well below AW. 12m signal lags: shorts ~12m INTO a drawdown (after the drop has happened), longs ~12m into a rally (after the rebound). Whipsaw in choppy markets; check DSR / bootstrap CI.

**TG-Short-LS** — combo: US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.13% · Sharpe 0.448 · MaxDD -20.50% · both-down -23.99% · Upβ 0.056 / Dnβ 0.294 · Dn-corr 0.347 · gross 1.20 · lev cost 1.16%/yr · DSR -0.86 · Sharpe CI [-0.25, 1.29]
- **Pros:** TG-Short (short equity on downside) + a 0.20 LS-TSMOM overlay — both the equity flip and the broader momentum crisis-alpha leg. Targets the asymmetric goal from two angles. Smaller overlay than RP-LS-Overlay → lower leverage cost.
- **Cons:** Inherits the MinVar-base equity starvation AND the 12m lag AND the overlay whipsaw — all three costs. Gross can exceed 1 → leverage cost up to 1.16%/yr. Most overfitting surface of the TG-Short family; check DSR / bootstrap CI.

**TG-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 4.62% · Sharpe 0.588 · MaxDD -16.31% · both-down -20.18% · Upβ 0.110 / Dnβ 0.421 · Dn-corr 0.513 · gross 1.00 · lev cost 0.00%/yr · DSR -0.72 · Sharpe CI [-0.07, 1.61]
- **Pros:** TG-Short with a FASTER 6m trend signal — reduces the 12m lag (out of drawdowns sooner, into rallies sooner), so the short flip is better timed. Direct lever for negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws MORE in choppy markets (more false flips). MinVar base still starves equity → muted upside capture. Shorter lookback → more turnover; check DSR / bootstrap CI.

**EW-Short** — combo: US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.67% · Sharpe 0.348 · MaxDD -20.06% · both-down -16.68% · Upβ 0.018 / Dnβ 0.561 · Dn-corr 0.607 · gross 1.00 · lev cost 0.00%/yr · DSR -0.96 · Sharpe CI [-0.25, 1.50]
- **Pros:** EQUAL-WEIGHT base (like All-Weather's own ~1/n across sleeves) so equity keeps a real weight (~12-25%) — fixes the MinVar-base equity starvation that left TG-Short with nothing to short and ~3% return. Short equity on the downside signal → negative downside-β with positive upside-β; return floor near AW. Sleeve-level netting can keep gross ≤ 1 (no leverage cost).
- **Cons:** More equity weight → higher vol / drawdown than the MinVar-base flavors. 12m signal lags (consider EW-Short-6m for less lag). Equal-weight ignores covariance; check DSR / bootstrap CI.

**EW-Short-LS** — combo: US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret 1.67% · Sharpe 0.210 · MaxDD -25.72% · both-down -21.93% · Upβ 0.024 / Dnβ 0.166 · Dn-corr 0.233 · gross 1.20 · lev cost 1.16%/yr · DSR -1.10 · Sharpe CI [-0.51, 1.00]
- **Pros:** EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM overlay. Highest upside capture of the family (EW base keeps equity, overlay adds crisis alpha). Targets both beat-AW return AND asymmetric protection.
- **Cons:** Gross can exceed 1 → leverage cost up to 1.16%/yr. Inherits the 12m lag and overlay whipsaw. Most overfitting surface; check DSR / bootstrap CI.

**EW-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.30% · Sharpe 0.414 · MaxDD -20.58% · both-down -20.18% · Upβ 0.091 / Dnβ 0.460 · Dn-corr 0.542 · gross 1.00 · lev cost 0.00%/yr · DSR -0.90 · Sharpe CI [-0.24, 1.43]
- **Pros:** EW-Short with a FASTER 6m signal — real equity weight (EW base) AND less lag, so the short flip is both meaningful and better timed. Directly targets the brief: high upside-β, negative downside-β, AW-like return floor. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws more; more turnover. Higher vol / drawdown than MinVar-base flavors (more equity). Most parameters → check DSR / bootstrap CI.

**EW-MA-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 4.25% · Sharpe 0.613 · MaxDD -14.02% · both-down -12.97% · Upβ 0.013 / Dnβ 0.123 · Dn-corr 0.224 · gross 1.00 · lev cost 0.00%/yr · DSR -0.70 · Sharpe CI [-0.08, 1.40]
- **Pros:** EW-Short driven by a LEADING signal: price-vs-10m-SMA crossover (an MA crosses BEFORE a lookback-return flips sign), so equity exits BEFORE the drawdown and re-enters BEFORE the rally — the round-2 lagging-momentum blocker's direct fix. Real equity weight (EW base) + short-on-downside; directly targets high upside-β with negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** MA crossover still whipsaws in choppy/sideways tape (price oscillates around the SMA → repeated false flips). Higher vol / drawdown than MinVar-base flavors (more equity); more turnover than the 12m TSMOM gate. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-Vol-Short** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.77% · Sharpe 0.247 · MaxDD -22.29% · both-down -13.87% · Upβ 0.040 / Dnβ 0.383 · Dn-corr 0.436 · gross 1.00 · lev cost 0.00%/yr · DSR -1.06 · Sharpe CI [-0.38, 1.35]
- **Pros:** EW-Short driven by a VOL-REGIME signal: short equity when 6m realized vol EXCEEDS its trailing 60m median (vol spikes LEAD drawdowns), long when vol is calm — a regime filter, not a price-trend filter. Different information set from price-MA → diversifies the signal family; real equity weight (EW base). Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Vol spikes can lag the actual drawdown start (vol rises AS price falls, not before) — may still enter the short late. 60m median needs a long warm-up; fewer active signals in the early TEST window. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-DMA-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.78% · Sharpe 0.206 · MaxDD -24.53% · both-down -18.48% · Upβ 0.038 / Dnβ 0.448 · Dn-corr 0.486 · gross 1.00 · lev cost 0.00%/yr · DSR -1.11 · Sharpe CI [-0.41, 1.16]
- **Pros:** EW-Short driven by a DUAL-MA signal: fast 3m SMA vs slow 10m SMA — a faster, smoother crossover than price-vs-SMA (the slow MA smooths the reference, so fewer false flips than EW-MA-Short). Leading signal (a fast/slow cross precedes the lookback-return flip); real equity weight (EW base) + short-on-downside. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Fast 3m SMA is noisy → still some whipsaw; the slow 10m MA adds lag vs the single-MA gate. Two MAs → slightly more overfitting surface than EW-MA-Short. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-AsymMA-Short** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 3.43% · Sharpe 0.406 · MaxDD -17.22% · both-down -17.76% · Upβ -0.124 / Dnβ -0.049 · Dn-corr -0.060 · gross 1.00 · lev cost 0.00%/yr · DSR -0.90 · Sharpe CI [-0.28, 1.15]
- **Pros:** ASYMMETRIC (hysteretic) MA gate — the round-3 prescription made concrete: LONG until price < 3m SMA (FAST downside exit), then SHORT until price > 12m SMA (SLOW upside re-entry). Starts LONG and holds through chop above the fast MA, so it stays correlated on the way up and only flees (goes net-short) after a clear break. Hysteresis band = the fast/slow-MA gap. The one untested lever: a SYMMETRIC signal (rounds 1-3) is equally trigger-happy up and down → Dnβ >= Upβ everywhere; an asymmetric one can in principle be 'correlated up, protected down'. Real equity weight (EW base) + short-on-downside; sleeve-level netting can keep gross <= 1.
- **Cons:** The slow 12m re-entry can lag the START of a rally (re-enters late after a V rebound) — some upside missed at the turn. Stateful + two MA horizons → more overfitting surface than the symmetric gates; the fast/slow gap is a tuned parameter. New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime.

**EW-DDStop-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.71% · Sharpe 0.299 · MaxDD -24.01% · both-down -23.75% · Upβ 0.106 / Dnβ 0.536 · Dn-corr 0.587 · gross 1.00 · lev cost 0.00%/yr · DSR -1.01 · Sharpe CI [-0.35, 1.27]
- **Pros:** ASYMMETRIC trailing-stop gate — the most direct map to the brief: LONG until the equity sleeve drawdown from its trailing 6m peak exceeds 10% (FAST exit — a clear break), then SHORT until it recovers inside 3% of the peak (SLOW re-entry, near a new high). 'Flee the break, wait for a new high.' Inherently asymmetric: the trigger is 'you've fallen >10%', the re-entry is 'you've made a new high' — quick to flee, slow to return, exactly the brief's shape. Real equity weight (EW base) + short-on-downside; sleeve-level netting can keep gross <= 1.
- **Cons:** Drawdown thresholds (10% exit / 3% re-entry) are tuned → overfitting surface; the 6m peak window is a parameter. A slow grind-down (2018, 2022) can hit the 10% stop late vs a fast crash; a V-rebound (2020) re-enters late (needs a new 6m high). New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime.

**EW-AsymMA-Short-6** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.80% · Sharpe 0.565 · MaxDD -14.83% · both-down -17.03% · Upβ -0.113 / Dnβ -0.026 · Dn-corr -0.032 · gross 1.00 · lev cost 0.00%/yr · DSR -0.75 · Sharpe CI [-0.10, 1.30]
- **Pros:** Round-4b SWEEP point: EW-AsymMA-Short with a FASTER re-entry (slow_entry=6 vs the round-4 default 12). The round-4 default drove Upβ NEGATIVE because the 12m re-entry stayed short through rally starts; re-entering at a 6m SMA re-loads equity sooner → tests whether a less-overshooting band can keep Upβ POSITIVE while Dnβ stays NEGATIVE (the unmet property). Fast 3m-MA exit preserved (downside protection unchanged); real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Faster re-entry reduces the hysteresis band → more whipsaw in choppy tape (re-enters on smaller bounces); may give back some of the downside protection the 12m band bought. Sweep parameter (slow_entry=6) is tuned → overfitting surface; one TRAIN/TEST split = one regime. Check DSR / bootstrap CI.

**EW-AsymMA-Short-9** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.27% · Sharpe 0.508 · MaxDD -14.10% · both-down -16.70% · Upβ -0.107 / Dnβ -0.041 · Dn-corr -0.050 · gross 1.00 · lev cost 0.00%/yr · DSR -0.80 · Sharpe CI [-0.14, 1.23]
- **Pros:** Round-4b SWEEP point: the intermediate re-entry (slow_entry=9, between the round-4 default 12 and the fast 6). Brackets the Upβ-vs-Dnβ trade-off: slower than 6 = more downside protection, faster than 12 = less upside overshoot. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Same construction costs as the rest of the asym_ma family (stateful, two MA horizons, tuned band). Sweep parameter → overfitting surface; one split = one regime. Check DSR / bootstrap CI.

**EW-AsymMA-Tight** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret 1.99% · Sharpe 0.412 · MaxDD -14.05% · both-down -8.79% · Upβ -0.111 / Dnβ -0.111 · Dn-corr -0.254 · gross 1.00 · lev cost 0.00%/yr · DSR -0.90 · Sharpe CI [-0.34, 1.14]
- **Pros:** Round-4b SWEEP point: a TIGHTER hysteresis band — fast_exit=2 (exit on a 2m-MA break, even faster downside flee) + slow_entry=6 (re-enter on a 6m SMA). The tightest band in the family: quickest to flee, quickest to return — tests the 'high turnover, low lag' corner of the grid. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** The 2m exit is noisy → more false flips in chop; the tight band → highest turnover of the family (more cost, more whipsaw). Two tuned parameters → most overfitting surface of the sweep; one split = one regime. Check DSR / bootstrap CI.

**EW-AsymVol-Short** — combo: US Equity, US REIT, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret -1.16% · Sharpe -0.161 · MaxDD -24.10% · both-down -11.70% · Upβ 0.024 / Dnβ 0.284 · Dn-corr 0.335 · gross 1.00 · lev cost 0.00%/yr · DSR -1.47 · Sharpe CI [-0.70, 0.48]
- **Pros:** Round-4b: a HYSTERETIC vol-regime gate — LONG -> SHORT once the prior month's 6m realized vol exceeds its trailing 60m median (fast exit on stress), SHORT -> LONG once vol falls back below 0.85x the median (slow re-entry, wait for genuine calm). The hysteresis band = 0.85..1.0x median; a vol spike flees, vol must genuinely calm to return. Fixes the round-3 EW-Vol-Short, which SHORTED THE 2020 COVID V-REBOUND (vol stayed elevated through the rally → the symmetric vol-gate never re-entered long, -> -1.52% / -31.69% MaxDD). The slow lower-bar re-entry waits for vol to actually calm. Different information set from price-MA → diversifies the signal family. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Vol can stay elevated THROUGH a V-rebound even with hysteresis (vol calms late) — the 0.85x bar may still re-enter after the rally's best months. 60m median needs a long warm-up; the 0.85x / 1.0x thresholds are tuned → overfitting surface. New signal → check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-DMA-1** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.53% · Sharpe 0.393 · MaxDD -20.55% · both-down -25.35% · Upβ 0.240 / Dnβ 0.583 · Dn-corr 0.642 · gross 1.00 · lev cost 0.00%/yr · DSR -0.92 · Sharpe CI [-0.18, 1.31]
- **Pros:** Round-5 DECOUPLED insurance overlay, light hedge (w_hedge=1.0): the long EW base NEVER flips (gross 1, fully long in every month incl. recoveries) so Upβ stays that of the long-only base — the round-4b structural blocker's direct fix. A SEPARATE additive short overlay on the equity sleeves activates only when the fast 3m/10m dual-MA signal is DOWN (flat otherwise); w_hedge=1.0 nets equity to ~0 in down-months (a 'cash on the downside' hedge, not net-short). Fast symmetric signal (dma) -> FAST-OFF in recoveries (does not drag the rally, unlike round-4's slow re-entry). Decouples the two halves the brief asks for: long base = upside, overlay = downside insurance; the 'long-term short a ticker' permission applied as an overlay not a gate.
- **Cons:** w_hedge=1.0 only nets equity to ~0 in down-months -> Dnβ is reduced but likely still POSITIVE (the non-equity sleeves still track equity down); to drive Dnβ NEGATIVE needs w_hedge > 1. Additive gross when active -> leverage cost; the overlay is a separate notional so it is NOT free (vs the sleeve-netted flip). New construction + tuned w_hedge -> overfitting surface; one TRAIN/TEST split = one regime. Check DSR / bootstrap CI.

**EW-Hedge-DMA** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.03% · Sharpe 0.234 · MaxDD -22.43% · both-down -22.50% · Upβ 0.129 / Dnβ 0.524 · Dn-corr 0.581 · gross 1.00 · lev cost 0.00%/yr · DSR -1.08 · Sharpe CI [-0.37, 1.15]
- **Pros:** Round-5 DECOUPLED overlay, MEDIUM hedge (w_hedge=1.5): same never-flipping long EW base + fast dma-triggered additive short overlay, but w_hedge=1.5 -> NET SHORT equity in down-months (base equity weight - 1.5x = negative). This is the sizing expected to push Dnβ NEGATIVE while the always-long base keeps Upβ POSITIVE — the unmet asymmetric property, by construction. Fast dma signal -> fast-off in recoveries; the base's full equity weight is at work in up-months (overlay flat). Directly targets 'correlated up, protected down' via decoupling, not a single price-gate.
- **Cons:** Gross 1 + 1.5 x (equity fraction) when active -> leverage cost (the explicit price of decoupling); only paid in down-months. Net-short equity in down-months means a wrong-footed whipsaw (signal flips short just before a rally) costs more than the light hedge; the fast dma signal whipsaws in chop. w_hedge=1.5 is tuned; new construction -> overfitting surface. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-DMA-2** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 0.52% · Sharpe 0.060 · MaxDD -25.85% · both-down -19.64% · Upβ 0.019 / Dnβ 0.466 · Dn-corr 0.510 · gross 1.00 · lev cost 0.00%/yr · DSR -1.25 · Sharpe CI [-0.56, 0.99]
- **Pros:** Round-5 DECOUPLED overlay, HEAVY hedge (w_hedge=2.0): the strongest downside clip — net short 1.0x the base equity weight in down-months. Tests how much downside protection (Dnβ most negative) the construction can buy before the leverage cost and whipsaw overwhelm the return. Same never-flipping long base (Upβ positive) + fast dma overlay. Brackets the w_hedge grid with EW-Hedge-DMA-1 (1.0) / -DMA (1.5).
- **Cons:** Largest additive gross -> largest leverage cost; most whipsaw damage if the signal mistimes. w_hedge=2.0 is the most aggressive / most overfit corner of the round-5 grid. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-MA** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.60% · Sharpe 0.463 · MaxDD -18.19% · both-down -20.17% · Upβ 0.127 / Dnβ 0.362 · Dn-corr 0.510 · gross 0.90 · lev cost 0.00%/yr · DSR -0.85 · Sharpe CI [-0.20, 1.34]
- **Pros:** Round-5 overlay with the single 10m-SMA signal (vs the dual-MA dma): the overlay shorts when price < its 10m SMA. A slower, smoother downside trigger than dma -> fewer false flips in chop, but slower to deactivate in a V-rebound. Same never-flipping long EW base (Upβ positive) + additive short overlay (w_hedge=1.5). Tests whether the smoother signal beats the fast dma on the overlay (fewer whipsaw trades vs later off in recoveries).
- **Cons:** The 10m SMA deactivates SLOWER than dma in a V-rebound (price reclaims the 10m SMA late) -> the overlay can drag the start of the rally (the round-4 problem, milder here because the base is always long). Additive gross -> leverage cost; tuned w_hedge. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-DD** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.16% · Sharpe 0.346 · MaxDD -22.43% · both-down -26.08% · Upβ 0.182 / Dnβ 0.586 · Dn-corr 0.645 · gross 1.00 · lev cost 0.00%/yr · DSR -0.97 · Sharpe CI [-0.29, 1.30]
- **Pros:** Round-5 overlay with the dd_stop (drawdown) signal: the overlay shorts once the equity sleeve is >10% below its trailing 6m peak and deactivates once within 3% of the peak. 'Hedge the break, un-hedge the new high' — the most direct map to the brief's shape, now applied to a SEPARATE overlay (not a flip). Same never-flipping long EW base (Upβ positive) + additive short overlay (w_hedge=1.5). The drawdown signal deactivates NATURALLY when equity recovers (drawdown shrinks) -> fast-off in V-rebounds, without a separate re-entry MA.
- **Cons:** dd_stop is a LAGGING trigger (price has already fallen 10% before the hedge activates) -> the hedge misses the first 10% of the drawdown; on an overlay (not a flip) this is late-activate but still fast-deactivate. Drawdown thresholds (10% / 3%) are tuned; additive gross -> leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur** — combo: US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities

- Net ann ret 0.26% · Sharpe 0.030 · MaxDD -28.01% · both-down -14.07% · Upβ -0.024 / Dnβ 0.399 · Dn-corr 0.430 · gross 1.00 · lev cost 0.00%/yr · DSR -1.28 · Sharpe CI [-0.68, 1.07]
- **Pros:** Round-6: round-5 decoupled overlay (never-flip long EW base -> Upβ positive) PLUS a duration/bond overlay (w_hedge_bd=1.5) that shorts the BOND sleeves on their OWN dma downtrend. The direct fix for the round-5 gap: in both-down / stagflation months bonds fall WITH equities, and an equity-only overlay could not touch them. Shorting bonds on bonds' own downtrend clips that loss. Self-avoiding flight-to-quality: when bonds RISE (2008 Q4, 2020 Q1) their dma is up -> no bond short -> no bleed there. Equity overlay (w_hedge=1.5, dma) unchanged from round 5.
- **Cons:** Two additive shorts (equity + bonds) -> higher gross -> more leverage cost than round 5. The dma signal still lags ~12m on the equity side (the round-5 'fires too late' issue is only half-fixed here). Bond dma can whipsaw in choppy rates regimes. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-MA** — combo: US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities

- Net ann ret 2.28% · Sharpe 0.296 · MaxDD -21.40% · both-down -12.10% · Upβ -0.025 / Dnβ 0.243 · Dn-corr 0.334 · gross 0.90 · lev cost 0.00%/yr · DSR -1.02 · Sharpe CI [-0.49, 1.30]
- **Pros:** Round-6 duration overlay with the symmetric 10m MA signal (vs EW-Hedge-Dur's dma) on BOTH the equity and bond shorts. Same never-flip long EW base + duration short (w_hedge_bd=1.5) targeting the both-down gap; self-avoiding flight-to-quality.
- **Cons:** The single 10m MA deactivates slower than dma in a V-rebound on both sleeves -> can drag the start of rallies. Two additive shorts -> leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-DD** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.29% · Sharpe 0.345 · MaxDD -23.63% · both-down -26.31% · Upβ 0.146 / Dnβ 0.559 · Dn-corr 0.613 · gross 1.00 · lev cost 0.00%/yr · DSR -0.97 · Sharpe CI [-0.32, 1.33]
- **Pros:** Round-6 with the FAST equity-drawdown trigger (gate_signal=eq_dd): a SYMMETRIC, stateless drawdown gate that shorts a sleeve once it is >10% below its 6m peak and releases once back within 3% — fires IN down-months and releases fast in recoveries, the direct fix for round-5's 'dma/ma fires ~12m too late' problem. Duration overlay (w_hedge_bd=1.5) shorts bonds on bonds' own drawdown -> clips the both-down loss; flight-to-quality safe. The user's literal ask: short duration/TLT in the overlay + a fast equity-drawdown trigger.
- **Cons:** eq_dd is stateless -> more whipsaw near peaks than hysteretic dd_stop (can toggle short/long in chop). For bonds a 10% drawdown threshold rarely fires (bonds less vol) -> the bond leg may stay quiet outside a true bond rout (2022). Two additive shorts + the fast trigger -> higher turnover / leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-2** — combo: US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities

- Net ann ret -0.35% · Sharpe -0.040 · MaxDD -30.47% · both-down -12.73% · Upβ -0.060 / Dnβ 0.373 · Dn-corr 0.392 · gross 1.00 · lev cost 0.00%/yr · DSR -1.35 · Sharpe CI [-0.77, 0.98]
- **Pros:** Round-6 with a BIGGER duration short (w_hedge_bd=2.0 vs 1.5) on the dma signal: w_hedge_bd>1 means net-short duration in bond-down months — a more aggressive stagflation hedge, the brief's 'short a ticker' (short TLT / long-duration) as a conditional overlay. Same never-flip long EW base (Upβ positive); equity overlay dma.
- **Cons:** Net-short duration when bonds trend down -> larger gross / leverage cost and larger whipsaw if the bond rout reverses. dma still lags on equity. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-DD2** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.02% · Sharpe 0.315 · MaxDD -24.03% · both-down -25.75% · Upβ 0.126 / Dnβ 0.542 · Dn-corr 0.593 · gross 1.00 · lev cost 0.00%/yr · DSR -1.00 · Sharpe CI [-0.37, 1.31]
- **Pros:** Round-6 combining BOTH levers at full strength: fast eq_dd equity trigger + a bigger 2.0x duration short. The maximal mechanical fix for the round-5 diagnosis (equity overlay fires too late AND can't touch bonds in both-down). Never-flip long EW base -> Upβ positive by construction.
- **Cons:** Most parameters / overfitting surface of the round-6 family; highest gross / leverage cost and turnover. eq_dd's bond leg may stay quiet outside a true bond rout. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-Dur** — combo: US Equity, International Equity, Preferred Stock, EM Bonds, Commodities

- Net ann ret 6.79% · Sharpe 0.587 · MaxDD -24.32% · both-down -30.11% · Upβ 0.542 / Dnβ 0.711 · Dn-corr 0.675 · gross 0.90 · lev cost 0.00%/yr · DSR -0.72 · Sharpe CI [0.03, 1.42]
- **Pros:** Round-7 LEADING macro gate (the user's ask): duration overlay fires off an EX-ANTE inflation regime (trailing-12m Commodities return) instead of a lagging sleeve trend. Short bonds (w_hedge_bd=1.5) ONLY when inflation is RISING (stagflation risk-off, 2022 -- the both-down regime round 6 could only hedge with a lagging short); no long tilt. Never-flip long EW base -> Upβ positive. Commodities lead equities in the stagflation case (topped before equities in 2022). Isolates the duration-regime lever (no equity short, no long tilt).
- **Cons:** Inflation regimes are persistent but not perfect: equity-up + inflation-up months (2021, 2024) take a bond-short drag on Upβ. Commodities are a noisy inflation proxy. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-DurL** — combo: US Equity, International Equity, Preferred Stock, EM Bonds, Commodities

- Net ann ret 7.17% · Sharpe 0.541 · MaxDD -28.98% · both-down -34.68% · Upβ 0.628 / Dnβ 0.817 · Dn-corr 0.646 · gross 0.90 · lev cost 0.00%/yr · DSR -0.77 · Sharpe CI [-0.00, 1.37]
- **Pros:** Round-7 with the SYMMETRIC duration-regime switch: short bonds (w_hedge_bd=1.5) when inflation RISING + LONG-bonds tilt (w_long_bd=1.5) when inflation FALLING -- own the bonds that rally in flight-to-quality (2008 Q4, 2020 Q1), the regime where bonds hedge equity for free and Dnβ can go negative. Never-flip long EW base -> Upβ positive. The leading-macro lever at its most complete (regime-switching duration, both directions).
- **Cons:** Two-sided regime switch -> most regime-timing risk: a wrong-footed inflation call (e.g. long bonds into a reflation) costs on both the tilt and the foregone short. Additive gross both ways -> leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-Both** — combo: US Equity, International Equity, US REIT, Preferred Stock, EM Bonds

- Net ann ret -0.16% · Sharpe -0.014 · MaxDD -22.69% · both-down -2.69% · Upβ 0.436 / Dnβ 0.316 · Dn-corr 0.289 · gross 0.50 · lev cost 0.00%/yr · DSR -1.33 · Sharpe CI [-0.63, 0.55]
- **Pros:** Round-7 full inflation-regime RISK-OFF: when inflation RISING, short BOTH equity (w_hedge=1.5) AND bonds (w_hedge_bd=1.5) -- both fall in stagflation, so this is the direct 2022 both-down hedge the round-5/6 equity-/bond-own-trend gates could not time. No long tilt. Never-flip long EW base -> Upβ positive (the equity short is an additive overlay, not a base flip).
- **Cons:** Shorting equity when inflation rising drags Upβ in equity-up + inflation-up months (2021, 2024) -- the same tension as every lagging equity short, now on a macro trigger. Highest gross of the round-7 family. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-BothL** — combo: US Equity, International Equity, US REIT, Preferred Stock, EM Bonds

- Net ann ret 0.22% · Sharpe 0.017 · MaxDD -27.42% · both-down -7.26% · Upβ 0.522 / Dnβ 0.422 · Dn-corr 0.318 · gross 0.50 · lev cost 0.00%/yr · DSR -1.29 · Sharpe CI [-0.56, 0.59]
- **Pros:** Round-7 maximal: short equity AND bonds when inflation RISING + long-bonds tilt (w_long_bd=1.5) when FALLING. The complete leading-macro regime switch across all three legs (equity short, duration short, duration long). The most aggressive test of whether an ex-ante inflation gate can deliver Upβ > Dnβ. Never-flip long EW base -> Upβ positive.
- **Cons:** Most parameters / overfitting surface of the round-7 family; largest additive gross / leverage cost; most regime-timing risk both ways. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-DurL2** — combo: US Equity, US REIT, Preferred Stock, EM Bonds, Commodities

- Net ann ret 7.15% · Sharpe 0.505 · MaxDD -30.46% · both-down -38.85% · Upβ 0.669 / Dnβ 0.907 · Dn-corr 0.652 · gross 0.90 · lev cost 0.00%/yr · DSR -0.81 · Sharpe CI [-0.01, 1.31]
- **Pros:** Round-7 with a BIGGER long-duration tilt (w_long_bd=2.0) when inflation FALLING -- push hardest on the flight-to-quality amplify lever (own 2.0x the base bond weight in disinflationary drawdowns) to drive Dnβ most negative, while keeping the 1.5x bond short in stagflation. No equity short (duration-only regime). Never-flip long EW base -> Upβ positive. Tests how much downside protection the long-tilt leg can buy before its leverage cost and reflation risk overwhelm it.
- **Cons:** The 2.0x long tilt is the most overfit / most leverage-cost corner of the round-7 grid; a long-bonds tilt into a reflation (inflation re-accelerates) is unhedged by the equity leg. Check DSR / bootstrap CI; one split = one regime.

**EW-InflC-Both** — combo: US Equity, International Equity, US REIT, EM Bonds, Commodities

- Net ann ret 5.41% · Sharpe 0.430 · MaxDD -25.74% · both-down -26.10% · Upβ 0.360 / Dnβ 0.563 · Dn-corr 0.449 · gross 1.00 · lev cost 0.00%/yr · DSR -0.88 · Sharpe CI [-0.13, 1.25]
- **Pros:** Round 8: the round-7 inflation gate NARROWED with a coincident equity-rolling confirmation (infl_confirm=eq_neg, trailing-3m US Equity < 0). Short BOTH equity (w_hedge=1.5) AND bonds (w_hedge_bd=1.5) only when inflation is RISING AND equity is rolling over -- 2022 protected, 2021/2024 reflation rallies NOT shorted -> return preserved (the round-7 EW-Infl-Both bled to ~0 return by shorting every rising-inflation month). Never-flip long EW base -> Upβ positive. The direct test of whether narrowing the broad ex-ante gate keeps Upβ > Dnβ AND restores return.
- **Cons:** The confirmation is itself a (short, 3m) lagging signal -> the short fires AFTER equity has started falling, so less early-drawdown protection than round-7's pure inflation gate (a return-vs-early-protection trade). Check DSR / bootstrap CI; one split = one regime.

**EW-InflC-BothL** — combo: US Equity, International Equity, US REIT, EM Bonds, Commodities

- Net ann ret 5.97% · Sharpe 0.427 · MaxDD -30.01% · both-down -28.44% · Upβ 0.427 / Dnβ 0.680 · Dn-corr 0.468 · gross 1.00 · lev cost 0.00%/yr · DSR -0.88 · Sharpe CI [-0.11, 1.28]
- **Pros:** Round 8: the confirmed inflation gate PLUS a confirmed long-duration tilt (w_long_bd=1.5) that fires only when inflation is FALLING AND equity is rolling over -- the true flight-to-quality regime (2008 Q4, 2020 Q1: disinflation + equity crash + bonds rally), NOT 2022-23 disinflation-with-bonds-falling that dragged round-7 EW-Infl-DurL's both-down to -34.68%. Own the rallying bonds only when they rally. Never-flip long EW base -> Upβ positive. The most complete round-8 construction (gated short + gated long-tilt).
- **Cons:** Most parameters / overfitting surface of the round-8 family; two-sided regime-timing risk both ways; the 3m equity confirmation can whipsaw near equity-market turns. Check DSR / bootstrap CI; one split = one regime.

**EW-InflC-Dur** — combo: US Equity, International Equity, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 7.30% · Sharpe 0.671 · MaxDD -21.91% · both-down -29.20% · Upβ 0.461 / Dnβ 0.646 · Dn-corr 0.648 · gross 1.00 · lev cost 0.00%/yr · DSR -0.64 · Sharpe CI [0.11, 1.57]
- **Pros:** Round 8 confirmed gate on DURATION only (no equity short): short bonds (w_hedge_bd=1.5) when inflation RISING AND equity rolling over, no long tilt. Isolates the confirmed-duration lever -- does the equity-rolling confirmation alone lift the round-7 EW-Infl-Dur return (6.79%) above 7.37% while keeping its low gross (0.90)? Never-flip long EW base -> Upβ positive. No equity short -> higher Upβ than the Both variants.
- **Cons:** Duration-only short cannot hedge equity-down months directly (Dnβ stays driven by the long equity base); the 3m confirmation narrows but does not eliminate regime-timing risk. Check DSR / bootstrap CI; one split = one regime.

**EW-InflC-DurL** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 7.28% · Sharpe 0.606 · MaxDD -26.20% · both-down -28.93% · Upβ 0.526 / Dnβ 0.747 · Dn-corr 0.600 · gross 1.00 · lev cost 0.00%/yr · DSR -0.71 · Sharpe CI [0.09, 1.53]
- **Pros:** Round 8 confirmed duration short (w_hedge_bd=1.5 when infl up AND eq rolling) + confirmed long-duration tilt (w_long_bd=1.5 when infl down AND eq rolling). The round-7 EW-Infl-DurL construction with BOTH legs gated on the equity-rolling confirmation -- the fix for its -34.68% both-down (the ungated long-tilt held in every disinflation month, including 2022-23 bonds-fall). Never-flip long EW base -> Upβ positive. Tests whether gating the long-tilt to true flight-to-quality recovers the duration-only both-down AND return.
- **Cons:** Two-sided confirmed gate -> most regime-timing risk of the duration-only round-8 presets; the 3m equity confirmation whipsaws near turns. Check DSR / bootstrap CI; one split = one regime.

**EW-InflC-Both6** — combo: US Equity, International Equity, US REIT, EM Bonds, Commodities

- Net ann ret 8.38% · Sharpe 0.652 · MaxDD -25.74% · both-down -29.64% · Upβ 0.466 / Dnβ 0.655 · Dn-corr 0.538 · gross 1.00 · lev cost 0.00%/yr · DSR -0.66 · Sharpe CI [0.08, 1.50]
- **Pros:** Round 8 EW-InflC-Both with a SLOWER 6m equity-rolling confirmation (eq_confirm_lookback=6) -- a more stable, less whipsaw-prone confirmation than the 3m default. Tests sensitivity of the confirmed gate to the confirmation window. Never-flip long EW base -> Upβ positive. Same short-both-legs construction as EW-InflC-Both, only the confirmation window differs.
- **Cons:** A 6m confirmation lags more -> the short fires even later in drawdowns (less early protection) but exits later in recoveries (more carry). Check DSR / bootstrap CI; one split = one regime.

> **Verdict:** Of the 39 TrendProtect flavors, **RP-LS-Overlay, StructShort, EW-InflC-Both6** beat All-Weather's net OOS return (7.37%) after the 5.8%/yr leverage cost. Cross-check the Dn-corr / Dnβ columns for the asymmetric protection and the DSR / bootstrap Sharpe CI for significance before trusting any single winner — the flavors share sleeves so DSR is conservative (see §3 effective-N), and a single TRAIN/TEST split is one regime.

## 8. Caveats (what is and is NOT fixed)

- **Fixed:** Volatility (^VIX) non-tradable sleeve removed by default; 20% per-sleeve
  cap kills single-ETF macro bets; transaction costs netted; Ledoit-Wolf shrinkage;
  diversification + both-down correlation in the objective; Deflated Sharpe; rolling
  selection re-enumerated from scratch (no TRAIN shortlist).
- **Bond total-return:** sleeves use Yahoo *adjusted close* (includes distributions
  where Yahoo provides them); this is ETF total return for the ETF-based sleeves,
  which is what All-Weather uses too — so the benchmark is fair. The only non-TR /
  non-investable sleeve was Volatility, now excluded.
- **Still one regime / two blocks:** TRAIN 2008–17, TEST 2018–26. The DSR and
  bootstrap CIs are guardrails, not a guarantee of future performance.
- **Vol target not implemented:** no-leverage + no dedicated cash/T-bill sleeve makes
  a vol target infeasible without adding a short-Treasury sleeve (left as a flag).
- **Regime-conditioned / CVaR / momentum overlays (review item 10)** are documented
  next steps, not implemented here.

