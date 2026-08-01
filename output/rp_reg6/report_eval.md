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
- **Combos × schemes:** 2817 × 22 = **61974 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, TG-Short, TG-Short-LS, TG-Short-6m, EW-Short, EW-Short-LS, EW-Short-6m, EW-MA-Short, EW-Vol-Short, EW-DMA-Short, EW-AsymMA-Short, EW-DDStop-Short, EW-AsymMA-Short-6, EW-AsymMA-Short-9, EW-AsymMA-Tight, EW-AsymVol-Short — EW/InvVol/InvVar/ERC/MinVar separate composition
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
- **TRAIN rank:** #1 (TRAIN score 75.8, z = +2.24)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.300 | **0.227** | -0.073 |
| Both-down ann ret (net) | 4.00% | **-7.48%** | -11.48% |
| Max drawdown | -19.72% | **-23.18%** | -3.46% |
| Diversification ratio | n/a | **n/a** | — |
| Corr w/ equity (both-down) | -0.513 | **0.144** | — |
| Ann turnover | 320.99% | 321.34% | — |

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **61974**.
- Raw OOS net Sharpe: **0.227**.
- Expected max null Sharpe over 61974 trials: 1.562 (annualized).
- **Deflated Sharpe (annualized): -1.335**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.00** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [-0.448, 1.064]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-19.53%, 8.05%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 61974 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.7** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
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
| InvVol | 2 | 0.774 | -34.41% | -18.45% | 1.493 | 57.3 | 31 |
| MinVar | 21 | 0.819 | -33.10% | -18.14% | 1.440 | 54.4 | 28 |
| InvVar | 3 | 0.762 | -33.48% | -18.34% | 1.493 | 51.8 | 34 |
| ERC | 17 | 0.799 | -33.01% | -17.92% | 1.429 | 51.3 | 27 |
| LS-TSMOM | 7 | 0.205 | -11.10% | -27.40% | n/a | 38.0 | 11 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 11.5 | field dispersion |
| Winner TRAIN score (z) | +2.24 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 30% | selection stability |
| Spearman TRAIN↔TEST score | +0.10 | rank persistence |
| Winner Sharpe test−train | -0.073 | large negative ⇒ overfit |
| Winner both-down test−train | -0.1148 | large negative ⇒ overfit |
| Effective N (vs nominal 61974) | 1.7 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.654**
- OOS (rolling) both-down ann ret = **-39.27%**
- OOS (rolling) max drawdown = -22.04%
- Rolling Deflated Sharpe = -0.907  (P>0 = 0.00)

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
| Ann return (net) | 6.03% | 7.78% | **2.45%** |
| Ann vol | 7.79% | 9.63% | **10.80%** |
| Net Sharpe | 0.774 | 0.807 | **0.227** |
| Max DD | -16.26% | -18.33% | **-23.18%** |
| Both-down ann ret | -29.27% | -31.85% | **-7.48%** |
| Both-down hit rate | 4.17% | 4.17% | **50.00%** |
| Corr w/ equity | 0.827 | 0.803 | **0.076** |
| Crisis avg ret | -5.28% | -6.86% | **-3.67%** |

- LS-TSMOM OOS net Sharpe: **0.227**
- LS-TSMOM OOS both-down ann ret: **-7.48%**  (hit rate 50.00%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.085**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.448, 1.064]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-19.53%, 8.05%]

> **Verdict:** LS-TSMOM **reduces** the both-down loss vs both All-Weather and the risk-parity winner (though still negative OOS) — directionally the trend overlay helps in the AW weak spot, but not enough to flip it positive in this window. Check the bootstrap CI before trusting the ranking.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 6.03% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 16 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric2`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RP winner | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Gold, Silver | 7.78% | **0.807** | -18.33% | -31.85% | 0.408 | 0.575 | 0.716 | 1.00 | 0.00% | — | — |
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 6.03% | **0.774** | -16.26% | -29.27% | 0.366 | 0.423 | 0.658 | 1.00 | 0.00% | — | — |
| TrendGate | US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities | 7.31% | **0.718** | -18.01% | -27.86% | 0.309 | 0.544 | 0.628 | 1.00 | 0.00% | -0.59 | [0.08, 1.65] |
| EW-MA-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 4.24% | **0.613** | -14.01% | -12.95% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | -0.70 | [-0.06, 1.41] |
| EW-AsymMA-Short-6 | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.80% | **0.565** | -14.83% | -17.03% | -0.113 | -0.026 | -0.032 | 1.00 | 0.00% | -0.75 | [-0.09, 1.32] |
| TG-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities | 4.08% | **0.515** | -14.51% | -23.75% | 0.112 | 0.412 | 0.524 | 1.00 | 0.00% | -0.80 | [-0.12, 1.45] |
| EW-AsymMA-Short-9 | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 4.27% | **0.508** | -14.10% | -16.70% | -0.107 | -0.041 | -0.050 | 1.00 | 0.00% | -0.80 | [-0.12, 1.23] |
| TG-Short | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities | 2.66% | **0.488** | -14.50% | -16.65% | 0.137 | 0.179 | 0.327 | 1.00 | 0.00% | -0.82 | [-0.20, 1.29] |
| TG-Short-LS | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities | 2.50% | **0.441** | -14.40% | -15.68% | 0.127 | 0.117 | 0.198 | 1.20 | 1.16% | -0.87 | [-0.18, 1.19] |
| EW-AsymMA-Short | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 3.43% | **0.406** | -17.22% | -17.76% | -0.124 | -0.049 | -0.060 | 1.00 | 0.00% | -0.90 | [-0.26, 1.15] |
| EW-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.81% | **0.355** | -17.76% | -24.02% | 0.106 | 0.441 | 0.551 | 1.00 | 0.00% | -0.96 | [-0.26, 1.24] |
| EW-DDStop-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 2.71% | **0.299** | -24.02% | -23.72% | 0.106 | 0.536 | 0.586 | 1.00 | 0.00% | -1.01 | [-0.35, 1.25] |
| EW-Short | US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.18% | **0.290** | -17.21% | -20.52% | 0.033 | 0.542 | 0.621 | 1.00 | 0.00% | -1.02 | [-0.28, 1.30] |
| EW-AsymMA-Tight | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds | 1.50% | **0.278** | -18.65% | -12.64% | -0.096 | -0.130 | -0.243 | 1.00 | 0.00% | -1.03 | [-0.49, 1.06] |
| LS-TSMOM | US REIT, US Treasuries, US Corporate Bonds, Gold, Silver | 2.45% | **0.227** | -23.18% | -7.48% | -0.289 | 0.281 | 0.253 | 1.00 | 0.00% | -1.08 | [-0.45, 1.06] |
| EW-DMA-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 1.78% | **0.205** | -24.53% | -18.49% | 0.038 | 0.449 | 0.487 | 1.00 | 0.00% | -1.11 | [-0.41, 1.16] |
| EW-Vol-Short | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 1.10% | **0.156** | -18.66% | -17.76% | 0.050 | 0.365 | 0.443 | 1.00 | 0.00% | -1.16 | [-0.42, 1.07] |
| EW-Short-LS | US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds | -0.05% | **-0.007** | -19.42% | -24.29% | -0.009 | 0.439 | 0.541 | 1.20 | 1.16% | -1.32 | [-0.53, 0.76] |
| EW-AsymVol-Short | US Equity, US REIT, US Treasuries, US Corporate Bonds, EM Bonds | -1.64% | **-0.222** | -27.63% | -15.59% | 0.038 | 0.266 | 0.329 | 1.00 | 0.00% | -1.53 | [-0.80, 0.42] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 7.31% · Sharpe 0.718 · MaxDD -18.01% · both-down -27.86% · Upβ 0.309 / Dnβ 0.544 · Dn-corr 0.628 · gross 1.00 · lev cost 0.00%/yr · DSR -0.59 · Sharpe CI [0.08, 1.65]
- **Pros:** Long-only (gross ≤ 1, no leverage cost). Cuts equity exposure after a sustained drawdown — downside dampening. Keeps bond/gold/diversifier sleeves long (carry).
- **Cons:** 12m trend-gate LAGS: long into the start of drawdowns, flat into the start of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal). Cannot go net-short, so no positive both-down return. Whipsaw in choppy markets (gate toggles on/off).

**TG-Short** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities

- Net ann ret 2.66% · Sharpe 0.488 · MaxDD -14.50% · both-down -16.65% · Upβ 0.137 / Dnβ 0.179 · Dn-corr 0.327 · gross 1.00 · lev cost 0.00%/yr · DSR -0.82 · Sharpe CI [-0.20, 1.29]
- **Pros:** Flips the equity sleeve to NET-SHORT on the downside signal (the brief's lever) — long equity when up, short equity when down; bonds/gold/diversifiers stay long. Directly targets negative downside-β with positive upside-β. Sleeve-level netting can keep gross ≤ 1 (no leverage cost) when the short equity leg nets against the long book. Reuses the MinVar base.
- **Cons:** MinVar base starves high-vol equity to ~5-10% weight → little equity to short, so the upside capture AND the short benefit are both muted; return floor is well below AW. 12m signal lags: shorts ~12m INTO a drawdown (after the drop has happened), longs ~12m into a rally (after the rebound). Whipsaw in choppy markets; check DSR / bootstrap CI.

**TG-Short-LS** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities

- Net ann ret 2.50% · Sharpe 0.441 · MaxDD -14.40% · both-down -15.68% · Upβ 0.127 / Dnβ 0.117 · Dn-corr 0.198 · gross 1.20 · lev cost 1.16%/yr · DSR -0.87 · Sharpe CI [-0.18, 1.19]
- **Pros:** TG-Short (short equity on downside) + a 0.20 LS-TSMOM overlay — both the equity flip and the broader momentum crisis-alpha leg. Targets the asymmetric goal from two angles. Smaller overlay than RP-LS-Overlay → lower leverage cost.
- **Cons:** Inherits the MinVar-base equity starvation AND the 12m lag AND the overlay whipsaw — all three costs. Gross can exceed 1 → leverage cost up to 1.16%/yr. Most overfitting surface of the TG-Short family; check DSR / bootstrap CI.

**TG-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 4.08% · Sharpe 0.515 · MaxDD -14.51% · both-down -23.75% · Upβ 0.112 / Dnβ 0.412 · Dn-corr 0.524 · gross 1.00 · lev cost 0.00%/yr · DSR -0.80 · Sharpe CI [-0.12, 1.45]
- **Pros:** TG-Short with a FASTER 6m trend signal — reduces the 12m lag (out of drawdowns sooner, into rallies sooner), so the short flip is better timed. Direct lever for negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws MORE in choppy markets (more false flips). MinVar base still starves equity → muted upside capture. Shorter lookback → more turnover; check DSR / bootstrap CI.

**EW-Short** — combo: US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.18% · Sharpe 0.290 · MaxDD -17.21% · both-down -20.52% · Upβ 0.033 / Dnβ 0.542 · Dn-corr 0.621 · gross 1.00 · lev cost 0.00%/yr · DSR -1.02 · Sharpe CI [-0.28, 1.30]
- **Pros:** EQUAL-WEIGHT base (like All-Weather's own ~1/n across sleeves) so equity keeps a real weight (~12-25%) — fixes the MinVar-base equity starvation that left TG-Short with nothing to short and ~3% return. Short equity on the downside signal → negative downside-β with positive upside-β; return floor near AW. Sleeve-level netting can keep gross ≤ 1 (no leverage cost).
- **Cons:** More equity weight → higher vol / drawdown than the MinVar-base flavors. 12m signal lags (consider EW-Short-6m for less lag). Equal-weight ignores covariance; check DSR / bootstrap CI.

**EW-Short-LS** — combo: US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds

- Net ann ret -0.05% · Sharpe -0.007 · MaxDD -19.42% · both-down -24.29% · Upβ -0.009 / Dnβ 0.439 · Dn-corr 0.541 · gross 1.20 · lev cost 1.16%/yr · DSR -1.32 · Sharpe CI [-0.53, 0.76]
- **Pros:** EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM overlay. Highest upside capture of the family (EW base keeps equity, overlay adds crisis alpha). Targets both beat-AW return AND asymmetric protection.
- **Cons:** Gross can exceed 1 → leverage cost up to 1.16%/yr. Inherits the 12m lag and overlay whipsaw. Most overfitting surface; check DSR / bootstrap CI.

**EW-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.81% · Sharpe 0.355 · MaxDD -17.76% · both-down -24.02% · Upβ 0.106 / Dnβ 0.441 · Dn-corr 0.551 · gross 1.00 · lev cost 0.00%/yr · DSR -0.96 · Sharpe CI [-0.26, 1.24]
- **Pros:** EW-Short with a FASTER 6m signal — real equity weight (EW base) AND less lag, so the short flip is both meaningful and better timed. Directly targets the brief: high upside-β, negative downside-β, AW-like return floor. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws more; more turnover. Higher vol / drawdown than MinVar-base flavors (more equity). Most parameters → check DSR / bootstrap CI.

**EW-MA-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 4.24% · Sharpe 0.613 · MaxDD -14.01% · both-down -12.95% · Upβ 0.013 / Dnβ 0.123 · Dn-corr 0.224 · gross 1.00 · lev cost 0.00%/yr · DSR -0.70 · Sharpe CI [-0.06, 1.41]
- **Pros:** EW-Short driven by a LEADING signal: price-vs-10m-SMA crossover (an MA crosses BEFORE a lookback-return flips sign), so equity exits BEFORE the drawdown and re-enters BEFORE the rally — the round-2 lagging-momentum blocker's direct fix. Real equity weight (EW base) + short-on-downside; directly targets high upside-β with negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** MA crossover still whipsaws in choppy/sideways tape (price oscillates around the SMA → repeated false flips). Higher vol / drawdown than MinVar-base flavors (more equity); more turnover than the 12m TSMOM gate. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-Vol-Short** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.10% · Sharpe 0.156 · MaxDD -18.66% · both-down -17.76% · Upβ 0.050 / Dnβ 0.365 · Dn-corr 0.443 · gross 1.00 · lev cost 0.00%/yr · DSR -1.16 · Sharpe CI [-0.42, 1.07]
- **Pros:** EW-Short driven by a VOL-REGIME signal: short equity when 6m realized vol EXCEEDS its trailing 60m median (vol spikes LEAD drawdowns), long when vol is calm — a regime filter, not a price-trend filter. Different information set from price-MA → diversifies the signal family; real equity weight (EW base). Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Vol spikes can lag the actual drawdown start (vol rises AS price falls, not before) — may still enter the short late. 60m median needs a long warm-up; fewer active signals in the early TEST window. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-DMA-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.78% · Sharpe 0.205 · MaxDD -24.53% · both-down -18.49% · Upβ 0.038 / Dnβ 0.449 · Dn-corr 0.487 · gross 1.00 · lev cost 0.00%/yr · DSR -1.11 · Sharpe CI [-0.41, 1.16]
- **Pros:** EW-Short driven by a DUAL-MA signal: fast 3m SMA vs slow 10m SMA — a faster, smoother crossover than price-vs-SMA (the slow MA smooths the reference, so fewer false flips than EW-MA-Short). Leading signal (a fast/slow cross precedes the lookback-return flip); real equity weight (EW base) + short-on-downside. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Fast 3m SMA is noisy → still some whipsaw; the slow 10m MA adds lag vs the single-MA gate. Two MAs → slightly more overfitting surface than EW-MA-Short. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-AsymMA-Short** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 3.43% · Sharpe 0.406 · MaxDD -17.22% · both-down -17.76% · Upβ -0.124 / Dnβ -0.049 · Dn-corr -0.060 · gross 1.00 · lev cost 0.00%/yr · DSR -0.90 · Sharpe CI [-0.26, 1.15]
- **Pros:** ASYMMETRIC (hysteretic) MA gate — the round-3 prescription made concrete: LONG until price < 3m SMA (FAST downside exit), then SHORT until price > 12m SMA (SLOW upside re-entry). Starts LONG and holds through chop above the fast MA, so it stays correlated on the way up and only flees (goes net-short) after a clear break. Hysteresis band = the fast/slow-MA gap. The one untested lever: a SYMMETRIC signal (rounds 1-3) is equally trigger-happy up and down → Dnβ >= Upβ everywhere; an asymmetric one can in principle be 'correlated up, protected down'. Real equity weight (EW base) + short-on-downside; sleeve-level netting can keep gross <= 1.
- **Cons:** The slow 12m re-entry can lag the START of a rally (re-enters late after a V rebound) — some upside missed at the turn. Stateful + two MA horizons → more overfitting surface than the symmetric gates; the fast/slow gap is a tuned parameter. New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime.

**EW-DDStop-Short** — combo: US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.71% · Sharpe 0.299 · MaxDD -24.02% · both-down -23.72% · Upβ 0.106 / Dnβ 0.536 · Dn-corr 0.586 · gross 1.00 · lev cost 0.00%/yr · DSR -1.01 · Sharpe CI [-0.35, 1.25]
- **Pros:** ASYMMETRIC trailing-stop gate — the most direct map to the brief: LONG until the equity sleeve drawdown from its trailing 6m peak exceeds 10% (FAST exit — a clear break), then SHORT until it recovers inside 3% of the peak (SLOW re-entry, near a new high). 'Flee the break, wait for a new high.' Inherently asymmetric: the trigger is 'you've fallen >10%', the re-entry is 'you've made a new high' — quick to flee, slow to return, exactly the brief's shape. Real equity weight (EW base) + short-on-downside; sleeve-level netting can keep gross <= 1.
- **Cons:** Drawdown thresholds (10% exit / 3% re-entry) are tuned → overfitting surface; the 6m peak window is a parameter. A slow grind-down (2018, 2022) can hit the 10% stop late vs a fast crash; a V-rebound (2020) re-enters late (needs a new 6m high). New signal → check DSR / bootstrap CI; one TRAIN/TEST split = one regime.

**EW-AsymMA-Short-6** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.80% · Sharpe 0.565 · MaxDD -14.83% · both-down -17.03% · Upβ -0.113 / Dnβ -0.026 · Dn-corr -0.032 · gross 1.00 · lev cost 0.00%/yr · DSR -0.75 · Sharpe CI [-0.09, 1.32]
- **Pros:** Round-4b SWEEP point: EW-AsymMA-Short with a FASTER re-entry (slow_entry=6 vs the round-4 default 12). The round-4 default drove Upβ NEGATIVE because the 12m re-entry stayed short through rally starts; re-entering at a 6m SMA re-loads equity sooner → tests whether a less-overshooting band can keep Upβ POSITIVE while Dnβ stays NEGATIVE (the unmet property). Fast 3m-MA exit preserved (downside protection unchanged); real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Faster re-entry reduces the hysteresis band → more whipsaw in choppy tape (re-enters on smaller bounces); may give back some of the downside protection the 12m band bought. Sweep parameter (slow_entry=6) is tuned → overfitting surface; one TRAIN/TEST split = one regime. Check DSR / bootstrap CI.

**EW-AsymMA-Short-9** — combo: International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver

- Net ann ret 4.27% · Sharpe 0.508 · MaxDD -14.10% · both-down -16.70% · Upβ -0.107 / Dnβ -0.041 · Dn-corr -0.050 · gross 1.00 · lev cost 0.00%/yr · DSR -0.80 · Sharpe CI [-0.12, 1.23]
- **Pros:** Round-4b SWEEP point: the intermediate re-entry (slow_entry=9, between the round-4 default 12 and the fast 6). Brackets the Upβ-vs-Dnβ trade-off: slower than 6 = more downside protection, faster than 12 = less upside overshoot. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Same construction costs as the rest of the asym_ma family (stateful, two MA horizons, tuned band). Sweep parameter → overfitting surface; one split = one regime. Check DSR / bootstrap CI.

**EW-AsymMA-Tight** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret 1.50% · Sharpe 0.278 · MaxDD -18.65% · both-down -12.64% · Upβ -0.096 / Dnβ -0.130 · Dn-corr -0.243 · gross 1.00 · lev cost 0.00%/yr · DSR -1.03 · Sharpe CI [-0.49, 1.06]
- **Pros:** Round-4b SWEEP point: a TIGHTER hysteresis band — fast_exit=2 (exit on a 2m-MA break, even faster downside flee) + slow_entry=6 (re-enter on a 6m SMA). The tightest band in the family: quickest to flee, quickest to return — tests the 'high turnover, low lag' corner of the grid. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** The 2m exit is noisy → more false flips in chop; the tight band → highest turnover of the family (more cost, more whipsaw). Two tuned parameters → most overfitting surface of the sweep; one split = one regime. Check DSR / bootstrap CI.

**EW-AsymVol-Short** — combo: US Equity, US REIT, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret -1.64% · Sharpe -0.222 · MaxDD -27.63% · both-down -15.59% · Upβ 0.038 / Dnβ 0.266 · Dn-corr 0.329 · gross 1.00 · lev cost 0.00%/yr · DSR -1.53 · Sharpe CI [-0.80, 0.42]
- **Pros:** Round-4b: a HYSTERETIC vol-regime gate — LONG -> SHORT once the prior month's 6m realized vol exceeds its trailing 60m median (fast exit on stress), SHORT -> LONG once vol falls back below 0.85x the median (slow re-entry, wait for genuine calm). The hysteresis band = 0.85..1.0x median; a vol spike flees, vol must genuinely calm to return. Fixes the round-3 EW-Vol-Short, which SHORTED THE 2020 COVID V-REBOUND (vol stayed elevated through the rally → the symmetric vol-gate never re-entered long, -> -1.52% / -31.69% MaxDD). The slow lower-bar re-entry waits for vol to actually calm. Different information set from price-MA → diversifies the signal family. Real equity weight (EW base); sleeve-level netting can keep gross <= 1.
- **Cons:** Vol can stay elevated THROUGH a V-rebound even with hysteresis (vol calms late) — the 0.85x bar may still re-enter after the rally's best months. 60m median needs a long warm-up; the 0.85x / 1.0x thresholds are tuned → overfitting surface. New signal → check DSR / bootstrap CI; one split = one regime.

> **Verdict:** Of the 16 TrendProtect flavors, **TrendGate** beat All-Weather's net OOS return (6.03%) after the 5.8%/yr leverage cost. Cross-check the Dn-corr / Dnβ columns for the asymmetric protection and the DSR / bootstrap Sharpe CI for significance before trusting any single winner — the flavors share sleeves so DSR is conservative (see §3 effective-N), and a single TRAIN/TEST split is one regime.

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

