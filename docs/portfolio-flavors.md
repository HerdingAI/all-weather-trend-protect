# Portfolio Flavors — Construction, Composition & Measured Comparison

*Research / illustration only. Not investment advice.*

This catalogs every portfolio "flavor" evaluated in `risk_parity_eval.py`: the six
existing schemes (EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM) plus the four **TrendProtect**
flavors added to answer the brief — *find an All-Weather variant with higher expected
return while keeping equity correlation asymmetric (correlated on the way up, low/negative
on the way down)*. For each flavor: the construction formula, what it holds (gross / net,
when it shorts), its parameters, the measured out-of-sample metrics, and pros / cons.

The measured numbers live in the canonical reports and are reproduced in the
**comparison menu** at the end:

- **Default-score canonical** (the legacy "uncorrelated positive returns" objective):
  [`output/risk_parity_eval/report_eval.md`](../output/risk_parity_eval/report_eval.md).
- **Asymmetric-score canonical** (the "correlated up, protected down" objective, all 10
  flavors): [`output/risk_parity_eval_asym/report_eval.md`](../output/risk_parity_eval_asym/report_eval.md)
  (regenerable with `.venv/bin/python risk_parity_eval.py --score-mode asymmetric`).

See also the peer review: [`docs/peer-review.md`](peer-review.md).

---

## 1. Common setup (all flavors share this)

- **Universe / sleeves (12):** US Equity, International Equity, US REIT, Preferred Stock,
  US Treasuries, US Corporate Bonds, US Municipal Bonds, EM Bonds, Gold, Silver,
  Commodities, Currency. Volatility (^VIX) is **excluded** (non-tradable).
- **Combos:** every subset of `≥5` and `≤8` sleeves that contains **≥1 equity and ≥1
  bond** sleeve (`enumerate_combos`). 2817 combos.
- **Split:** TRAIN 2008-01 → 2017-12 (selection) / TEST 2018-01 → 2026-07 (eval only).
  Rolling re-enumeration each January over a trailing 10y window (strictly prior data).
- **Constraints:** long-only for the COV family; 20% per-sleeve cap enforced **inside**
  the MinVar/ERC solver (exact capped-simplex projection, Fix 1); Ledoit-Wolf
  covariance shrinkage; trailing 36m, annual refit; 10 bps/side transaction cost on
  two-way turnover.
- **Both-down regime:** external SPY + AGG (both negative) — de-tautologized from the
  candidate universe (Fix 2). 17 TRAIN / 24 TEST months.
- **Equity reference** for the asymmetric metrics (`upside_beta`, `downside_beta`,
  `downside_corr_eq`): the external SPY total-return series (equity-up months =
  `SPY > 0`, equity-down months = `SPY < 0`).

### Score objectives

- **`--score-mode default`** (legacy "uncorrelated positive returns"):
  `0.30·pct(Sharpe) + 0.25·pct(both-down ann) + 0.15·pct(−maxDD) + 0.15·pct(div ratio)
  + 0.15·pct(−corr with equity in both-down)`.
- **`--score-mode asymmetric`** (the brief's "correlated up, protected down"):
  `0.30·pct(Sharpe) + 0.20·pct(upside_beta − downside_beta) + 0.20·pct(−downside_corr_eq)
  + 0.15·pct(both-down ann) + 0.15·pct(−maxDD)`.
  Selection uses TRAIN only in both modes (the overfitting guard is unchanged).

### Leverage cost

`--lev-rate 0.058` (5.8% APR, the user's funding cost). Charged **monthly** as
`max(0, gross_notional − 1) · lev_rate / 12` in the TrendProtect flavor backtests.
Long-only COV schemes and LS-TSMOM run at gross = 1 → no leverage cost.

---

## 2. The six existing schemes (the COV family + LS-TSMOM)

### EW — Equal Weight
- **Construction:** `w_i = 1/n` across the combo sleeves, then 20% cap (post-hoc clip).
- **Holds:** every sleeve in the combo at equal weight (capped). Long-only, gross = 1.
- **When it shorts:** never.
- **Parameters:** none beyond the cap.
- **Pros:** simplest, most diversified, no covariance estimation error.
- **Cons:** ignores risk / correlation structure; can over-weight a high-vol sleeve.
- **Regime wins/loses:** wins in calm, broadly-up markets; loses when one sleeve
  dominates risk.

### InvVol — Inverse Volatility
- **Construction:** `w_i ∝ 1/vol_i` (trailing 36m), capped.
- **Holds:** low-vol sleeves overweighted. Long-only, gross = 1.
- **When it shorts:** never.
- **Parameters:** trailing window (36m).
- **Pros:** risk-equalizes without a full covariance; more robust than ERC to
  estimation error.
- **Cons:** ignores correlations; bonds dominate (low vol) → equity-heavy in name
  only, bond-heavy in fact.
- **Regime wins/loses:** wins when low-vol assets also return well; loses in a
  vol-regime shift (e.g. 2022 bonds).

### InvVar — Inverse Variance
- **Construction:** `w_i ∝ 1/vol_i²`, capped.
- **Holds:** even more concentrated into the lowest-variance sleeve than InvVol.
  Long-only, gross = 1.
- **When it shorts:** never.
- **Parameters:** trailing window (36m).
- **Pros / Cons:** like InvVol but more extreme concentration; more sensitive to the
  bond sleeve.
- **Regime wins/loses:** similar to InvVol, more bond-tilted.

### ERC — Equal Risk Contribution
- **Construction:** weights so each sleeve contributes equal risk (`w_i · ∂vol/∂w_i`
  equal), solved with the 20% cap **inside** the optimizer (capped projected-gradient,
  an approximation; Fix 1). Long-only, gross = 1.
- **Holds:** risk-balanced across sleeves; cap typically binds US Treasuries at 20%.
- **When it shorts:** never.
- **Parameters:** trailing window (36m), `--erc-cap-mode capped`.
- **Pros:** the textbook "true" risk-parity allocation.
- **Cons:** covariance-estimation sensitive; capped-ERC is an *approximation* (MinVar
  is the rigorous box-constrained solver and the empirical winner).
- **Regime wins/loses:** the canonical risk-parity tilt; dampens both-down vs
  All-Weather but does not flip it positive.

### MinVar — Minimum Variance
- **Construction:** minimize `w'Σw` s.t. `w≥0`, `Σw=1`, `w_i ≤ cap` — a true
  box-constrained QP via exact capped-simplex projection (Fix 1). Long-only, gross = 1.
- **Holds:** the lowest-risk combination of the combo's sleeves; cap binds the
  lowest-variance sleeve (often US Treasuries) at 20%.
- **When it shorts:** never.
- **Parameters:** trailing window (36m).
- **Pros:** the empirical OOS winner (default-score run: Sharpe 1.518, both-down
  −11.42%, MaxDD −5.61%); rigorous cap enforcement; covariance-efficient.
- **Cons:** still long-only → cannot deliver *positive* both-down returns; equity
  correlation stays positive (0.762) including on the downside.
- **Regime wins/loses:** the best long-only dampener of the All-Weather weak spot;
  loses in a sustained both-down (bonds + equities fall together).

### LS-TSMOM — Long/Short Managed Futures (time-series momentum)
- **Construction:** each month, per sleeve,
  `pos_i = base_w_i · sign(trailing-12m return)`, with **equal-weight base**,
  **$1 gross, dollar-neutral, 0% T-bill collateral** (matches `all_weather_v2.py`'s
  conservative assumption). Monthly re-sign; drift `w/(1+g)` (not `w/w.sum()`).
- **Holds:** long sleeves with positive trailing-12m return, short those with
  negative. Gross = 1, net ≈ 0 (dollar-neutral).
- **When it shorts:** whenever a sleeve's trailing-12m return is negative —
  this is the crisis-alpha mechanism (shorts the falling bonds+equities in 2022).
- **Parameters:** `--tsmom-lookback` (default 12).
- **Pros:** the only direction in the original space that *can* deliver positive
  both-down returns (it shorts the falling legs); near-zero equity correlation
  (0.129) — the "uncorrelated" the brief asks for, measured.
- **Cons:** full-period Sharpe is far below long-only (whipsaw in calm markets);
  the edge is **not statistically significant** in the default-score window (DSR
  −0.964, Sharpe CI straddles 0); 0% collateral is conservative (real T-bills add
  ~1-2%/yr).
- **Regime wins/loses:** wins in 2022-style stagflation and the dot-com bust;
  whipsaws in the 2010s ZIRP grind.

---

## 3. The four TrendProtect flavors (the new constructions)

All four are **presets of one parameterized engine** (`_backtest_flavor`), so they
share the trend signal, the blend, and the leverage-cost machinery. Per month, each
flavor's position is rebuilt from:

1. a **long MinVar base leg** (annual refit, cap-respecting, reuses the Fix-1 solver)
   — `base_w`, sum = 1;
2. an optional **trend-gate** on the **equity sleeves** of the combo:
   `base_w[i] *= 1{trailing-12m_i > 0}` for equity sleeves only (bonds / gold /
   diversifiers stay long). Long when up, **flat when down**;
3. an optional **LS-TSMOM momentum overlay**: `pos += w_overlay · base_w ·
   sign(trailing-12m)` per sleeve (dollar-neutral, adds `w_overlay` of gross);
4. an optional **structural short**: `pos[short_sleeve] -= w_short`, held
   permanently (sleeve-level **netting** — a long US-Treasuries leg of 0.20
   shorted by 0.30 becomes net −0.10);
5. **gross_notional = Σ|pos|**; **leverage cost** = `max(0, gross_notional − 1) ·
   lev_rate / 12` (5.8% APR) charged monthly;
6. monthly rebalance with the same 10 bps/side turnover machinery; drift
   `w / (1+g)`.

### TrendGate
- **Preset:** `trend_gate=True, w_overlay=0.0, struct_short=None`.
- **Construction:** long MinVar base, with equity sleeves gated to cash when their
  own trailing-12m return < 0. Bonds/gold/diversifiers stay long.
- **Holds:** the MinVar combo, minus any equity sleeve currently in a 12m drawdown.
  Long-only. **Gross ≤ 1** (gating reduces exposure) → **no leverage cost**.
- **When it shorts:** never (long-only with a cash gate).
- **Parameters:** `--tsmom-lookback` (gate lookback, default 12).
- **Pros:** long-only (no leverage cost, no shorting risk); cuts equity exposure
  after a sustained drawdown (downside dampening); keeps the carry of the
  bond/gold/diversifier sleeves.
- **Cons:** the 12m trend-gate **lags** — it turns off ~12m *into* a drawdown (long
  at the start of the drop) and on ~12m *into* a rally (flat at the start of the
  recovery), so `downside_beta` is often **≥** `upside_beta` (the lag works against
  the asymmetric goal); cannot go net-short, so no positive both-down return;
  whipsaw in choppy markets.
- **Regime wins/loses:** wins in a sustained, slow drawdown where 12m momentum
  flips cleanly (2022 bonds); loses at drawdown *starts* and in choppy markets.

### RP-LS-Overlay
- **Preset:** `trend_gate=False, w_overlay=0.30, struct_short=None`.
- **Construction:** long MinVar base (full, ungated) + a 0.30-gross dollar-neutral
  LS-TSMOM momentum overlay on top.
- **Holds:** the full MinVar long leg **plus** a long/short momentum sleeve.
  **Gross = 1.30** → leverage cost ≈ `(0.30)·5.8% = 1.74%/yr`.
- **When it shorts:** the overlay shorts any sleeve with negative trailing-12m
  return (the crisis-alpha leg).
- **Parameters:** `--tsmom-lookback`, `w_overlay=0.30`, `--lev-rate 0.058`.
- **Pros:** the LS overlay shorts the falling legs → genuinely positive in
  both-down (the direction that matches the brief); the long MinVar base keeps the
  return / Sharpe floor; the overlay is crisis-alpha on top of a diversified long
  book.
- **Cons:** gross 1.30 → leverage cost drags the return; overlay whipsaw in calm
  markets (the 2010s) drags Sharpe; `downside_corr_eq` may stay positive if the
  long leg dominates the down months.
- **Regime wins/loses:** wins in both-down / stagflation (overlay shorts); whipsaws
  in calm markets.

### StructShort
- **Preset:** `trend_gate=False, w_overlay=0.0, struct_short=("US Treasuries", 0.30)`.
- **Construction:** long MinVar base, minus a permanent 0.30 short on the US
  Treasuries sleeve (sleeve-level netting).
- **Holds:** the MinVar combo, with US Treasuries flipped to **net-short** (a
  0.20 long leg − 0.30 short = net −0.10). **Gross ≤ 1** (sleeve-level netting
  *reduces* gross; no leverage cost) — typically ~0.90 gross.
- **When it shorts:** always — a structural net-short-duration position, held in
  every month (not signal-driven).
- **Parameters:** `struct_short` sleeve + weight.
- **Pros:** a direct hedge for a 2022-style stocks+bonds rout (short duration);
  sleeve-level netting keeps gross ≤ 1 (no leverage cost); structural (not
  signal-driven) → no whipsaw, no lookback lag.
- **Cons:** a permanent short pays for the hedge in **every** non-stagflation year
  (carry drag — short duration is expensive outside 2022); only applies to combos
  containing the short sleeve (TRAIN search self-selects those); sleeve-level short
  is a net-short-duration **tilt**, not a standalone short ticker (ticker-level
  shorting that *adds* gross is a flagged refinement).
- **Regime wins/loses:** wins in a bond rout (2022); loses (carry) in any year
  bonds rally — which is most years in the TEST window.

### TG-LS-Overlay
- **Preset:** `trend_gate=True, w_overlay=0.20, struct_short=None`.
- **Construction:** long MinVar base with the equity trend-gate **and** a 0.20-gross
  LS-TSMOM overlay — both levers.
- **Holds:** the trend-gated MinVar long leg plus a long/short momentum sleeve.
  **Gross ≈ 1.20** (gating reduces the long leg, overlay adds gross) → leverage
  cost ≈ `(0.20)·5.8% = 1.16%/yr`.
- **When it shorts:** the overlay shorts falling sleeves; the gate flats equity
  in drawdowns.
- **Parameters:** `--tsmom-lookback`, `w_overlay=0.20`, `--lev-rate 0.058`.
- **Pros:** combines downside dampening (gate) with crisis alpha (overlay) —
  targets the asymmetric goal from two angles; smaller overlay than RP-LS-Overlay
  → lower leverage cost.
- **Cons:** inherits **both** the trend-gate lag **and** the overlay whipsaw —
  both costs; gross 1.20 → leverage cost; the most parameters → the most
  overfitting surface (check the DSR / bootstrap CI).
- **Regime wins/loses:** wins when both the gate and the overlay align (sustained
  drawdown with a clean momentum flip); loses when they conflict (gate flats
  equity into a rally while the overlay whipsaws).

---

## 4. Reproducing the comparison

```bash
# Default-score canonical (legacy objective, 6 schemes) — the validated baseline:
.venv/bin/python risk_parity_eval.py
# → output/risk_parity_eval/report_eval.md

# Asymmetric-score canonical (the brief's objective, all 10 flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,RP-LS-Overlay,StructShort,TG-LS-Overlay
# → output/risk_parity_eval_asym/report_eval.md (§10 = the comparison menu)

# Regression guard (default score, COV-only — existing numbers unchanged):
.venv/bin/python risk_parity_eval.py --ref-mode sleeves --schemes EW,InvVol,InvVar,ERC,MinVar --no-rolling

# Tweak the leverage cost or the trend lookback:
.venv/bin/python risk_parity_eval.py --score-mode asymmetric --lev-rate 0.0 --tsmom-lookback 6
```

---

## 5. Comparison menu (measured, out-of-sample)

Ranked table — the four TrendProtect flavors vs All-Weather, the risk-parity (MinVar)
winner, and LS-TSMOM — over the **TEST 2018-01 → 2026-07** window, net of 10 bps/side
turnover cost **and** the 5.8% APR leverage cost (where gross > 1). Generated as **§10**
of the asymmetric canonical report:
[`output/risk_parity_eval_asym/report_eval.md`](../output/risk_parity_eval_asym/report_eval.md).
Sorted by net Sharpe.

| Portfolio | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **TrendGate** | 4.39% | **1.385** | −4.20% | −4.50% | 0.044 | 0.161 | 0.491 | 1.00 | 0.00% | 0.07 | [0.70, 2.27] |
| **RP winner (MinVar)** | 5.46% | **1.294** | −5.25% | −7.44% | 0.081 | 0.194 | 0.475 | 1.00 | 0.00% | — | — |
| **TG-LS-Overlay** | 4.26% | **1.264** | −3.65% | −4.48% | 0.041 | 0.133 | 0.376 | 1.20 | 1.16% | −0.05 | [0.67, 2.06] |
| **All-Weather** | **7.37%** | **1.055** | −12.31% | −18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| **StructShort** | 5.65% | **0.794** | −12.31% | −18.90% | 0.308 | 0.479 | 0.723 | 1.00 | 0.00% | −0.52 | [0.18, 1.69] |
| **RP-LS-Overlay** | 4.31% | **0.539** | −13.31% | −30.07% | 0.369 | 0.502 | 0.749 | 1.30 | 1.74% | −0.77 | [−0.01, 1.24] |
| **LS-TSMOM** | 0.83% | **0.094** | −24.97% | −13.30% | −0.232 | 0.352 | 0.379 | 1.00 | 0.00% | −1.22 | [−0.56, 1.02] |

Columns: Ann ret = net annualized return (after turnover + leverage cost); Sharpe =
net annualized; MaxDD = worst peak-to-trough; Both-down = annualized return in the 24
TEST months where external SPY **and** AGG are both negative; Upβ = β to equity on
equity-up months; Dnβ = β on equity-down months; Dn-corr = correlation with equity on
equity-down months; Gross = gross notional (Σ|pos|); Lev cost/yr = leverage drag
((gross−1)·5.8%); DSR = Deflated Sharpe (negative = edge **not** significant after
multiple-comparison adjustment); Sharpe CI = block-bootstrap 95% interval.

> **Verdict (measured, honest).** **None of the four TrendProtect flavors beat
> All-Weather's 7.37% net OOS return** in this window after the 5.8%/yr leverage cost —
> that is the measured answer, not a forced winner. What the flavors *do* buy is a
> **much better risk profile**: TrendGate leads on Sharpe (1.385 vs AW 1.055), MaxDD
> (−4.20% vs −12.31%), and both-down (−4.50% vs −18.74%) — at the cost of ~3%/yr of
> return. The asymmetric goal ("correlated up, protected down") is **only weakly met**:
> the trend-gate flavors keep Upβ and Dnβ **both low** (the gate mostly flats equity,
> so the combos run bond/gold/commodity-heavy), and Dnβ slightly **exceeds** Upβ — the
> documented 12m-lag works *against* the asymmetric shape (long into drawdown starts,
> flat into rally starts). LS-TSMOM is the only flavor with Upβ < 0 (it shorts into
> up-months via the momentum leg) but its return/Sharpe are poor and **not
> significant** (DSR −1.22, CI straddles 0). The flavors that add gross (RP-LS-Overlay
> gross 1.30, TG-LS-Overlay gross 1.20) pay 1.16–1.74%/yr of leverage cost and do not
> recover it. Trust the DSR / bootstrap CI: the flavors share sleeves (effective N ≪
> nominal N) and this is one TRAIN/TEST split = one regime.

### Top picks (a menu of good options, with the trade-off named)

- **Best risk-adjusted (Sharpe + MaxDD + both-down), lower return:** **TrendGate**
  — Sharpe 1.385, MaxDD −4.20%, both-down −4.50%, but 4.39% net (≈3%/yr below AW).
  Long-only, no leverage cost. DSR 0.07 (marginal; CI [0.70, 2.27] clear of 0).
- **Best return (the AW bar itself):** **All-Weather** — 7.37% / Sharpe 1.055, but
  both-down −18.74%, MaxDD −12.31%, Dn-corr 0.793 (highly correlated on the downside —
  the weak spot the brief set out to fix).
- **Lowest drawdown / shallowest both-down:** **TG-LS-Overlay** — MaxDD −3.65%,
  both-down −4.48%, Sharpe 1.264, but 4.26% net + 1.16%/yr leverage cost, DSR −0.05
  (edge not significant).
- **Directionally correct but insignificant:** **LS-TSMOM** — the only net-short /
  crisis-alpha leg (Upβ −0.232), but 0.83% net, DSR −1.22.
- **Structural duration hedge:** **StructShort** — 5.65% net (closest to AW among
  the flavors), Sharpe 0.794, gross 1.00 (netting, no leverage cost), but both-down
  −18.90% and DSR −0.52 (the permanent short pays carry in most years).

*Research / illustration only. Not investment advice.*