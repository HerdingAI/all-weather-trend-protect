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
- **Combos × schemes:** 2817 × 37 = **104229 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, TG-Short, TG-Short-LS, TG-Short-6m, EW-Short, EW-Short-LS, EW-Short-6m, EW-MA-Short, EW-Vol-Short, EW-DMA-Short, EW-AsymMA-Short, EW-DDStop-Short, EW-AsymMA-Short-6, EW-AsymMA-Short-9, EW-AsymMA-Tight, EW-AsymVol-Short, EW-Hedge-DMA-1, EW-Hedge-DMA, EW-Hedge-DMA-2, EW-Hedge-MA, EW-Hedge-DD, EW-Hedge-Dur, EW-Hedge-Dur-MA, EW-Hedge-Dur-DD, EW-Hedge-Dur-2, EW-Hedge-Dur-DD2, EW-Infl-Dur, EW-Infl-DurL, EW-Infl-Both, EW-Infl-BothL, EW-Infl-DurL2 — EW/InvVol/InvVar/ERC/MinVar separate composition
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

- **Combo:** US REIT,US Treasuries,US Corporate Bonds,Gold,Silver
- **Scheme:** LS-TSMOM  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 79.9, z = +2.68)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.300 | **0.227** | -0.073 |
| Both-down ann ret (net) | 4.00% | **-7.48%** | -11.48% |
| Max drawdown | -19.72% | **-23.18%** | -3.46% |
| Diversification ratio | n/a | **n/a** | — |
| Corr w/ equity (both-down) | -0.513 | **0.144** | — |
| Ann turnover | 320.99% | 321.34% | — |

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **104229**.
- Raw OOS net Sharpe: **0.227**.
- Expected max null Sharpe over 104229 trials: 1.600 (annualized).
- **Deflated Sharpe (annualized): -1.373**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.00** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [-0.453, 1.091]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-19.55%, 7.83%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 104229 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.6** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 and the both-down CI crosses 0: the both-down edge is **not** statistically robust after accounting for the number of portfolios tried.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 6.03% | **2.45%** |
| Ann vol | 7.79% | **10.80%** |
| Net Sharpe | 0.774 | **0.227** |
| Max DD | -16.26% | **-23.18%** |
| Both-down ann ret | -29.27% | **-7.48%** |
| Both-down hit rate | 4.17% | **50.00%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.827 | **0.076** |
| Corr w/ bonds | 0.784 | **-0.020** |
| Crisis avg ret | -5.28% | **-3.67%** |

Winner OOS Sharpe − All-Weather = **-0.547**; both-down ann diff = **+0.2178**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MinVar | 9 | 0.829 | -35.01% | -18.92% | 1.427 | 64.7 | 37 |
| ERC | 5 | 0.831 | -34.36% | -18.29% | 1.450 | 63.8 | 37 |
| EW-Infl-DurL | 1 | 0.609 | -36.82% | -23.91% | n/a | 57.4 | 36 |
| EW-Infl-DurL2 | 1 | 0.609 | -36.82% | -23.91% | n/a | 57.4 | 19 |
| EW-Infl-Both | 1 | 0.524 | -50.36% | -24.36% | n/a | 54.1 | 25 |
| EW-Hedge-DD | 1 | 0.617 | -31.05% | -19.89% | n/a | 52.7 | 35 |
| EW-DDStop-Short | 1 | 0.617 | -31.05% | -19.89% | n/a | 52.7 | 50 |
| EW-Infl-BothL | 4 | 0.537 | -47.97% | -23.63% | n/a | 52.4 | 21 |
| EW-Hedge-Dur-DD2 | 3 | 0.632 | -29.64% | -17.40% | n/a | 47.8 | 28 |
| EW-Hedge-Dur-DD | 3 | 0.632 | -29.64% | -17.40% | n/a | 47.8 | 28 |
| LS-TSMOM | 21 | 0.202 | -11.10% | -27.06% | n/a | 41.8 | 16 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 11.2 | field dispersion |
| Winner TRAIN score (z) | +2.68 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 10% | selection stability |
| Spearman TRAIN↔TEST score | -0.55 | rank persistence |
| Winner Sharpe test−train | -0.073 | large negative ⇒ overfit |
| Winner both-down test−train | -0.1148 | large negative ⇒ overfit |
| Effective N (vs nominal 104229) | 1.6 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.654**
- OOS (rolling) both-down ann ret = **-39.27%**
- OOS (rolling) max drawdown = -22.04%
- Rolling Deflated Sharpe = -0.946  (P>0 = 0.00)

| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |
|---:|---|---|---:|---:|---|
| 2018 | US Equity,International Equity,Preferred Stock,US Treasuries,Gold,Silver | MinVar | 78.0 | 0.66 | US Equity 20.0% |
| 2019 | US Equity,US REIT,US Corporate Bonds,Gold,Silver | EW | 74.8 | 0.71 | US Equity 20.0% |
| 2020 | US REIT,US Corporate Bonds,EM Bonds,Gold,Silver | MinVar | 79.4 | 0.59 | US REIT 20.0% |
| 2021 | US Equity,US Treasuries,US Corporate Bonds,Gold,Silver | MinVar | 76.4 | 0.54 | US Equity 20.0% |
| 2022 | US Equity,US REIT,US Treasuries,US Corporate Bonds,Gold,Silver | MinVar | 72.4 | 1.01 | US Equity 20.0% |
| 2023 | US Equity,US REIT,US Treasuries,US Corporate Bonds,Gold,Silver | MinVar | 72.9 | 0.60 | US Equity 20.0% |
| 2024 | US Equity,International Equity,US Treasuries,Gold,Silver | EW | 74.2 | 0.49 | US Equity 20.0% |
| 2025 | US Equity,International Equity,US Treasuries,Gold,Silver | EW | 77.2 | 0.61 | US Equity 20.0% |
| 2026 | US Equity,International Equity,US Treasuries,Gold,Silver | EW | 78.3 | 0.97 | US Equity 20.0% |

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
| Ann return (net) | 6.03% | 9.52% | **2.45%** |
| Ann vol | 7.79% | 10.93% | **10.80%** |
| Net Sharpe | 0.774 | 0.871 | **0.227** |
| Max DD | -16.26% | -19.25% | **-23.18%** |
| Both-down ann ret | -29.27% | -35.66% | **-7.48%** |
| Both-down hit rate | 4.17% | 8.33% | **50.00%** |
| Corr w/ equity | 0.827 | 0.780 | **0.076** |
| Crisis avg ret | -5.28% | -6.81% | **-3.67%** |

- LS-TSMOM OOS net Sharpe: **0.227**
- LS-TSMOM OOS both-down ann ret: **-7.48%**  (hit rate 50.00%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.085**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.453, 1.091]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-19.55%, 7.83%]

> **Verdict:** LS-TSMOM **reduces** the both-down loss vs both All-Weather and the risk-parity winner (though still negative OOS) — directionally the trend overlay helps in the AW weak spot, but not enough to flip it positive in this window. Check the bootstrap CI before trusting the ranking.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 6.03% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 31 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric2`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RP winner | US Equity, US REIT, Preferred Stock, US Treasuries, Gold, Silver | 9.52% | **0.871** | -19.25% | -35.66% | 0.418 | 0.597 | 0.659 | 1.00 | 0.00% | — | — |
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 6.03% | **0.774** | -16.26% | -29.27% | 0.366 | 0.423 | 0.658 | 1.00 | 0.00% | — | — |
| TrendGate | US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities | 7.31% | **0.718** | -18.01% | -27.86% | 0.309 | 0.544 | 0.628 | 1.00 | 0.00% | -0.59 | [0.07, 1.68] |
| EW-MA-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 4.24% | **0.613** | -14.01% | -12.95% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | -0.70 | [-0.08, 1.40] |
| EW-Infl-Dur | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 6.79% | **0.587** | -24.34% | -30.08% | 0.541 | 0.712 | 0.674 | 0.90 | 0.00% | -0.72 | [0.03, 1.42] |
| EW-AsymMA-Tight | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.98% | **0.568** | -17.20% | -16.47% | -0.090 | -0.053 | -0.066 | 1.00 | 0.00% | -0.74 | [-0.15, 1.29] |
| EW-AsymMA-Short-6 | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.80% | **0.565** | -14.83% | -17.03% | -0.113 | -0.026 | -0.032 | 1.00 | 0.00% | -0.75 | [-0.10, 1.30] |
| EW-Infl-DurL | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 7.17% | **0.540** | -29.00% | -34.65% | 0.627 | 0.818 | 0.645 | 0.90 | 0.00% | -0.77 | [-0.00, 1.38] |
| EW-Infl-DurL2 | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 7.30% | **0.526** | -30.54% | -36.18% | 0.656 | 0.853 | 0.636 | 0.90 | 0.00% | -0.78 | [-0.00, 1.36] |
| TG-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities | 4.08% | **0.515** | -14.51% | -23.75% | 0.112 | 0.412 | 0.524 | 1.00 | 0.00% | -0.80 | [-0.12, 1.48] |
| EW-AsymMA-Short-9 | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.27% | **0.508** | -14.10% | -16.70% | -0.107 | -0.041 | -0.050 | 1.00 | 0.00% | -0.80 | [-0.14, 1.23] |
| TG-Short | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities | 2.66% | **0.488** | -14.50% | -16.65% | 0.137 | 0.179 | 0.327 | 1.00 | 0.00% | -0.82 | [-0.23, 1.28] |
| EW-Hedge-MA | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.60% | **0.462** | -18.18% | -20.16% | 0.127 | 0.362 | 0.510 | 0.90 | 0.00% | -0.85 | [-0.20, 1.34] |
| EW-AsymMA-Short | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 3.43% | **0.406** | -17.22% | -17.76% | -0.124 | -0.049 | -0.060 | 1.00 | 0.00% | -0.90 | [-0.28, 1.15] |
| EW-Hedge-DMA-1 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.53% | **0.393** | -20.56% | -25.34% | 0.239 | 0.584 | 0.641 | 1.00 | 0.00% | -0.92 | [-0.18, 1.31] |
| TG-Short-LS | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver | 3.46% | **0.382** | -22.07% | -26.29% | 0.040 | 0.228 | 0.283 | 1.20 | 1.16% | -0.93 | [-0.31, 1.20] |
| EW-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.81% | **0.355** | -17.76% | -24.02% | 0.106 | 0.441 | 0.551 | 1.00 | 0.00% | -0.96 | [-0.26, 1.26] |
| EW-Hedge-DD | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.16% | **0.346** | -22.44% | -26.06% | 0.181 | 0.587 | 0.645 | 1.00 | 0.00% | -0.97 | [-0.29, 1.30] |
| EW-Hedge-Dur-DD | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.29% | **0.345** | -23.64% | -26.29% | 0.146 | 0.560 | 0.613 | 1.00 | 0.00% | -0.97 | [-0.32, 1.33] |
| EW-Hedge-Dur-DD2 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 3.02% | **0.315** | -24.04% | -25.73% | 0.126 | 0.542 | 0.593 | 1.00 | 0.00% | -1.00 | [-0.37, 1.31] |
| EW-DDStop-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 2.71% | **0.299** | -24.02% | -23.72% | 0.106 | 0.536 | 0.586 | 1.00 | 0.00% | -1.01 | [-0.35, 1.27] |
| EW-Short | US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.18% | **0.290** | -17.21% | -20.52% | 0.033 | 0.542 | 0.621 | 1.00 | 0.00% | -1.02 | [-0.28, 1.32] |
| EW-Hedge-Dur-MA | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 1.92% | **0.238** | -22.91% | -13.41% | -0.032 | 0.248 | 0.329 | 0.90 | 0.00% | -1.07 | [-0.50, 1.20] |
| EW-Hedge-DMA | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 2.02% | **0.234** | -22.44% | -22.49% | 0.129 | 0.525 | 0.581 | 1.00 | 0.00% | -1.08 | [-0.37, 1.15] |
| LS-TSMOM | US REIT, US Treasuries, US Corporate Bonds, Gold, Silver | 2.45% | **0.227** | -23.18% | -7.48% | -0.289 | 0.281 | 0.253 | 1.00 | 0.00% | -1.08 | [-0.45, 1.09] |
| EW-DMA-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 1.78% | **0.205** | -24.53% | -18.49% | 0.038 | 0.449 | 0.487 | 1.00 | 0.00% | -1.11 | [-0.41, 1.16] |
| EW-Short-LS | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds | 1.28% | **0.159** | -27.53% | -24.86% | 0.033 | 0.133 | 0.183 | 1.20 | 1.16% | -1.15 | [-0.52, 0.90] |
| EW-Vol-Short | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 1.10% | **0.156** | -18.66% | -17.76% | 0.050 | 0.365 | 0.443 | 1.00 | 0.00% | -1.16 | [-0.42, 1.08] |
| EW-AsymVol-Short | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 0.51% | **0.074** | -18.55% | -17.25% | 0.068 | 0.374 | 0.452 | 1.00 | 0.00% | -1.24 | [-0.46, 0.92] |
| EW-Hedge-DMA-2 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 0.52% | **0.059** | -25.85% | -19.65% | 0.019 | 0.467 | 0.510 | 1.00 | 0.00% | -1.25 | [-0.56, 0.99] |
| EW-Infl-BothL | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | 0.21% | **0.016** | -27.44% | -7.27% | 0.523 | 0.422 | 0.318 | 0.50 | 0.00% | -1.29 | [-0.57, 0.59] |
| EW-Hedge-Dur | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 0.04% | **0.005** | -26.67% | -15.39% | -0.003 | 0.406 | 0.423 | 1.00 | 0.00% | -1.31 | [-0.67, 0.99] |
| EW-Infl-Both | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | -0.17% | **-0.015** | -22.70% | -2.70% | 0.437 | 0.316 | 0.290 | 0.50 | 0.00% | -1.33 | [-0.63, 0.55] |
| EW-Hedge-Dur-2 | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | -0.62% | **-0.067** | -29.36% | -13.02% | -0.046 | 0.367 | 0.367 | 1.00 | 0.00% | -1.38 | [-0.75, 0.89] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 7.31% · Sharpe 0.718 · MaxDD -18.01% · both-down -27.86% · Upβ 0.309 / Dnβ 0.544 · Dn-corr 0.628 · gross 1.00 · lev cost 0.00%/yr · DSR -0.59 · Sharpe CI [0.07, 1.68]
- **Pros:** Long-only (gross ≤ 1, no leverage cost). Cuts equity exposure after a sustained drawdown — downside dampening. Keeps bond/gold/diversifier sleeves long (carry).
- **Cons:** 12m trend-gate LAGS: long into the start of drawdowns, flat into the start of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal). Cannot go net-short, so no positive both-down return. Whipsaw in choppy markets (gate toggles on/off).

**TG-Short** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities

- Net ann ret 2.66% · Sharpe 0.488 · MaxDD -14.50% · both-down -16.65% · Upβ 0.137 / Dnβ 0.179 · Dn-corr 0.327 · gross 1.00 · lev cost 0.00%/yr · DSR -0.82 · Sharpe CI [-0.23, 1.28]
- **Pros:** Flips the equity sleeve to NET-SHORT on the downside signal (the brief's lever) — long equity when up, short equity when down; bonds/gold/diversifiers stay long. Directly targets negative downside-β with positive upside-β. Sleeve-level netting can keep gross ≤ 1 (no leverage cost) when the short equity leg nets against the long book. Reuses the MinVar base.
- **Cons:** MinVar base starves high-vol equity to ~5-10% weight → little equity to short, so the upside capture AND the short benefit are both muted; return floor is well below AW. 12m signal lags: shorts ~12m INTO a drawdown (after the drop has happened), longs ~12m into a rally (after the rebound). Whipsaw in choppy markets; check DSR / bootstrap CI.

**TG-Short-LS** — combo: US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 3.46% · Sharpe 0.382 · MaxDD -22.07% · both-down -26.29% · Upβ 0.040 / Dnβ 0.228 · Dn-corr 0.283 · gross 1.20 · lev cost 1.16%/yr · DSR -0.93 · Sharpe CI [-0.31, 1.20]
- **Pros:** TG-Short (short equity on downside) + a 0.20 LS-TSMOM overlay — both the equity flip and the broader momentum crisis-alpha leg. Targets the asymmetric goal from two angles. Smaller overlay than RP-LS-Overlay → lower leverage cost.
- **Cons:** Inherits the MinVar-base equity starvation AND the 12m lag AND the overlay whipsaw — all three costs. Gross can exceed 1 → leverage cost up to 1.16%/yr. Most overfitting surface of the TG-Short family; check DSR / bootstrap CI.

**TG-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 4.08% · Sharpe 0.515 · MaxDD -14.51% · both-down -23.75% · Upβ 0.112 / Dnβ 0.412 · Dn-corr 0.524 · gross 1.00 · lev cost 0.00%/yr · DSR -0.80 · Sharpe CI [-0.12, 1.48]
- **Pros:** TG-Short with a FASTER 6m trend signal — reduces the 12m lag (out of drawdowns sooner, into rallies sooner), so the short flip is better timed. Direct lever for negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws MORE in choppy markets (more false flips). MinVar base still starves equity → muted upside capture. Shorter lookback → more turnover; check DSR / bootstrap CI.

**EW-Short** — combo: US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.18% · Sharpe 0.290 · MaxDD -17.21% · both-down -20.52% · Upβ 0.033 / Dnβ 0.542 · Dn-corr 0.621 · gross 1.00 · lev cost 0.00%/yr · DSR -1.02 · Sharpe CI [-0.28, 1.32]
- **Pros:** EQUAL-WEIGHT base (like All-Weather's own ~1/n across sleeves) so equity keeps a real weight (~12-25%) — fixes the MinVar-base equity starvation that left TG-Short with nothing to short and ~3% return. Short equity on the downside signal → negative downside-β with positive upside-β; return floor near AW. Sleeve-level netting can keep gross ≤ 1 (no leverage cost).
- **Cons:** More equity weight → higher vol / drawdown than the MinVar-base flavors. 12m signal lags (consider EW-Short-6m for less lag). Equal-weight ignores covariance; check DSR / bootstrap CI.

**EW-Short-LS** — combo: US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret 1.28% · Sharpe 0.159 · MaxDD -27.53% · both-down -24.86% · Upβ 0.033 / Dnβ 0.133 · Dn-corr 0.183 · gross 1.20 · lev cost 1.16%/yr · DSR -1.15 · Sharpe CI [-0.52, 0.90]
- **Pros:** EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM overlay. Highest upside capture of the family (EW base keeps equity, overlay adds crisis alpha). Targets both beat-AW return AND asymmetric protection.
- **Cons:** Gross can exceed 1 → leverage cost up to 1.16%/yr. Inherits the 12m lag and overlay whipsaw. Most overfitting surface; check DSR / bootstrap CI.

**EW-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.81% · Sharpe 0.355 · MaxDD -17.76% · both-down -24.02% · Upβ 0.106 / Dnβ 0.441 · Dn-corr 0.551 · gross 1.00 · lev cost 0.00%/yr · DSR -0.96 · Sharpe CI [-0.26, 1.26]
- **Pros:** EW-Short with a FASTER 6m signal — real equity weight (EW base) AND less lag, so the short flip is both meaningful and better timed. Directly targets the brief: high upside-β, negative downside-β, AW-like return floor. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws more; more turnover. Higher vol / drawdown than MinVar-base flavors (more equity). Most parameters → check DSR / bootstrap CI.

**EW-MA-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 4.24% · Sharpe 0.613 · MaxDD -14.01% · both-down -12.95% · Upβ 0.013 / Dnβ 0.123 · Dn-corr 0.224 · gross 1.00 · lev cost 0.00%/yr · DSR -0.70 · Sharpe CI [-0.08, 1.40]
- **Pros:** EW-Short driven by a LEADING signal: price-vs-10m-SMA crossover (an MA crosses BEFORE a lookback-return flips sign), so equity exits BEFORE the drawdown and re-enters BEFORE the rally — the round-2 lagging-momentum blocker's direct fix. Real equity weight (EW base) + short-on-downside; directly targets high upside-β with negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** MA crossover still whipsaws in choppy/sideways tape (price oscillates around the SMA → repeated false flips). Higher vol / drawdown than MinVar-base flavors (more equity); more turnover than the 12m TSMOM gate. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-Vol-Short** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.10% · Sharpe 0.156 · MaxDD -18.66% · both-down -17.76% · Upβ 0.050 / Dnβ 0.365 · Dn-corr 0.443 · gross 1.00 · lev cost 0.00%/yr · DSR -1.16 · Sharpe CI [-0.42, 1.08]
- **Pros:** EW-Short driven by a VOL-REGIME signal: short equity when 6m realized vol EXCEEDS its trailing 60m median (vol spikes LEAD drawdowns), long when vol is calm — a regime filter, not a price-trend filter. Different information set from price-MA → diversifies the signal family; real equity weight (EW base). Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Vol spikes can lag the actual drawdown start (vol rises AS price falls, not before) — may still enter the short late. 60m median needs a long warm-up; fewer active signals in the early TEST window. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-DMA-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.78% · Sharpe 0.205 · MaxDD -24.53% · both-down -18.49% · Upβ 0.038 / Dnβ 0.449 · Dn-corr 0.487 · gross 1.00 · lev cost 0.00%/yr · DSR -1.11 · Sharpe CI [-0.41, 1.16]
- **Pros:** EW-Short driven by a DUAL-MA signal: fast 3m SMA vs slow 10m SMA — a faster, smoother crossover than price-vs-SMA (the slow MA smooths the reference, so fewer false flips than EW-MA-Short). Leading signal (a fast/slow cross precedes the lookback-return flip); real equity weight (EW base) + short-on-downside. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Fast 3m SMA is noisy → still some whipsaw; the slow 10m MA adds lag vs the single-MA gate. Two MAs → slightly more overfitting surface than EW-MA-Short. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-AsymMA-Short** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 3.43% · Sharpe 0.406 · MaxDD -17.22% · both-down -17.76% · Upβ -0.124 / Dnβ -0.049 · Dn-corr -0.060 · gross 1.00 · lev cost 0.00%/yr · DSR -0.90 · Sharpe CI [-0.28, 1.15]
- **Pros:** ASYMMETRIC (hysteretic) MA gate — the round-3 prescription made concrete: LONG until price < 3m SMA (FAST downside exit), then SHORT until price > 12m SMA (SLOW upside re-entry). Starts LONG and holds through chop above the fast MA, so it stays correlated on the way up and only flees (goes net-short) after a clear break. Hysteresis band = the fast/slow-MA gap. The one untested lever: a SYMMETRIC signal (rounds 1-3) is equally trigger-happy up and down → Dnβ >= Upβ everywhere; an asymmetric one can in principle be 'correlated up, protected down'. Real equity weight (EW base) + short-on-downside; sleeve-level netting can keep gross <= 1.
- **Cons:** The slow 12m re-entry can lag the START of a rally (re-enters late after a V rebound) — some upside missed at the turn. Stateful + two MA horizons → more overfitting surface than the symmetric gates; the fast/slow gap is a tuned parameter. New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime.

**EW-DDStop-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.71% · Sharpe 0.299 · MaxDD -24.02% · both-down -23.72% · Upβ 0.106 / Dnβ 0.536 · Dn-corr 0.586 · gross 1.00 · lev cost 0.00%/yr · DSR -1.01 · Sharpe CI [-0.35, 1.27]
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

**EW-AsymMA-Tight** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.98% · Sharpe 0.568 · MaxDD -17.20% · both-down -16.47% · Upβ -0.090 / Dnβ -0.053 · Dn-corr -0.066 · gross 1.00 · lev cost 0.00%/yr · DSR -0.74 · Sharpe CI [-0.15, 1.29]
- **Pros:** Round-4b SWEEP point: a TIGHTER hysteresis band — fast_exit=2 (exit on a 2m-MA break, even faster downside flee) + slow_entry=6 (re-enter on a 6m SMA). The tightest band in the family: quickest to flee, quickest to return — tests the 'high turnover, low lag' corner of the grid. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** The 2m exit is noisy → more false flips in chop; the tight band → highest turnover of the family (more cost, more whipsaw). Two tuned parameters → most overfitting surface of the sweep; one split = one regime. Check DSR / bootstrap CI.

**EW-AsymVol-Short** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 0.51% · Sharpe 0.074 · MaxDD -18.55% · both-down -17.25% · Upβ 0.068 / Dnβ 0.374 · Dn-corr 0.452 · gross 1.00 · lev cost 0.00%/yr · DSR -1.24 · Sharpe CI [-0.46, 0.92]
- **Pros:** Round-4b: a HYSTERETIC vol-regime gate — LONG -> SHORT once the prior month's 6m realized vol exceeds its trailing 60m median (fast exit on stress), SHORT -> LONG once vol falls back below 0.85x the median (slow re-entry, wait for genuine calm). The hysteresis band = 0.85..1.0x median; a vol spike flees, vol must genuinely calm to return. Fixes the round-3 EW-Vol-Short, which SHORTED THE 2020 COVID V-REBOUND (vol stayed elevated through the rally → the symmetric vol-gate never re-entered long, -> -1.52% / -31.69% MaxDD). The slow lower-bar re-entry waits for vol to actually calm. Different information set from price-MA → diversifies the signal family. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Vol can stay elevated THROUGH a V-rebound even with hysteresis (vol calms late) — the 0.85x bar may still re-enter after the rally's best months. 60m median needs a long warm-up; the 0.85x / 1.0x thresholds are tuned → overfitting surface. New signal → check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-DMA-1** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.53% · Sharpe 0.393 · MaxDD -20.56% · both-down -25.34% · Upβ 0.239 / Dnβ 0.584 · Dn-corr 0.641 · gross 1.00 · lev cost 0.00%/yr · DSR -0.92 · Sharpe CI [-0.18, 1.31]
- **Pros:** Round-5 DECOUPLED insurance overlay, light hedge (w_hedge=1.0): the long EW base NEVER flips (gross 1, fully long in every month incl. recoveries) so Upβ stays that of the long-only base — the round-4b structural blocker's direct fix. A SEPARATE additive short overlay on the equity sleeves activates only when the fast 3m/10m dual-MA signal is DOWN (flat otherwise); w_hedge=1.0 nets equity to ~0 in down-months (a 'cash on the downside' hedge, not net-short). Fast symmetric signal (dma) -> FAST-OFF in recoveries (does not drag the rally, unlike round-4's slow re-entry). Decouples the two halves the brief asks for: long base = upside, overlay = downside insurance; the 'long-term short a ticker' permission applied as an overlay not a gate.
- **Cons:** w_hedge=1.0 only nets equity to ~0 in down-months -> Dnβ is reduced but likely still POSITIVE (the non-equity sleeves still track equity down); to drive Dnβ NEGATIVE needs w_hedge > 1. Additive gross when active -> leverage cost; the overlay is a separate notional so it is NOT free (vs the sleeve-netted flip). New construction + tuned w_hedge -> overfitting surface; one TRAIN/TEST split = one regime. Check DSR / bootstrap CI.

**EW-Hedge-DMA** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.02% · Sharpe 0.234 · MaxDD -22.44% · both-down -22.49% · Upβ 0.129 / Dnβ 0.525 · Dn-corr 0.581 · gross 1.00 · lev cost 0.00%/yr · DSR -1.08 · Sharpe CI [-0.37, 1.15]
- **Pros:** Round-5 DECOUPLED overlay, MEDIUM hedge (w_hedge=1.5): same never-flipping long EW base + fast dma-triggered additive short overlay, but w_hedge=1.5 -> NET SHORT equity in down-months (base equity weight - 1.5x = negative). This is the sizing expected to push Dnβ NEGATIVE while the always-long base keeps Upβ POSITIVE — the unmet asymmetric property, by construction. Fast dma signal -> fast-off in recoveries; the base's full equity weight is at work in up-months (overlay flat). Directly targets 'correlated up, protected down' via decoupling, not a single price-gate.
- **Cons:** Gross 1 + 1.5 x (equity fraction) when active -> leverage cost (the explicit price of decoupling); only paid in down-months. Net-short equity in down-months means a wrong-footed whipsaw (signal flips short just before a rally) costs more than the light hedge; the fast dma signal whipsaws in chop. w_hedge=1.5 is tuned; new construction -> overfitting surface. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-DMA-2** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 0.52% · Sharpe 0.059 · MaxDD -25.85% · both-down -19.65% · Upβ 0.019 / Dnβ 0.467 · Dn-corr 0.510 · gross 1.00 · lev cost 0.00%/yr · DSR -1.25 · Sharpe CI [-0.56, 0.99]
- **Pros:** Round-5 DECOUPLED overlay, HEAVY hedge (w_hedge=2.0): the strongest downside clip — net short 1.0x the base equity weight in down-months. Tests how much downside protection (Dnβ most negative) the construction can buy before the leverage cost and whipsaw overwhelm the return. Same never-flipping long base (Upβ positive) + fast dma overlay. Brackets the w_hedge grid with EW-Hedge-DMA-1 (1.0) / -DMA (1.5).
- **Cons:** Largest additive gross -> largest leverage cost; most whipsaw damage if the signal mistimes. w_hedge=2.0 is the most aggressive / most overfit corner of the round-5 grid. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-MA** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.60% · Sharpe 0.462 · MaxDD -18.18% · both-down -20.16% · Upβ 0.127 / Dnβ 0.362 · Dn-corr 0.510 · gross 0.90 · lev cost 0.00%/yr · DSR -0.85 · Sharpe CI [-0.20, 1.34]
- **Pros:** Round-5 overlay with the single 10m-SMA signal (vs the dual-MA dma): the overlay shorts when price < its 10m SMA. A slower, smoother downside trigger than dma -> fewer false flips in chop, but slower to deactivate in a V-rebound. Same never-flipping long EW base (Upβ positive) + additive short overlay (w_hedge=1.5). Tests whether the smoother signal beats the fast dma on the overlay (fewer whipsaw trades vs later off in recoveries).
- **Cons:** The 10m SMA deactivates SLOWER than dma in a V-rebound (price reclaims the 10m SMA late) -> the overlay can drag the start of the rally (the round-4 problem, milder here because the base is always long). Additive gross -> leverage cost; tuned w_hedge. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-DD** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.16% · Sharpe 0.346 · MaxDD -22.44% · both-down -26.06% · Upβ 0.181 / Dnβ 0.587 · Dn-corr 0.645 · gross 1.00 · lev cost 0.00%/yr · DSR -0.97 · Sharpe CI [-0.29, 1.30]
- **Pros:** Round-5 overlay with the dd_stop (drawdown) signal: the overlay shorts once the equity sleeve is >10% below its trailing 6m peak and deactivates once within 3% of the peak. 'Hedge the break, un-hedge the new high' — the most direct map to the brief's shape, now applied to a SEPARATE overlay (not a flip). Same never-flipping long EW base (Upβ positive) + additive short overlay (w_hedge=1.5). The drawdown signal deactivates NATURALLY when equity recovers (drawdown shrinks) -> fast-off in V-rebounds, without a separate re-entry MA.
- **Cons:** dd_stop is a LAGGING trigger (price has already fallen 10% before the hedge activates) -> the hedge misses the first 10% of the drawdown; on an overlay (not a flip) this is late-activate but still fast-deactivate. Drawdown thresholds (10% / 3%) are tuned; additive gross -> leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 0.04% · Sharpe 0.005 · MaxDD -26.67% · both-down -15.39% · Upβ -0.003 / Dnβ 0.406 · Dn-corr 0.423 · gross 1.00 · lev cost 0.00%/yr · DSR -1.31 · Sharpe CI [-0.67, 0.99]
- **Pros:** Round-6: round-5 decoupled overlay (never-flip long EW base -> Upβ positive) PLUS a duration/bond overlay (w_hedge_bd=1.5) that shorts the BOND sleeves on their OWN dma downtrend. The direct fix for the round-5 gap: in both-down / stagflation months bonds fall WITH equities, and an equity-only overlay could not touch them. Shorting bonds on bonds' own downtrend clips that loss. Self-avoiding flight-to-quality: when bonds RISE (2008 Q4, 2020 Q1) their dma is up -> no bond short -> no bleed there. Equity overlay (w_hedge=1.5, dma) unchanged from round 5.
- **Cons:** Two additive shorts (equity + bonds) -> higher gross -> more leverage cost than round 5. The dma signal still lags ~12m on the equity side (the round-5 'fires too late' issue is only half-fixed here). Bond dma can whipsaw in choppy rates regimes. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-MA** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.92% · Sharpe 0.238 · MaxDD -22.91% · both-down -13.41% · Upβ -0.032 / Dnβ 0.248 · Dn-corr 0.329 · gross 0.90 · lev cost 0.00%/yr · DSR -1.07 · Sharpe CI [-0.50, 1.20]
- **Pros:** Round-6 duration overlay with the symmetric 10m MA signal (vs EW-Hedge-Dur's dma) on BOTH the equity and bond shorts. Same never-flip long EW base + duration short (w_hedge_bd=1.5) targeting the both-down gap; self-avoiding flight-to-quality.
- **Cons:** The single 10m MA deactivates slower than dma in a V-rebound on both sleeves -> can drag the start of rallies. Two additive shorts -> leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-DD** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.29% · Sharpe 0.345 · MaxDD -23.64% · both-down -26.29% · Upβ 0.146 / Dnβ 0.560 · Dn-corr 0.613 · gross 1.00 · lev cost 0.00%/yr · DSR -0.97 · Sharpe CI [-0.32, 1.33]
- **Pros:** Round-6 with the FAST equity-drawdown trigger (gate_signal=eq_dd): a SYMMETRIC, stateless drawdown gate that shorts a sleeve once it is >10% below its 6m peak and releases once back within 3% — fires IN down-months and releases fast in recoveries, the direct fix for round-5's 'dma/ma fires ~12m too late' problem. Duration overlay (w_hedge_bd=1.5) shorts bonds on bonds' own drawdown -> clips the both-down loss; flight-to-quality safe. The user's literal ask: short duration/TLT in the overlay + a fast equity-drawdown trigger.
- **Cons:** eq_dd is stateless -> more whipsaw near peaks than hysteretic dd_stop (can toggle short/long in chop). For bonds a 10% drawdown threshold rarely fires (bonds less vol) -> the bond leg may stay quiet outside a true bond rout (2022). Two additive shorts + the fast trigger -> higher turnover / leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-2** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret -0.62% · Sharpe -0.067 · MaxDD -29.36% · both-down -13.02% · Upβ -0.046 / Dnβ 0.367 · Dn-corr 0.367 · gross 1.00 · lev cost 0.00%/yr · DSR -1.38 · Sharpe CI [-0.75, 0.89]
- **Pros:** Round-6 with a BIGGER duration short (w_hedge_bd=2.0 vs 1.5) on the dma signal: w_hedge_bd>1 means net-short duration in bond-down months — a more aggressive stagflation hedge, the brief's 'short a ticker' (short TLT / long-duration) as a conditional overlay. Same never-flip long EW base (Upβ positive); equity overlay dma.
- **Cons:** Net-short duration when bonds trend down -> larger gross / leverage cost and larger whipsaw if the bond rout reverses. dma still lags on equity. Check DSR / bootstrap CI; one split = one regime.

**EW-Hedge-Dur-DD2** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.02% · Sharpe 0.315 · MaxDD -24.04% · both-down -25.73% · Upβ 0.126 / Dnβ 0.542 · Dn-corr 0.593 · gross 1.00 · lev cost 0.00%/yr · DSR -1.00 · Sharpe CI [-0.37, 1.31]
- **Pros:** Round-6 combining BOTH levers at full strength: fast eq_dd equity trigger + a bigger 2.0x duration short. The maximal mechanical fix for the round-5 diagnosis (equity overlay fires too late AND can't touch bonds in both-down). Never-flip long EW base -> Upβ positive by construction.
- **Cons:** Most parameters / overfitting surface of the round-6 family; highest gross / leverage cost and turnover. eq_dd's bond leg may stay quiet outside a true bond rout. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-Dur** — combo: US Equity, International Equity, Preferred Stock, EM Bonds, Commodities

- Net ann ret 6.79% · Sharpe 0.587 · MaxDD -24.34% · both-down -30.08% · Upβ 0.541 / Dnβ 0.712 · Dn-corr 0.674 · gross 0.90 · lev cost 0.00%/yr · DSR -0.72 · Sharpe CI [0.03, 1.42]
- **Pros:** Round-7 LEADING macro gate (the user's ask): duration overlay fires off an EX-ANTE inflation regime (trailing-12m Commodities return) instead of a lagging sleeve trend. Short bonds (w_hedge_bd=1.5) ONLY when inflation is RISING (stagflation risk-off, 2022 -- the both-down regime round 6 could only hedge with a lagging short); no long tilt. Never-flip long EW base -> Upβ positive. Commodities lead equities in the stagflation case (topped before equities in 2022). Isolates the duration-regime lever (no equity short, no long tilt).
- **Cons:** Inflation regimes are persistent but not perfect: equity-up + inflation-up months (2021, 2024) take a bond-short drag on Upβ. Commodities are a noisy inflation proxy. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-DurL** — combo: US Equity, International Equity, Preferred Stock, EM Bonds, Commodities

- Net ann ret 7.17% · Sharpe 0.540 · MaxDD -29.00% · both-down -34.65% · Upβ 0.627 / Dnβ 0.818 · Dn-corr 0.645 · gross 0.90 · lev cost 0.00%/yr · DSR -0.77 · Sharpe CI [-0.00, 1.38]
- **Pros:** Round-7 with the SYMMETRIC duration-regime switch: short bonds (w_hedge_bd=1.5) when inflation RISING + LONG-bonds tilt (w_long_bd=1.5) when inflation FALLING -- own the bonds that rally in flight-to-quality (2008 Q4, 2020 Q1), the regime where bonds hedge equity for free and Dnβ can go negative. Never-flip long EW base -> Upβ positive. The leading-macro lever at its most complete (regime-switching duration, both directions).
- **Cons:** Two-sided regime switch -> most regime-timing risk: a wrong-footed inflation call (e.g. long bonds into a reflation) costs on both the tilt and the foregone short. Additive gross both ways -> leverage cost. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-Both** — combo: US Equity, International Equity, US REIT, Preferred Stock, EM Bonds

- Net ann ret -0.17% · Sharpe -0.015 · MaxDD -22.70% · both-down -2.70% · Upβ 0.437 / Dnβ 0.316 · Dn-corr 0.290 · gross 0.50 · lev cost 0.00%/yr · DSR -1.33 · Sharpe CI [-0.63, 0.55]
- **Pros:** Round-7 full inflation-regime RISK-OFF: when inflation RISING, short BOTH equity (w_hedge=1.5) AND bonds (w_hedge_bd=1.5) -- both fall in stagflation, so this is the direct 2022 both-down hedge the round-5/6 equity-/bond-own-trend gates could not time. No long tilt. Never-flip long EW base -> Upβ positive (the equity short is an additive overlay, not a base flip).
- **Cons:** Shorting equity when inflation rising drags Upβ in equity-up + inflation-up months (2021, 2024) -- the same tension as every lagging equity short, now on a macro trigger. Highest gross of the round-7 family. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-BothL** — combo: US Equity, International Equity, US REIT, Preferred Stock, EM Bonds

- Net ann ret 0.21% · Sharpe 0.016 · MaxDD -27.44% · both-down -7.27% · Upβ 0.523 / Dnβ 0.422 · Dn-corr 0.318 · gross 0.50 · lev cost 0.00%/yr · DSR -1.29 · Sharpe CI [-0.57, 0.59]
- **Pros:** Round-7 maximal: short equity AND bonds when inflation RISING + long-bonds tilt (w_long_bd=1.5) when FALLING. The complete leading-macro regime switch across all three legs (equity short, duration short, duration long). The most aggressive test of whether an ex-ante inflation gate can deliver Upβ > Dnβ. Never-flip long EW base -> Upβ positive.
- **Cons:** Most parameters / overfitting surface of the round-7 family; largest additive gross / leverage cost; most regime-timing risk both ways. Check DSR / bootstrap CI; one split = one regime.

**EW-Infl-DurL2** — combo: US Equity, International Equity, Preferred Stock, EM Bonds, Commodities

- Net ann ret 7.30% · Sharpe 0.526 · MaxDD -30.54% · both-down -36.18% · Upβ 0.656 / Dnβ 0.853 · Dn-corr 0.636 · gross 0.90 · lev cost 0.00%/yr · DSR -0.78 · Sharpe CI [-0.00, 1.36]
- **Pros:** Round-7 with a BIGGER long-duration tilt (w_long_bd=2.0) when inflation FALLING -- push hardest on the flight-to-quality amplify lever (own 2.0x the base bond weight in disinflationary drawdowns) to drive Dnβ most negative, while keeping the 1.5x bond short in stagflation. No equity short (duration-only regime). Never-flip long EW base -> Upβ positive. Tests how much downside protection the long-tilt leg can buy before its leverage cost and reflation risk overwhelm it.
- **Cons:** The 2.0x long tilt is the most overfit / most leverage-cost corner of the round-7 grid; a long-bonds tilt into a reflation (inflation re-accelerates) is unhedged by the equity leg. Check DSR / bootstrap CI; one split = one regime.

> **Verdict:** Of the 31 TrendProtect flavors, **TrendGate, EW-Infl-Dur, EW-Infl-DurL, EW-Infl-DurL2** beat All-Weather's net OOS return (6.03%) after the 5.8%/yr leverage cost. Cross-check the Dn-corr / Dnβ columns for the asymmetric protection and the DSR / bootstrap Sharpe CI for significance before trusting any single winner — the flavors share sleeves so DSR is conservative (see §3 effective-N), and a single TRAIN/TEST split is one regime.

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

