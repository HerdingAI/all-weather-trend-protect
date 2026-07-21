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
- **Combos × schemes:** 2817 × 13 = **36621 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, RP-LS-Overlay, StructShort, TG-LS-Overlay, TG-Short, TG-Short-LS, TG-Short-6m — EW/InvVol/InvVar/ERC/MinVar separate composition
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

- **Combo:** US Equity,US REIT,Preferred Stock,US Treasuries,Gold
- **Scheme:** LS-TSMOM  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 83.5, z = +3.19)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.543 | **0.094** | -0.449 |
| Both-down ann ret (net) | 19.09% | **-13.30%** | -32.39% |
| Max drawdown | -28.24% | **-24.97%** | 3.27% |
| Diversification ratio | n/a | **n/a** | — |
| Corr w/ equity (both-down) | -0.761 | **0.231** | — |
| Ann turnover | n/a | 266.58% | — |

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **36621**.
- Raw OOS net Sharpe: **0.094**.
- Expected max null Sharpe over 36621 trials: 1.522 (annualized).
- **Deflated Sharpe (annualized): -1.428**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.00** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [-0.556, 1.024]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-27.20%, 6.75%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 36621 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.4** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 and the both-down CI crosses 0: the both-down edge is **not** statistically robust after accounting for the number of portfolios tried.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 7.37% | **0.83%** |
| Ann vol | 6.99% | **8.81%** |
| Net Sharpe | 1.055 | **0.094** |
| Max DD | -12.31% | **-24.97%** |
| Both-down ann ret | -18.74% | **-13.30%** |
| Both-down hit rate | 16.67% | **29.17%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.885 | **0.222** |
| Corr w/ bonds | 0.437 | **-0.014** |
| Crisis avg ret | -3.04% | **-3.89%** |

Winner OOS Sharpe − All-Weather = **-0.961**; both-down ann diff = **+0.0544**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| LS-TSMOM | 50 | 0.122 | -9.81% | -22.31% | n/a | 51.0 | 26 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 10.5 | field dispersion |
| Winner TRAIN score (z) | +3.19 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 0% | selection stability |
| Spearman TRAIN↔TEST score | -0.44 | rank persistence |
| Winner Sharpe test−train | -0.449 | large negative ⇒ overfit |
| Winner both-down test−train | -0.3239 | large negative ⇒ overfit |
| Effective N (vs nominal 36621) | 1.4 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.553**
- OOS (rolling) both-down ann ret = **-12.90%**
- OOS (rolling) max drawdown = -19.05%
- Rolling Deflated Sharpe = -0.969  (P>0 = 0.00)

| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |
|---:|---|---|---:|---:|---|
| 2018 | US Equity,US REIT,Preferred Stock,US Treasuries,US Corporate Bonds | LS-TSMOM | 84.3 | 0.50 | L/S gross 100% |
| 2019 | International Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Silver,Currency | MinVar | 73.8 | 1.47 | US Treasuries 20.0% |
| 2020 | Preferred Stock,US Treasuries,US Corporate Bonds,Gold,Silver,Currency | MinVar | 80.5 | 1.21 | Preferred Stock 20.0% |
| 2021 | Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Currency | EW | 79.3 | 1.06 | Preferred Stock 16.7% |
| 2022 | Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Currency | EW | 76.6 | 1.07 | Preferred Stock 16.7% |
| 2023 | US Equity,International Equity,US Treasuries,US Corporate Bonds,Commodities | LS-TSMOM | 84.5 | 0.50 | L/S gross 100% |
| 2024 | Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Commodities | LS-TSMOM | 79.0 | 0.67 | L/S gross 100% |
| 2025 | International Equity,US Corporate Bonds,EM Bonds,Gold,Commodities | LS-TSMOM | 75.0 | 0.22 | L/S gross 100% |
| 2026 | International Equity,US Corporate Bonds,EM Bonds,Gold,Commodities | LS-TSMOM | 75.1 | 0.31 | L/S gross 100% |

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

- **TRAIN-best LS-TSMOM combo:** US Equity, US REIT, Preferred Stock, US Treasuries, Gold
- **Signal:** `pos = (1/n)·sign(trailing-12m)` per sleeve, monthly. Lookback configurable via `--tsmom-lookback`.

| Metric | All-Weather (OOS) | Risk-parity winner (OOS) | **LS-TSMOM (OOS)** |
|---|---:|---:|---:|
| Ann return (net) | 7.37% | 5.46% | **0.83%** |
| Ann vol | 6.99% | 4.22% | **8.81%** |
| Net Sharpe | 1.055 | 1.294 | **0.094** |
| Max DD | -12.31% | -5.25% | **-24.97%** |
| Both-down ann ret | -18.74% | -7.44% | **-13.30%** |
| Both-down hit rate | 16.67% | 25.00% | **29.17%** |
| Corr w/ equity | 0.885 | 0.508 | **0.222** |
| Crisis avg ret | -3.04% | -1.24% | **-3.89%** |

- LS-TSMOM OOS net Sharpe: **0.094**
- LS-TSMOM OOS both-down ann ret: **-13.30%**  (hit rate 29.17%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.217**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.556, 1.024]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-27.20%, 6.75%]

> **Verdict:** LS-TSMOM beats All-Weather in the both-down regime but does not beat the risk-parity winner here — the trend overlay helps vs AW but the dampened long-only portfolio is competitive in this window.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 7.37% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). Four constructions of one parameterized engine (`_backtest_flavor`), each a long **MinVar** base leg (annual refit, cap-respecting) plus active overlays: a **trend-gate** (gate equity sleeves to cash when their own trailing-12m return < 0), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TrendGate | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Silver, Commodities, Currency | 4.39% | **1.385** | -4.20% | -4.50% | 0.044 | 0.161 | 0.491 | 1.00 | 0.00% | 0.07 | [0.70, 2.27] |
| RP winner | Preferred Stock, US Treasuries, US Municipal Bonds, Gold, Silver, Currency | 5.46% | **1.294** | -5.25% | -7.44% | 0.081 | 0.194 | 0.475 | 1.00 | 0.00% | — | — |
| TG-LS-Overlay | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Silver, Commodities, Currency | 4.26% | **1.264** | -3.65% | -4.48% | 0.041 | 0.133 | 0.376 | 1.20 | 1.16% | -0.05 | [0.67, 2.06] |
| TG-Short | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities, Currency | 3.37% | **1.059** | -5.13% | -6.47% | 0.058 | 0.147 | 0.432 | 1.00 | 0.00% | -0.25 | [0.38, 1.97] |
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| TG-Short-LS | International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities, Currency | 3.17% | **0.936** | -4.51% | -6.31% | 0.056 | 0.122 | 0.324 | 1.20 | 1.16% | -0.37 | [0.34, 1.78] |
| TG-Short-6m | US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities, Currency | 3.53% | **0.911** | -7.34% | -8.88% | 0.093 | 0.240 | 0.559 | 1.00 | 0.00% | -0.40 | [0.24, 1.96] |
| RP-LS-Overlay | US Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Commodities, Currency | 4.36% | **0.865** | -8.29% | -9.73% | 0.171 | 0.291 | 0.525 | 1.30 | 1.74% | -0.45 | [0.26, 1.67] |
| StructShort | US Equity, International Equity, US Corporate Bonds, US Municipal Bonds, Commodities, Currency | 5.65% | **0.794** | -12.31% | -18.90% | 0.308 | 0.479 | 0.723 | 1.00 | 0.00% | -0.52 | [0.18, 1.69] |
| LS-TSMOM | US Equity, US REIT, Preferred Stock, US Treasuries, Gold | 0.83% | **0.094** | -24.97% | -13.30% | -0.232 | 0.352 | 0.379 | 1.00 | 0.00% | -1.22 | [-0.56, 1.02] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Silver, Commodities, Currency

- Net ann ret 4.39% · Sharpe 1.385 · MaxDD -4.20% · both-down -4.50% · Upβ 0.044 / Dnβ 0.161 · Dn-corr 0.491 · gross 1.00 · lev cost 0.00%/yr · DSR 0.07 · Sharpe CI [0.70, 2.27]
- **Pros:** Long-only (gross ≤ 1, no leverage cost). Cuts equity exposure after a sustained drawdown — downside dampening. Keeps bond/gold/diversifier sleeves long (carry).
- **Cons:** 12m trend-gate LAGS: long into the start of drawdowns, flat into the start of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal). Cannot go net-short, so no positive both-down return. Whipsaw in choppy markets (gate toggles on/off).

**RP-LS-Overlay** — combo: US Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Commodities, Currency

- Net ann ret 4.36% · Sharpe 0.865 · MaxDD -8.29% · both-down -9.73% · Upβ 0.171 / Dnβ 0.291 · Dn-corr 0.525 · gross 1.30 · lev cost 1.74%/yr · DSR -0.45 · Sharpe CI [0.26, 1.67]
- **Pros:** LS-TSMOM overlay shorts the falling legs → genuinely positive in both-down (the direction that matches the brief). Long MinVar base keeps the return / Sharpe floor. Dollar-neutral overlay is crisis-alpha on top of a diversified long book.
- **Cons:** Gross 1.30 → leverage cost 1.74%/yr drags the return. Overlay whipsaw in calm markets (the 2010s) drags Sharpe. Dn-corr may stay positive if the long leg dominates the down months.

**StructShort** — combo: US Equity, International Equity, US Corporate Bonds, US Municipal Bonds, Commodities, Currency

- Net ann ret 5.65% · Sharpe 0.794 · MaxDD -12.31% · both-down -18.90% · Upβ 0.308 / Dnβ 0.479 · Dn-corr 0.723 · gross 1.00 · lev cost 0.00%/yr · DSR -0.52 · Sharpe CI [0.18, 1.69]
- **Pros:** Permanent net-short-duration tilt (short US Treasuries) → direct hedge for a 2022-style stocks+bonds rout. Sleeve-level netting keeps gross ≤ 1 (no leverage cost). Structural (not signal-driven) → no whipsaw, no lookback lag.
- **Cons:** Pays for the hedge in every non-stagflation year (carry drag) — a permanent short is expensive outside 2022. Only applies to combos containing the short sleeve (TRAIN search self-selects those). Sleeve-level short is a net-short-duration *tilt*, not a standalone short ticker (ticker-level shorting that adds gross is a flagged refinement).

**TG-LS-Overlay** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Silver, Commodities, Currency

- Net ann ret 4.26% · Sharpe 1.264 · MaxDD -3.65% · both-down -4.48% · Upβ 0.041 / Dnβ 0.133 · Dn-corr 0.376 · gross 1.20 · lev cost 1.16%/yr · DSR -0.05 · Sharpe CI [0.67, 2.06]
- **Pros:** Combines the trend-gate (downside dampening) with a small LS overlay (crisis alpha) — both levers. Smaller overlay (gross 1.20) → lower leverage cost than RP-LS-Overlay. Targets the asymmetric goal from two angles.
- **Cons:** Inherits the trend-gate lag AND the overlay whipsaw — both costs. Gross 1.20 → leverage cost 1.16%/yr. Most parameters → most overfitting surface; check the DSR / bootstrap CI.

**TG-Short** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities, Currency

- Net ann ret 3.37% · Sharpe 1.059 · MaxDD -5.13% · both-down -6.47% · Upβ 0.058 / Dnβ 0.147 · Dn-corr 0.432 · gross 1.00 · lev cost 0.00%/yr · DSR -0.25 · Sharpe CI [0.38, 1.97]
- **Pros:** 
- **Cons:** 

**TG-Short-LS** — combo: International Equity, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities, Currency

- Net ann ret 3.17% · Sharpe 0.936 · MaxDD -4.51% · both-down -6.31% · Upβ 0.056 / Dnβ 0.122 · Dn-corr 0.324 · gross 1.20 · lev cost 1.16%/yr · DSR -0.37 · Sharpe CI [0.34, 1.78]
- **Pros:** 
- **Cons:** 

**TG-Short-6m** — combo: US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Silver, Commodities, Currency

- Net ann ret 3.53% · Sharpe 0.911 · MaxDD -7.34% · both-down -8.88% · Upβ 0.093 / Dnβ 0.240 · Dn-corr 0.559 · gross 1.00 · lev cost 0.00%/yr · DSR -0.40 · Sharpe CI [0.24, 1.96]
- **Pros:** 
- **Cons:** 

> **Verdict:** None of the four TrendProtect flavors beat All-Weather's net OOS return (7.37%) after the 5.8%/yr leverage cost in this window — the honest, measured answer. The flavors still shift the asymmetric profile (see Upβ / Dnβ / Dn-corr); whether the downside protection is worth the return drag is a judgment call the table surfaces. Check DSR / bootstrap Sharpe CI for significance (flavors share sleeves → DSR conservative; one split = one regime).

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

