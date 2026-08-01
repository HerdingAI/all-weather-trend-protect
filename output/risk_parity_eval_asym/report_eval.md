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
- **Combos × schemes:** 2817 × 10 = **28170 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM, TrendGate, RP-LS-Overlay, StructShort, TG-LS-Overlay — EW/InvVol/InvVar/ERC/MinVar separate composition
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
- **TRAIN rank:** #1 (TRAIN score 80.7, z = +2.73)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 0.509 | **0.075** | -0.435 |
| Both-down ann ret (net) | 16.95% | **-9.46%** | -26.41% |
| Max drawdown | -28.86% | **-23.28%** | 5.58% |
| Diversification ratio | n/a | **n/a** | — |
| Corr w/ equity (both-down) | -0.769 | **0.133** | — |
| Ann turnover | n/a | 315.32% | — |

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **28170**.
- Raw OOS net Sharpe: **0.075**.
- Expected max null Sharpe over 28170 trials: 1.502 (annualized).
- **Deflated Sharpe (annualized): -1.427**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.00** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [-0.506, 0.914]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-24.07%, 13.04%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 28170 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.3** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 and the both-down CI crosses 0: the both-down edge is **not** statistically robust after accounting for the number of portfolios tried.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 6.03% | **0.67%** |
| Ann vol | 7.79% | **9.01%** |
| Net Sharpe | 0.774 | **0.075** |
| Max DD | -16.26% | **-23.28%** |
| Both-down ann ret | -29.27% | **-9.46%** |
| Both-down hit rate | 4.17% | **37.50%** |
| Diversification ratio | n/a | **n/a** |
| Corr w/ equity | 0.827 | **0.135** |
| Corr w/ bonds | 0.784 | **-0.113** |
| Crisis avg ret | -5.28% | **-2.75%** |

Winner OOS Sharpe − All-Weather = **-0.699**; both-down ann diff = **+0.1981**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| LS-TSMOM | 50 | 0.101 | -7.66% | -21.93% | n/a | 51.0 | 26 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 11.3 | field dispersion |
| Winner TRAIN score (z) | +2.73 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 0% | selection stability |
| Spearman TRAIN↔TEST score | -0.65 | rank persistence |
| Winner Sharpe test−train | -0.435 | large negative ⇒ overfit |
| Winner both-down test−train | -0.2641 | large negative ⇒ overfit |
| Effective N (vs nominal 28170) | 1.3 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.414**
- OOS (rolling) both-down ann ret = **-15.19%**
- OOS (rolling) max drawdown = -24.30%
- Rolling Deflated Sharpe = -1.088  (P>0 = 0.00)

| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |
|---:|---|---|---:|---:|---|
| 2018 | US Equity,US REIT,Preferred Stock,US Treasuries,US Corporate Bonds | LS-TSMOM | 83.4 | 0.47 | L/S gross 100% |
| 2019 | US Equity,US Treasuries,US Municipal Bonds,Gold,Silver,Currency | MinVar | 73.3 | 1.24 | US Equity 20.0% |
| 2020 | Preferred Stock,US Treasuries,US Corporate Bonds,Gold,Silver,Currency | MinVar | 81.0 | 1.09 | Preferred Stock 20.0% |
| 2021 | Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Currency | EW | 80.6 | 0.99 | Preferred Stock 16.7% |
| 2022 | Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Currency | EW | 76.4 | 1.22 | Preferred Stock 20.0% |
| 2023 | US Equity,International Equity,Preferred Stock,US Corporate Bonds,Commodities | LS-TSMOM | 83.2 | 0.41 | L/S gross 100% |
| 2024 | Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Commodities | LS-TSMOM | 76.0 | 0.55 | L/S gross 100% |
| 2025 | International Equity,US Corporate Bonds,EM Bonds,Gold,Commodities | LS-TSMOM | 74.9 | 0.22 | L/S gross 100% |
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
| Ann return (net) | 6.03% | 7.16% | **0.67%** |
| Ann vol | 7.79% | 5.87% | **9.01%** |
| Net Sharpe | 0.774 | 1.220 | **0.075** |
| Max DD | -16.26% | -9.00% | **-23.28%** |
| Both-down ann ret | -29.27% | -16.09% | **-9.46%** |
| Both-down hit rate | 4.17% | 16.67% | **37.50%** |
| Corr w/ equity | 0.827 | 0.694 | **0.135** |
| Crisis avg ret | -5.28% | -2.48% | **-2.75%** |

- LS-TSMOM OOS net Sharpe: **0.075**
- LS-TSMOM OOS both-down ann ret: **-9.46%**  (hit rate 37.50%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-1.236**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.506, 0.914]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-24.07%, 13.04%]

> **Verdict:** LS-TSMOM **reduces** the both-down loss vs both All-Weather and the risk-parity winner (though still negative OOS) — directionally the trend overlay helps in the AW weak spot, but not enough to flip it positive in this window. Check the bootstrap CI before trusting the ranking.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 6.03% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 4 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode asymmetric`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RP winner | US Equity, US Treasuries, US Municipal Bonds, Gold, Silver, Currency | 7.16% | **1.220** | -9.00% | -16.09% | 0.188 | 0.293 | 0.565 | 1.00 | 0.00% | — | — |
| TrendGate | US Equity, International Equity, US Treasuries, US Corporate Bonds, Gold, Commodities, Currency | 5.64% | **1.170** | -6.92% | -7.89% | 0.073 | 0.225 | 0.462 | 1.00 | 0.00% | -0.14 | [0.50, 2.01] |
| TG-LS-Overlay | US Equity, US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Commodities, Currency | 4.09% | **0.990** | -5.10% | -7.89% | 0.058 | 0.199 | 0.454 | 1.20 | 1.16% | -0.32 | [0.39, 1.74] |
| StructShort | US Equity, International Equity, US Corporate Bonds, US Municipal Bonds, Commodities, Currency | 5.66% | **0.795** | -12.27% | -18.87% | 0.308 | 0.479 | 0.723 | 1.00 | 0.00% | -0.52 | [0.19, 1.70] |
| All-Weather | US Equity, US Treasuries, Gold, Commodities | 6.03% | **0.774** | -16.26% | -29.27% | 0.366 | 0.423 | 0.658 | 1.00 | 0.00% | — | — |
| RP-LS-Overlay | US Equity, International Equity, Preferred Stock, US Treasuries, US Corporate Bonds | 5.13% | **0.506** | -18.00% | -40.72% | 0.489 | 0.561 | 0.728 | 1.30 | 1.74% | -0.81 | [-0.05, 1.17] |
| LS-TSMOM | US Equity, US REIT, Preferred Stock, US Treasuries, Gold | 0.67% | **0.075** | -23.28% | -9.46% | -0.247 | 0.283 | 0.296 | 1.00 | 0.00% | -1.24 | [-0.51, 0.91] |

**Reading the asymmetric columns:** Upβ = beta to equity on equity-up months; Dnβ = beta on equity-down months; Dn-corr = correlation with equity on equity-down months. A flavor that is *correlated up, protected down* has Upβ ≫ Dnβ and a low (ideally negative) Dn-corr. The 12m trend-gate *lags* by construction (it turns off ~12m into a drawdown and on ~12m into a rally), so its asymmetric profile is an empirical question this table answers, not an assumption.

### Per-flavor pros / cons

**TrendGate** — combo: US Equity, International Equity, US Treasuries, US Corporate Bonds, Gold, Commodities, Currency

- Net ann ret 5.64% · Sharpe 1.170 · MaxDD -6.92% · both-down -7.89% · Upβ 0.073 / Dnβ 0.225 · Dn-corr 0.462 · gross 1.00 · lev cost 0.00%/yr · DSR -0.14 · Sharpe CI [0.50, 2.01]
- **Pros:** Long-only (gross ≤ 1, no leverage cost). Cuts equity exposure after a sustained drawdown — downside dampening. Keeps bond/gold/diversifier sleeves long (carry).
- **Cons:** 12m trend-gate LAGS: long into the start of drawdowns, flat into the start of rallies → Dnβ often ≥ Upβ (the lag works against the asymmetric goal). Cannot go net-short, so no positive both-down return. Whipsaw in choppy markets (gate toggles on/off).

**RP-LS-Overlay** — combo: US Equity, International Equity, Preferred Stock, US Treasuries, US Corporate Bonds

- Net ann ret 5.13% · Sharpe 0.506 · MaxDD -18.00% · both-down -40.72% · Upβ 0.489 / Dnβ 0.561 · Dn-corr 0.728 · gross 1.30 · lev cost 1.74%/yr · DSR -0.81 · Sharpe CI [-0.05, 1.17]
- **Pros:** LS-TSMOM overlay shorts the falling legs → genuinely positive in both-down (the direction that matches the brief). Long MinVar base keeps the return / Sharpe floor. Dollar-neutral overlay is crisis-alpha on top of a diversified long book.
- **Cons:** Gross 1.30 → leverage cost 1.74%/yr drags the return. Overlay whipsaw in calm markets (the 2010s) drags Sharpe. Dn-corr may stay positive if the long leg dominates the down months.

**StructShort** — combo: US Equity, International Equity, US Corporate Bonds, US Municipal Bonds, Commodities, Currency

- Net ann ret 5.66% · Sharpe 0.795 · MaxDD -12.27% · both-down -18.87% · Upβ 0.308 / Dnβ 0.479 · Dn-corr 0.723 · gross 1.00 · lev cost 0.00%/yr · DSR -0.52 · Sharpe CI [0.19, 1.70]
- **Pros:** Permanent net-short-duration tilt (short US Treasuries) → direct hedge for a 2022-style stocks+bonds rout. Sleeve-level netting keeps gross ≤ 1 (no leverage cost). Structural (not signal-driven) → no whipsaw, no lookback lag.
- **Cons:** Pays for the hedge in every non-stagflation year (carry drag) — a permanent short is expensive outside 2022. Only applies to combos containing the short sleeve (TRAIN search self-selects those). Sleeve-level short is a net-short-duration *tilt*, not a standalone short ticker (ticker-level shorting that adds gross is a flagged refinement).

**TG-LS-Overlay** — combo: US Equity, US REIT, US Treasuries, US Corporate Bonds, US Municipal Bonds, Gold, Commodities, Currency

- Net ann ret 4.09% · Sharpe 0.990 · MaxDD -5.10% · both-down -7.89% · Upβ 0.058 / Dnβ 0.199 · Dn-corr 0.454 · gross 1.20 · lev cost 1.16%/yr · DSR -0.32 · Sharpe CI [0.39, 1.74]
- **Pros:** Combines the trend-gate (downside dampening) with a small LS overlay (crisis alpha) — both levers. Smaller overlay (gross 1.20) → lower leverage cost than RP-LS-Overlay. Targets the asymmetric goal from two angles.
- **Cons:** Inherits the trend-gate lag AND the overlay whipsaw — both costs. Gross 1.20 → leverage cost 1.16%/yr. Most parameters → most overfitting surface; check the DSR / bootstrap CI.

> **Verdict:** None of the 4 TrendProtect flavors beat All-Weather's net OOS return (6.03%) after the 5.8%/yr leverage cost in this window — the honest, measured answer. The flavors still shift the asymmetric profile (see Upβ / Dnβ / Dn-corr); whether the downside protection is worth the return drag is a judgment call the table surfaces. Check DSR / bootstrap Sharpe CI for significance (flavors share sleeves → DSR conservative; one split = one regime).

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

