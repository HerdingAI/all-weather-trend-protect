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
- **Combos × schemes:** 2817 × 16 = **45072 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, TG-Short, TG-Short-LS, TG-Short-6m, EW-Short, EW-Short-LS, EW-Short-6m, EW-MA-Short, EW-Vol-Short, EW-DMA-Short — EW/InvVol/InvVar/ERC/MinVar separate composition
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

- **Combo:** US Equity,Preferred Stock,US Corporate Bonds,EM Bonds,Gold,Silver
- **Scheme:** ERC  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 75.2, z = +2.12)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.722 | **0.783** | 0.062 |
| Both-down ann ret (net) | -33.94% | **-32.44%** | 1.50% |
| Max drawdown | -28.90% | **-18.15%** | 10.74% |
| Diversification ratio | 1.623 | **1.451** | — |
| Corr w/ equity (both-down) | 0.762 | **0.781** | — |
| Ann turnover | 45.44% | 37.84% | — |

- **Cap integrity (Fix 1):** winner max sleeve weight = 20.00% vs cap 20% → YES — solver output already ≤ cap (post-hoc clip is a no-op).

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **45072**.
- Raw OOS net Sharpe: **0.783**.
- Expected max null Sharpe over 45072 trials: 1.538 (annualized).
- **Deflated Sharpe (annualized): -0.754**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.02** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [0.143, 1.584]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-41.00%, -20.99%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 45072 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.6** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 **and** the both-down CI is entirely negative: there is **no statistically robust resilience** to the both-down scenario among these investable sleeves — the best portfolio is the least-bad, not a positive-return hedge.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 6.03% | **7.82%** |
| Ann vol | 7.79% | **9.98%** |
| Net Sharpe | 0.774 | **0.783** |
| Max DD | -16.26% | **-18.15%** |
| Both-down ann ret | -29.27% | **-32.44%** |
| Both-down hit rate | 4.17% | **4.17%** |
| Diversification ratio | n/a | **1.451** |
| Corr w/ equity | 0.827 | **0.790** |
| Corr w/ bonds | 0.784 | **0.664** |
| Crisis avg ret | -5.28% | **-7.22%** |

Winner OOS Sharpe − All-Weather = **+0.009**; both-down ann diff = **-0.0317**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MinVar | 22 | 0.817 | -33.13% | -18.30% | 1.425 | 53.2 | 25 |
| InvVol | 4 | 0.773 | -32.58% | -18.04% | 1.502 | 51.0 | 30 |
| ERC | 20 | 0.807 | -32.46% | -17.75% | 1.432 | 49.1 | 25 |
| InvVar | 4 | 0.769 | -32.37% | -17.95% | 1.498 | 48.2 | 28 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 11.9 | field dispersion |
| Winner TRAIN score (z) | +2.12 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 50% | selection stability |
| Spearman TRAIN↔TEST score | +0.44 | rank persistence |
| Winner Sharpe test−train | +0.062 | large negative ⇒ overfit |
| Winner both-down test−train | +0.0150 | large negative ⇒ overfit |
| Effective N (vs nominal 45072) | 1.6 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.654**
- OOS (rolling) both-down ann ret = **-39.27%**
- OOS (rolling) max drawdown = -22.04%
- Rolling Deflated Sharpe = -0.884  (P>0 = 0.01)

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

- **TRAIN-best LS-TSMOM combo:** US Equity, US REIT, US Corporate Bonds, Gold, Silver
- **Signal:** `pos = (1/n)·sign(trailing-12m)` per sleeve, monthly. Lookback configurable via `--tsmom-lookback`.

| Metric | All-Weather (OOS) | Risk-parity winner (OOS) | **LS-TSMOM (OOS)** |
|---|---:|---:|---:|
| Ann return (net) | 6.03% | 7.82% | **2.31%** |
| Ann vol | 7.79% | 9.98% | **12.28%** |
| Net Sharpe | 0.774 | 0.783 | **0.188** |
| Max DD | -16.26% | -18.15% | **-32.90%** |
| Both-down ann ret | -29.27% | -32.44% | **-15.38%** |
| Both-down hit rate | 4.17% | 4.17% | **33.33%** |
| Corr w/ equity | 0.827 | 0.790 | **0.203** |
| Crisis avg ret | -5.28% | -7.22% | **-6.40%** |

- LS-TSMOM OOS net Sharpe: **0.188**
- LS-TSMOM OOS both-down ann ret: **-15.38%**  (hit rate 33.33%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.123**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.578, 1.134]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-30.07%, 4.66%]

> **Verdict:** LS-TSMOM **reduces** the both-down loss vs both All-Weather and the risk-parity winner (though still negative OOS) — directionally the trend overlay helps in the AW weak spot, but not enough to flip it positive in this window. Check the bootstrap CI before trusting the ranking.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 6.03% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 10 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric2`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RP winner | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Gold, Silver | 7.82% | **0.783** | -18.15% | -32.44% | 0.409 | 0.589 | 0.701 | 1.00 | 0.00% | — | — |
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 6.03% | **0.774** | -16.26% | -29.27% | 0.366 | 0.423 | 0.658 | 1.00 | 0.00% | — | — |
| TG-Short-6m | US Equity, International Equity, US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Gold, Commodities | 4.86% | **0.726** | -12.83% | -16.65% | 0.104 | 0.267 | 0.406 | 1.00 | 0.00% | -0.58 | [0.04, 1.60] |
| EW-MA-Short | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 3.67% | **0.621** | -10.34% | -14.43% | 0.026 | 0.109 | 0.235 | 1.00 | 0.00% | -0.69 | [-0.04, 1.34] |
| TrendGate | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities | 4.89% | **0.609** | -16.99% | -25.84% | 0.248 | 0.448 | 0.627 | 1.00 | 0.00% | -0.70 | [-0.09, 1.53] |
| TG-Short | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities | 2.66% | **0.488** | -14.50% | -16.65% | 0.137 | 0.179 | 0.327 | 1.00 | 0.00% | -0.82 | [-0.23, 1.28] |
| TG-Short-LS | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver | 3.46% | **0.382** | -22.07% | -26.29% | 0.040 | 0.228 | 0.283 | 1.20 | 1.16% | -0.93 | [-0.31, 1.20] |
| EW-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.81% | **0.355** | -17.76% | -24.02% | 0.106 | 0.441 | 0.551 | 1.00 | 0.00% | -0.96 | [-0.26, 1.26] |
| EW-Short | US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.18% | **0.290** | -17.21% | -20.52% | 0.033 | 0.542 | 0.621 | 1.00 | 0.00% | -1.02 | [-0.28, 1.32] |
| EW-DMA-Short | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 1.61% | **0.225** | -18.59% | -19.04% | 0.047 | 0.381 | 0.515 | 1.00 | 0.00% | -1.09 | [-0.37, 1.11] |
| LS-TSMOM | US Equity, US REIT, US Corporate Bonds, Gold, Silver | 2.31% | **0.188** | -32.90% | -15.38% | -0.306 | 0.444 | 0.361 | 1.00 | 0.00% | -1.12 | [-0.58, 1.13] |
| EW-Short-LS | US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds | -0.05% | **-0.007** | -19.42% | -24.29% | -0.009 | 0.439 | 0.541 | 1.20 | 1.16% | -1.32 | [-0.56, 0.76] |
| EW-Vol-Short | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds | -1.61% | **-0.251** | -30.50% | -18.24% | -0.037 | 0.220 | 0.309 | 1.00 | 0.00% | -1.56 | [-0.95, 0.46] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 4.89% · Sharpe 0.609 · MaxDD -16.99% · both-down -25.84% · Upβ 0.248 / Dnβ 0.448 · Dn-corr 0.627 · gross 1.00 · lev cost 0.00%/yr · DSR -0.70 · Sharpe CI [-0.09, 1.53]
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

**TG-Short-6m** — combo: US Equity, International Equity, US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Gold, Commodities

- Net ann ret 4.86% · Sharpe 0.726 · MaxDD -12.83% · both-down -16.65% · Upβ 0.104 / Dnβ 0.267 · Dn-corr 0.406 · gross 1.00 · lev cost 0.00%/yr · DSR -0.58 · Sharpe CI [0.04, 1.60]
- **Pros:** TG-Short with a FASTER 6m trend signal — reduces the 12m lag (out of drawdowns sooner, into rallies sooner), so the short flip is better timed. Direct lever for negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws MORE in choppy markets (more false flips). MinVar base still starves equity → muted upside capture. Shorter lookback → more turnover; check DSR / bootstrap CI.

**EW-Short** — combo: US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.18% · Sharpe 0.290 · MaxDD -17.21% · both-down -20.52% · Upβ 0.033 / Dnβ 0.542 · Dn-corr 0.621 · gross 1.00 · lev cost 0.00%/yr · DSR -1.02 · Sharpe CI [-0.28, 1.32]
- **Pros:** EQUAL-WEIGHT base (like All-Weather's own ~1/n across sleeves) so equity keeps a real weight (~12-25%) — fixes the MinVar-base equity starvation that left TG-Short with nothing to short and ~3% return. Short equity on the downside signal → negative downside-β with positive upside-β; return floor near AW. Sleeve-level netting can keep gross ≤ 1 (no leverage cost).
- **Cons:** More equity weight → higher vol / drawdown than the MinVar-base flavors. 12m signal lags (consider EW-Short-6m for less lag). Equal-weight ignores covariance; check DSR / bootstrap CI.

**EW-Short-LS** — combo: US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds

- Net ann ret -0.05% · Sharpe -0.007 · MaxDD -19.42% · both-down -24.29% · Upβ -0.009 / Dnβ 0.439 · Dn-corr 0.541 · gross 1.20 · lev cost 1.16%/yr · DSR -1.32 · Sharpe CI [-0.56, 0.76]
- **Pros:** EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM overlay. Highest upside capture of the family (EW base keeps equity, overlay adds crisis alpha). Targets both beat-AW return AND asymmetric protection.
- **Cons:** Gross can exceed 1 → leverage cost up to 1.16%/yr. Inherits the 12m lag and overlay whipsaw. Most overfitting surface; check DSR / bootstrap CI.

**EW-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.81% · Sharpe 0.355 · MaxDD -17.76% · both-down -24.02% · Upβ 0.106 / Dnβ 0.441 · Dn-corr 0.551 · gross 1.00 · lev cost 0.00%/yr · DSR -0.96 · Sharpe CI [-0.26, 1.26]
- **Pros:** EW-Short with a FASTER 6m signal — real equity weight (EW base) AND less lag, so the short flip is both meaningful and better timed. Directly targets the brief: high upside-β, negative downside-β, AW-like return floor. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws more; more turnover. Higher vol / drawdown than MinVar-base flavors (more equity). Most parameters → check DSR / bootstrap CI.

**EW-MA-Short** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.67% · Sharpe 0.621 · MaxDD -10.34% · both-down -14.43% · Upβ 0.026 / Dnβ 0.109 · Dn-corr 0.235 · gross 1.00 · lev cost 0.00%/yr · DSR -0.69 · Sharpe CI [-0.04, 1.34]
- **Pros:** EW-Short driven by a LEADING signal: price-vs-10m-SMA crossover (an MA crosses BEFORE a lookback-return flips sign), so equity exits BEFORE the drawdown and re-enters BEFORE the rally — the round-2 lagging-momentum blocker's direct fix. Real equity weight (EW base) + short-on-downside; directly targets high upside-β with negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** MA crossover still whipsaws in choppy/sideways tape (price oscillates around the SMA → repeated false flips). Higher vol / drawdown than MinVar-base flavors (more equity); more turnover than the 12m TSMOM gate. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-Vol-Short** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds

- Net ann ret -1.61% · Sharpe -0.251 · MaxDD -30.50% · both-down -18.24% · Upβ -0.037 / Dnβ 0.220 · Dn-corr 0.309 · gross 1.00 · lev cost 0.00%/yr · DSR -1.56 · Sharpe CI [-0.95, 0.46]
- **Pros:** EW-Short driven by a VOL-REGIME signal: short equity when 6m realized vol EXCEEDS its trailing 60m median (vol spikes LEAD drawdowns), long when vol is calm — a regime filter, not a price-trend filter. Different information set from price-MA → diversifies the signal family; real equity weight (EW base). Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Vol spikes can lag the actual drawdown start (vol rises AS price falls, not before) — may still enter the short late. 60m median needs a long warm-up; fewer active signals in the early TEST window. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-DMA-Short** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 1.61% · Sharpe 0.225 · MaxDD -18.59% · both-down -19.04% · Upβ 0.047 / Dnβ 0.381 · Dn-corr 0.515 · gross 1.00 · lev cost 0.00%/yr · DSR -1.09 · Sharpe CI [-0.37, 1.11]
- **Pros:** EW-Short driven by a DUAL-MA signal: fast 3m SMA vs slow 10m SMA — a faster, smoother crossover than price-vs-SMA (the slow MA smooths the reference, so fewer false flips than EW-MA-Short). Leading signal (a fast/slow cross precedes the lookback-return flip); real equity weight (EW base) + short-on-downside. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Fast 3m SMA is noisy → still some whipsaw; the slow 10m MA adds lag vs the single-MA gate. Two MAs → slightly more overfitting surface than EW-MA-Short. New signal → new overfitting surface; check DSR / bootstrap CI.

> **Verdict:** None of the 10 TrendProtect flavors beat All-Weather's net OOS return (6.03%) after the 5.8%/yr leverage cost in this window — the honest, measured answer. The flavors still shift the asymmetric profile (see Upβ / Dnβ / Dn-corr); whether the downside protection is worth the return drag is a judgment call the table surfaces. Check DSR / bootstrap Sharpe CI for significance (flavors share sleeves → DSR conservative; one split = one regime).

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

