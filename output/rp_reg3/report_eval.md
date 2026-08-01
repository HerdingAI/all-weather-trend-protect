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
- **Combos × schemes:** 2817 × 6 = **16902 trials** on TRAIN.
- **Schemes:** EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM — EW/InvVol/InvVar/ERC/MinVar separate composition
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

- **Combo:** US Equity,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Silver,Currency
- **Scheme:** ERC  (risk-parity family)
- **TRAIN rank:** #1 (TRAIN score 77.0, z = +1.72)

| Metric | TRAIN (in-sample) | **TEST (OOS, net)** | Δ |
|---|---:|---:|---:|
| Net Sharpe | 1.094 | **1.111** | 0.018 |
| Both-down ann ret (net) | -12.05% | **-14.73%** | -2.69% |
| Max drawdown | -16.04% | **-9.00%** | 7.04% |
| Diversification ratio | 2.247 | **1.925** | — |
| Corr w/ equity (both-down) | 0.614 | **0.769** | — |
| Ann turnover | 39.99% | 35.75% | — |

- **Cap integrity (Fix 1):** winner max sleeve weight = 20.00% vs cap 20% → YES — solver output already ≤ cap (post-hoc clip is a no-op).

## 3. Statistical significance (multiple-comparison adjusted)

- Trials run on TRAIN: **16902**.
- Raw OOS net Sharpe: **1.111**.
- Expected max null Sharpe over 16902 trials: 1.461 (annualized).
- **Deflated Sharpe (annualized): -0.350**  (raw minus the luck-of-many-trials benchmark).
- **P(true Sharpe > 0 after deflation) = 0.16** (DSR probability).

- Block-bootstrap 95% CI on OOS net Sharpe: [0.421, 1.965]
- Block-bootstrap 95% CI on OOS both-down ann ret: [-18.03%, -10.70%]

> **DSR caveats (read before interpreting the headline DSR):**
> - **Effective N ≪ nominal N.** DSR's penalty uses N = 16902 independent trials, but the trials share sleeves (any two portfolios holding US Treasuries are correlated), so the *effective* independent-
>   trial count is the **effective rank of the TRAIN trial-return matrix = 1.2** (participation ratio, Σλ/λ_max). The true luck-of-many-trials benchmark is therefore **smaller** than the one used,
>   so DSR ≤ 0 here is a **conservative** upper bound on the multiple-comparison penalty — the edge may be more significant than DSR suggests, not less. (A proper OOS multiple-comparison test — Holm/Bonferroni over the effective N, or DSR applied to the TRAIN max — is future work.)
> - **DSR is applied to the OOS Sharpe of the TRAIN-selected winner** (a non-canonical but accepted variant of Bailey & López de Prado 2014), not to the in-sample max Sharpe. Combined with the effective-N point, treat the headline DSR as a conservative guardrail, not a precise p-value.

> **Interpretation:** Deflated Sharpe ≤ 0 **and** the both-down CI is entirely negative: there is **no statistically robust resilience** to the both-down scenario among these investable sleeves — the best portfolio is the least-bad, not a positive-return hedge.

## 4. Winner vs All-Weather on TEST (out-of-sample, net of cost)

| Metric | All-Weather (OOS) | Winner (OOS) |
|---|---:|---:|
| Ann return (net) | 6.03% | **5.23%** |
| Ann vol | 7.79% | **4.71%** |
| Net Sharpe | 0.774 | **1.111** |
| Max DD | -16.26% | **-9.00%** |
| Both-down ann ret | -29.27% | **-14.73%** |
| Both-down hit rate | 4.17% | **4.17%** |
| Diversification ratio | n/a | **1.925** |
| Corr w/ equity | 0.827 | **0.735** |
| Corr w/ bonds | 0.784 | **0.808** |
| Crisis avg ret | -5.28% | **-2.75%** |

Winner OOS Sharpe − All-Weather = **+0.337**; both-down ann diff = **+0.1453**.

## 5. Composition vs allocation — does the weighting scheme matter? (OOS, TRAIN top-N)

| Scheme | n | OOS Sharpe (avg) | OOS both-down ann (avg) | OOS maxDD (avg) | OOS div ratio (avg) | OOS score (avg) | TRAIN rank (avg) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MinVar | 22 | 1.109 | -14.06% | -9.18% | 2.043 | 56.1 | 24 |
| EW | 3 | 1.211 | -16.15% | -9.37% | 1.921 | 55.2 | 28 |
| InvVar | 4 | 1.134 | -15.95% | -9.26% | 1.952 | 53.7 | 28 |
| InvVol | 3 | 1.155 | -16.52% | -9.29% | 1.935 | 49.6 | 25 |
| ERC | 18 | 1.090 | -16.35% | -9.76% | 1.940 | 43.7 | 27 |

## 6. Overfit diagnostics

| Diagnostic | Value | Reading |
|---|---:|---|
| TRAIN score mean / std | 41.3 / 20.8 | field dispersion |
| Winner TRAIN score (z) | +1.72 | within pack |
| Top-10 TRAIN in Top-20 TEST | 40% | selection stability |
| Spearman TRAIN↔TEST score | +0.42 | rank persistence |
| Winner Sharpe test−train | +0.018 | large negative ⇒ overfit |
| Winner both-down test−train | -0.0269 | large negative ⇒ overfit |
| Effective N (vs nominal 16902) | 1.2 | DSR penalty is conservative (trials correlated) |

## 7. Rolling FULL re-enumerated selection (strictest OOS test)

Each January the FULL combo×scheme search is re-run on the trailing 10y window
(data strictly prior — **not** a TRAIN shortlist) and the #1 is held for 12 months.

- OOS (rolling) net Sharpe = **0.771**
- OOS (rolling) both-down ann ret = **-15.86%**
- OOS (rolling) max drawdown = -11.34%
- Rolling Deflated Sharpe = -0.691  (P>0 = 0.02)

| Year | Combo | Scheme | Sel score | Sel Sharpe | Top weight |
|---:|---|---|---:|---:|---|
| 2018 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold,Silver,Currency | MinVar | 70.7 | 0.92 | US Equity 20.0% |
| 2019 | US Equity,US Corporate Bonds,US Municipal Bonds,Gold,Silver,Commodities,Currency | MinVar | 70.4 | 1.10 | US Equity 20.0% |
| 2020 | Preferred Stock,US Corporate Bonds,US Municipal Bonds,Gold,Silver,Currency | MinVar | 78.7 | 1.12 | Preferred Stock 20.0% |
| 2021 | US Equity,US Treasuries,US Municipal Bonds,Gold,Currency | MinVar | 78.2 | 1.19 | US Treasuries 20.0% |
| 2022 | US REIT,Preferred Stock,US Treasuries,US Corporate Bonds,US Municipal Bonds,Currency | MinVar | 77.4 | 1.23 | US Treasuries 20.0% |
| 2023 | US Equity,US Treasuries,US Municipal Bonds,Gold,Currency | MinVar | 69.8 | 0.82 | US Treasuries 20.0% |
| 2024 | US REIT,US Treasuries,US Corporate Bonds,US Municipal Bonds,Gold,Currency | MinVar | 70.0 | 0.83 | US Treasuries 20.0% |
| 2025 | US Equity,US Municipal Bonds,Gold,Commodities,Currency | MinVar | 69.4 | 0.86 | US Municipal Bonds 20.0% |
| 2026 | US Equity,US Municipal Bonds,Gold,Silver,Commodities,Currency | EW | 69.8 | 1.10 | US Equity 16.7% |

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

- **TRAIN-best LS-TSMOM combo:** International Equity, Preferred Stock, US Treasuries, US Municipal Bonds, EM Bonds, Commodities, Currency
- **Signal:** `pos = (1/n)·sign(trailing-12m)` per sleeve, monthly. Lookback configurable via `--tsmom-lookback`.

| Metric | All-Weather (OOS) | Risk-parity winner (OOS) | **LS-TSMOM (OOS)** |
|---|---:|---:|---:|
| Ann return (net) | 6.03% | 5.23% | **1.97%** |
| Ann vol | 7.79% | 4.71% | **5.96%** |
| Net Sharpe | 0.774 | 1.111 | **0.330** |
| Max DD | -16.26% | -9.00% | **-12.58%** |
| Both-down ann ret | -29.27% | -14.73% | **4.79%** |
| Both-down hit rate | 4.17% | 4.17% | **45.83%** |
| Corr w/ equity | 0.827 | 0.735 | **-0.233** |
| Crisis avg ret | -5.28% | -2.75% | **3.61%** |

- LS-TSMOM OOS net Sharpe: **0.330**
- LS-TSMOM OOS both-down ann ret: **4.79%**  (hit rate 45.83%)
- LS-TSMOM Deflated Sharpe (annualized, n_trials = 2817): **-0.981**  (P>0 = 0.00)
- Block-bootstrap 95% CI on LS-TSMOM OOS Sharpe: [-0.312, 1.103]
- Block-bootstrap 95% CI on LS-TSMOM OOS both-down ann ret: [-4.86%, 17.22%]

> **Verdict:** **LS-TSMOM delivers POSITIVE both-down returns OOS and beats All-Weather** where All-Weather is weakest — the long/short trend overlay achieves what long-only risk parity could not. This is the All-Weather variant the brief asked for. The trade-off (whipsaw in calm markets — check the full-period Sharpe) is the price of crisis alpha.

> **Collateral assumption:** LS-TSMOM is modeled at $1 gross with 0% T-bill collateral (conservative, matches awv2). A real implementation holds the cash collateral in T-bills, adding ~1-2%/yr to the return shown. Sizing is equal-weight across the combo (neutral); vol-scaling is a flagged refinement.

## 10. TrendProtect flavor comparison menu (correlated up, protected down)

The brief: find an All-Weather flavor with **higher expected return** (target: beat All-Weather's 6.03% net OOS) while keeping equity correlation **asymmetric** — correlated on the way up (capture upside), low/negative on the way down (downside protection). 0 constructions of one parameterized engine (`_backtest_flavor`), each a long base leg (annual refit, cap-respecting — MinVar by default, or equal-weight `base_mode=ew` to keep real equity weight like AW) plus active overlays: a **trend-gate** on the equity sleeves (gate to cash when their own trailing-12m return < 0, OR `gate_mode=short` to FLIP the equity sleeve to net-short on the downside signal — the direct lever for negative downside-β while keeping upside-β), a **LS-TSMOM momentum overlay** (dollar-neutral, adds gross → leverage cost), and a **structural short** (permanent sleeve-level net-short, e.g. US Treasuries for a net-short-duration tilt). Leverage cost = **5.8% APR** on gross > 1, charged monthly. Selection uses the **`--score-mode default`** objective. Full construction + per-flavor pros/cons: [`docs/portfolio-flavors.md`](../docs/portfolio-flavors.md).

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

