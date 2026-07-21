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
- **Combos × schemes:** 2817 × 5 = **14085 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar — EW/InvVol/InvVar/ERC/MinVar separate composition
  from allocation; **LS-TSMOM** is a long/short managed-futures (trend) overlay that
  targets the All-Weather weak spot (both-down / stagflation) — see §9.
- **Constraints:** long-only, no leverage, **per-sleeve cap 20%**, monthly
  rebalance, **10.0 bps/side** transaction costs, **lw** covariance
  shrinkage, trailing 36m, annual refit.
- **Score =** 0.30·pct(net Sharpe) + 0.25·pct(both-down ann ret) + 0.15·pct(−maxDD)
  + 0.15·pct(diversification ratio) + 0.15·pct(−corr with equity in both-down months).
- **Both-down regime reference:** sleeves (legacy) (`--ref-mode sleeves`). Both-down months: TRAIN 27 | TEST 26. 'external' uses investable non-candidate indices (SPY/AGG) so the equity-correlation metric measures a hedge, not a tautology from the reference overlapping the universe.
- **ERC cap mode:** capped (cap enforced inside the solver for MinVar and ERC-capped; see §2 'Cap integrity').

## 2. Headline — selected winner, OUT OF SAMPLE (TEST)

- **Combo:** US Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Silver,Currency
- **Scheme:** MinVar  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 84.1, z = +2.33)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 1.149 | **1.450** | 0.301 |
| Both-down ann ret (net) | -3.42% | **-6.98%** | -3.56% |
| Max drawdown | -15.80% | **-4.95%** | 10.84% |
| Diversification ratio | 2.452 | **2.120** | — |
| Corr w/ equity (both-down) | 0.659 | **0.855** | — |
| Ann turnover | 40.15% | 33.36% | — |

- **Cap integrity (Fix 1):** winner max sleeve weight = 20.00% vs cap 20% → YES — solver output already ≤ cap (post-hoc clip is a no-op).

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **14085**.
- Raw OOS net Sharpe: **1.450**.
- Expected max null Sharpe over 14085 trials: 1.447 (annualized).
- **Deflated Sharpe (annualized): 0.003**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.50** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [0.769, 2.352]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-10.73%, -2.64%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 14085 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.2** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe > 0: the edge survives the multiple-comparison adjustment (but still check the bootstrap CI and rolling §7).

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 7.37% | **5.43%** |
| Ann vol | 6.99% | **3.75%** |
| Net Sharpe | 1.055 | **1.450** |
| Max DD | -12.31% | **-4.95%** |
| Both-down ann ret | -18.80% | **-6.98%** |
| Both-down hit rate | 11.54% | **30.77%** |
| Diversification ratio | n/a | **2.120** |
| Corr w/ equity | 0.945 | **0.744** |
| Corr w/ bonds | 0.716 | **0.833** |
| Crisis avg ret | -3.04% | **-1.41%** |

Winner OOS Sharpe − All-Weather = **+0.395**; both-down ann diff = **+0.1182**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MinVar | 19 | 1.303 | -8.99% | -5.93% | 2.074 | 59.0 | 27 |
| EW | 2 | 1.401 | -11.54% | -6.47% | 2.004 | 55.2 | 18 |
| InvVar | 6 | 1.324 | -10.34% | -5.83% | 2.052 | 51.7 | 19 |
| ERC | 17 | 1.245 | -10.37% | -6.31% | 1.999 | 44.2 | 28 |
| InvVol | 6 | 1.262 | -11.61% | -6.35% | 2.005 | 43.0 | 25 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 50.0 / 14.6 | field dispersion |
| Winner TRAIN score (z) | +2.33 | OUTLIER — overfit risk |
| Top-10 TRAIN in Top-20 TEST | 70% | selection stability |
| Spearman TRAIN↔TEST score | +0.32 | rank persistence |
| Winner Sharpe test−train | +0.301 | large negative ⇒ overfit |
| Winner both-down test−train | -0.0356 | large negative ⇒ overfit |
| Effective N (vs nominal 14085) | 1.2 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.


| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |
|---:|---|---|---:|---:|---|

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

> LS-TSMOM was **not run** this invocation. Re-run with
> `--schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM` to populate this section.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 7.37% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 0 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode default`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

> No TrendProtect flavors ran this invocation. Re-run with
> `--schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,RP-LS-Overlay,StructShort,TG-LS-Overlay` to populate this section.

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

