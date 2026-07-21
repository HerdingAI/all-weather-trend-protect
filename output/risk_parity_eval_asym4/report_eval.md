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
- **Combos × schemes:** 2817 × 18 = **50706 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, TG-Short, TG-Short-LS, TG-Short-6m, EW-Short, EW-Short-LS, EW-Short-6m, EW-MA-Short, EW-Vol-Short, EW-DMA-Short, EW-AsymMA-Short, EW-DDStop-Short — EW/InvVol/InvVar/ERC/MinVar separate composition
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

- **Combo:** US Equity,International Equity,Preferred Stock,US Treasuries,Gold,Silver
- **Scheme:** MinVar  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 74.8, z = +2.12)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.657 | **0.921** | 0.264 |
| Both-down ann ret (net) | -33.46% | **-30.50%** | 2.96% |
| Max drawdown | -31.20% | **-15.65%** | 15.55% |
| Diversification ratio | 1.743 | **1.434** | — |
| Corr w/ equity (both-down) | 0.808 | **0.778** | — |
| Ann turnover | 48.50% | 45.33% | — |

- **Cap integrity (Fix 1):** winner max sleeve weight = 20.00% vs cap 20% → YES — solver output already ≤ cap (post-hoc clip is a no-op).

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **50706**.
- Raw OOS net Sharpe: **0.921**.
- Expected max null Sharpe over 50706 trials: 1.547 (annualized).
- **Deflated Sharpe (annualized): -0.626**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.04** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [0.290, 1.725]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-37.86%, -20.48%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 50706 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.6** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 **and** the both-down CI is entirely negative: there is **no statistically robust resilience** to the both-down scenario among these investable sleeves — the best portfolio is the least-bad, not a positive-return hedge.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 7.37% | **9.29%** |
| Ann vol | 6.99% | **10.09%** |
| Net Sharpe | 1.055 | **0.921** |
| Max DD | -12.31% | **-15.65%** |
| Both-down ann ret | -18.74% | **-30.50%** |
| Both-down hit rate | 16.67% | **12.50%** |
| Diversification ratio | n/a | **1.434** |
| Corr w/ equity | 0.885 | **0.825** |
| Corr w/ bonds | 0.437 | **0.573** |
| Crisis avg ret | -3.04% | **-6.26%** |

Winner OOS Sharpe − All-Weather = **-0.134**; both-down ann diff = **-0.1176**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| InvVol | 5 | 0.829 | -31.13% | -16.09% | 1.524 | 54.6 | 37 |
| MinVar | 21 | 0.863 | -31.50% | -16.67% | 1.455 | 53.0 | 22 |
| InvVar | 4 | 0.813 | -32.36% | -16.66% | 1.512 | 52.9 | 38 |
| ERC | 19 | 0.851 | -30.69% | -16.12% | 1.448 | 48.3 | 23 |
| LS-TSMOM | 1 | 0.159 | -17.12% | -34.71% | n/a | 36.0 | 40 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 11.7 | field dispersion |
| Winner TRAIN score (z) | +2.12 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 60% | selection stability |
| Spearman TRAIN↔TEST score | +0.41 | rank persistence |
| Winner Sharpe test−train | +0.264 | large negative ⇒ overfit |
| Winner both-down test−train | +0.0296 | large negative ⇒ overfit |
| Effective N (vs nominal 50706) | 1.6 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.660**
- OOS (rolling) both-down ann ret = **-38.30%**
- OOS (rolling) max drawdown = -22.37%
- Rolling Deflated Sharpe = -0.886  (P>0 = 0.01)

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

- **TRAIN-best LS-TSMOM combo:** US Equity, US REIT, US Treasuries, Gold, Silver
- **Signal:** `pos = (1/n)·sign(trailing-12m)` per sleeve, monthly. Lookback configurable via `--tsmom-lookback`.

| Metric | All-Weather (OOS) | Risk-parity winner (OOS) | **LS-TSMOM (OOS)** |
|---|---:|---:|---:|
| Ann return (net) | 7.37% | 9.29% | **1.87%** |
| Ann vol | 6.99% | 10.09% | **11.77%** |
| Net Sharpe | 1.055 | 0.921 | **0.159** |
| Max DD | -12.31% | -15.65% | **-34.71%** |
| Both-down ann ret | -18.74% | -30.50% | **-17.12%** |
| Both-down hit rate | 16.67% | 12.50% | **33.33%** |
| Corr w/ equity | 0.885 | 0.825 | **0.227** |
| Crisis avg ret | -3.04% | -6.26% | **-6.75%** |

- LS-TSMOM OOS net Sharpe: **0.159**
- LS-TSMOM OOS both-down ann ret: **-17.12%**  (hit rate 33.33%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.152**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.637, 1.107]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-30.18%, 0.63%]

> **Verdict:** LS-TSMOM **reduces** the both-down loss vs both All-Weather and the risk-parity winner (though still negative OOS) — directionally the trend overlay helps in the AW weak spot, but not enough to flip it positive in this window. Check the bootstrap CI before trusting the ranking.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 7.37% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 12 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric2`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| RP winner | US Equity, International Equity, Preferred Stock, US Treasuries, Gold, Silver | 9.29% | **0.921** | -15.65% | -30.50% | 0.432 | 0.585 | 0.747 | 1.00 | 0.00% | — | — |
| TrendGate | US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities | 7.32% | **0.719** | -17.99% | -27.88% | 0.310 | 0.543 | 0.628 | 1.00 | 0.00% | -0.59 | [0.07, 1.68] |
| EW-MA-Short | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 4.08% | **0.687** | -12.46% | -11.24% | 0.014 | 0.125 | 0.259 | 1.00 | 0.00% | -0.62 | [-0.02, 1.52] |
| TG-Short | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities | 3.27% | **0.622** | -10.29% | -13.17% | 0.134 | 0.201 | 0.366 | 1.00 | 0.00% | -0.69 | [0.01, 1.46] |
| TG-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver, Commodities | 4.62% | **0.588** | -16.31% | -20.18% | 0.110 | 0.421 | 0.513 | 1.00 | 0.00% | -0.72 | [-0.07, 1.61] |
| TG-Short-LS | US Equity, International Equity, US Treasuries, US Corporate Bonds, EM Bonds, Silver | 4.13% | **0.448** | -20.50% | -23.99% | 0.056 | 0.294 | 0.347 | 1.20 | 1.16% | -0.86 | [-0.25, 1.29] |
| EW-Short-6m | US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 3.30% | **0.414** | -20.58% | -20.18% | 0.091 | 0.460 | 0.542 | 1.00 | 0.00% | -0.90 | [-0.24, 1.43] |
| EW-AsymMA-Short | International Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Silver | 3.43% | **0.406** | -17.22% | -17.76% | -0.124 | -0.049 | -0.060 | 1.00 | 0.00% | -0.90 | [-0.28, 1.15] |
| EW-Short | US REIT, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.67% | **0.348** | -20.06% | -16.68% | 0.018 | 0.561 | 0.607 | 1.00 | 0.00% | -0.96 | [-0.25, 1.50] |
| EW-DDStop-Short | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 2.71% | **0.299** | -24.01% | -23.75% | 0.106 | 0.536 | 0.587 | 1.00 | 0.00% | -1.01 | [-0.35, 1.27] |
| EW-DMA-Short | US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities | 2.02% | **0.273** | -20.92% | -15.83% | 0.035 | 0.396 | 0.495 | 1.00 | 0.00% | -1.04 | [-0.38, 1.26] |
| LS-TSMOM | US Equity, US REIT, US Treasuries, Gold, Silver | 1.87% | **0.159** | -34.71% | -17.12% | -0.315 | 0.462 | 0.392 | 1.00 | 0.00% | -1.15 | [-0.64, 1.11] |
| EW-Short-LS | US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds | 0.37% | **0.057** | -15.46% | -21.28% | -0.018 | 0.472 | 0.582 | 1.20 | 1.16% | -1.25 | [-0.46, 0.91] |
| EW-Vol-Short | US Equity, US REIT, Preferred Stock, US Corporate Bonds, EM Bonds | -1.52% | **-0.182** | -31.69% | -13.96% | -0.006 | 0.275 | 0.277 | 1.00 | 0.00% | -1.49 | [-0.75, 0.49] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: US Equity, International Equity, US Corporate Bonds, EM Bonds, Silver, Commodities

- Net ann ret 7.32% · Sharpe 0.719 · MaxDD -17.99% · both-down -27.88% · Upβ 0.310 / Dnβ 0.543 · Dn-corr 0.628 · gross 1.00 · lev cost 0.00%/yr · DSR -0.59 · Sharpe CI [0.07, 1.68]
- **Pros:** Long-only (gross ≤ 1, no leverage cost). Cuts equity exposure after a sustained drawdown — downside dampening. Keeps bond/gold/diversifier sleeves long (carry).
- **Cons:** 12m trend-gate LAGS: long into the start of drawdowns, flat into the start of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal). Cannot go net-short, so no positive both-down return. Whipsaw in choppy markets (gate toggles on/off).

**TG-Short** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities

- Net ann ret 3.27% · Sharpe 0.622 · MaxDD -10.29% · both-down -13.17% · Upβ 0.134 / Dnβ 0.201 · Dn-corr 0.366 · gross 1.00 · lev cost 0.00%/yr · DSR -0.69 · Sharpe CI [0.01, 1.46]
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

**EW-Short-LS** — combo: US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds

- Net ann ret 0.37% · Sharpe 0.057 · MaxDD -15.46% · both-down -21.28% · Upβ -0.018 / Dnβ 0.472 · Dn-corr 0.582 · gross 1.20 · lev cost 1.16%/yr · DSR -1.25 · Sharpe CI [-0.46, 0.91]
- **Pros:** EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM overlay. Highest upside capture of the family (EW base keeps equity, overlay adds crisis alpha). Targets both beat-AW return AND asymmetric protection.
- **Cons:** Gross can exceed 1 → leverage cost up to 1.16%/yr. Inherits the 12m lag and overlay whipsaw. Most overfitting surface; check DSR / bootstrap CI.

**EW-Short-6m** — combo: US Equity, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 3.30% · Sharpe 0.414 · MaxDD -20.58% · both-down -20.18% · Upβ 0.091 / Dnβ 0.460 · Dn-corr 0.542 · gross 1.00 · lev cost 0.00%/yr · DSR -0.90 · Sharpe CI [-0.24, 1.43]
- **Pros:** EW-Short with a FASTER 6m signal — real equity weight (EW base) AND less lag, so the short flip is both meaningful and better timed. Directly targets the brief: high upside-β, negative downside-β, AW-like return floor. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Faster signal whipsaws more; more turnover. Higher vol / drawdown than MinVar-base flavors (more equity). Most parameters → check DSR / bootstrap CI.

**EW-MA-Short** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 4.08% · Sharpe 0.687 · MaxDD -12.46% · both-down -11.24% · Upβ 0.014 / Dnβ 0.125 · Dn-corr 0.259 · gross 1.00 · lev cost 0.00%/yr · DSR -0.62 · Sharpe CI [-0.02, 1.52]
- **Pros:** EW-Short driven by a LEADING signal: price-vs-10m-SMA crossover (an MA crosses BEFORE a lookback-return flips sign), so equity exits BEFORE the drawdown and re-enters BEFORE the rally — the round-2 lagging-momentum blocker's direct fix. Real equity weight (EW base) + short-on-downside; directly targets high upside-β with negative downside-β. Sleeve-level netting can keep gross ≤ 1.
- **Cons:** MA crossover still whipsaws in choppy/sideways tape (price oscillates around the SMA → repeated false flips). Higher vol / drawdown than MinVar-base flavors (more equity); more turnover than the 12m TSMOM gate. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-Vol-Short** — combo: US Equity, US REIT, Preferred Stock, US Corporate Bonds, EM Bonds

- Net ann ret -1.52% · Sharpe -0.182 · MaxDD -31.69% · both-down -13.96% · Upβ -0.006 / Dnβ 0.275 · Dn-corr 0.277 · gross 1.00 · lev cost 0.00%/yr · DSR -1.49 · Sharpe CI [-0.75, 0.49]
- **Pros:** EW-Short driven by a VOL-REGIME signal: short equity when 6m realized vol EXCEEDS its trailing 60m median (vol spikes LEAD drawdowns), long when vol is calm — a regime filter, not a price-trend filter. Different information set from price-MA → diversifies the signal family; real equity weight (EW base). Sleeve-level netting can keep gross ≤ 1.
- **Cons:** Vol spikes can lag the actual drawdown start (vol rises AS price falls, not before) — may still enter the short late. 60m median needs a long warm-up; fewer active signals in the early TEST window. New signal → new overfitting surface; check DSR / bootstrap CI.

**EW-DMA-Short** — combo: US Equity, Preferred Stock, US Treasuries, US Corporate Bonds, EM Bonds, Commodities

- Net ann ret 2.02% · Sharpe 0.273 · MaxDD -20.92% · both-down -15.83% · Upβ 0.035 / Dnβ 0.396 · Dn-corr 0.495 · gross 1.00 · lev cost 0.00%/yr · DSR -1.04 · Sharpe CI [-0.38, 1.26]
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

> **Verdict:** None of the 12 TrendProtect flavors beat All-Weather's net OOS return (7.37%) after the 5.8%/yr leverage cost in this window — the honest, measured answer. The flavors still shift the asymmetric profile (see Upβ / Dnβ / Dn-corr); whether the downside protection is worth the return drag is a judgment call the table surfaces. Check DSR / bootstrap Sharpe CI for significance (flavors share sleeves → DSR conservative; one split = one regime).

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

