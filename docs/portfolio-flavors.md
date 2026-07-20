# Portfolio Flavors — Construction, Composition & Measured Comparison

*Research / illustration only. Not investment advice.*

This catalogs every portfolio "flavor" evaluated in `risk_parity_eval.py`: the six
existing schemes (EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM) plus the **TrendProtect**
flavors added to answer the brief — *find an All-Weather variant with higher expected
return while keeping equity correlation asymmetric (correlated on the way up, low/negative
on the way down)*. The TrendProtect family grew in two rounds: **round 1** added four
cash-gate / overlay / structural-short flavors; **round 2** added six `gate_mode=short`
flavors (flip equity to net-short on the downside signal — the direct lever for negative
downside-β) and an `asymmetric2` score that rewards upside capture + return instead of
fleeing equity. For each flavor: the construction formula, what it holds (gross / net,
when it shorts), its parameters, the measured out-of-sample metrics, and pros / cons.

The measured numbers live in the canonical reports and are reproduced in the
**comparison menus** at the end:

- **Default-score canonical** (the legacy "uncorrelated positive returns" objective):
  [`output/risk_parity_eval/report_eval.md`](../output/risk_parity_eval/report_eval.md).
- **Asymmetric-score canonical** (round 1, the four cash-gate flavors):
  [`output/risk_parity_eval_asym/report_eval.md`](../output/risk_parity_eval_asym/report_eval.md)
  (regenerable with `.venv/bin/python risk_parity_eval.py --score-mode asymmetric`).
- **Asymmetric2-score canonical** (round 2, the seven `gate_mode=short` / EW-base
  flavors): [`output/risk_parity_eval_asym2b/report_eval.md`](../output/risk_parity_eval_asym2b/report_eval.md)
  (regenerable with `.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 ...`).

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
  + 0.15·pct(both-down ann) + 0.15·pct(−maxDD)`. **Diagnostic:** the `(upβ−dnβ)` term
  lets the search *flee* equity (a combo with low Upβ AND low Dnβ scores well) → it
  selects bond/gold-heavy combos with ~3-4% return. See `asymmetric2` for the fix.
- **`--score-mode asymmetric2`** (rewards upside capture AND return, not just the
  Upβ−Dnβ gap): `0.30·pct(ann_return_net) + 0.20·pct(upside_beta) + 0.15·pct(−downside_beta)
  + 0.10·pct(−downside_corr_eq) + 0.15·pct(Sharpe) + 0.10·pct(−maxDD)`. Rewards a high
  Upβ (real equity weight) *and* a high net return, so the search keeps equity in the
  book instead of fleeing to diversifiers. This is the score used for the TG-Short /
  EW-Short family.
  Selection uses TRAIN only in all three modes (the overfitting guard is unchanged).

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

## 3. The TrendProtect flavors (the new constructions)

All TrendProtect flavors are **presets of one parameterized engine**
(`_backtest_flavor`), so they share the trend signal, the blend, and the leverage-cost
machinery. The engine knobs (each preset is a dict of these):

- `trend_gate` (bool) — apply the equity trend-gate;
- `gate_mode` ("cash" or "short") — **cash** gates equity sleeves to 0 (flat) on the
  downside signal; **short** *flips* the equity sleeve to net-short on the downside
  signal (`pos *= sign(trailing-lookback)` for equity sleeves — long when up, short
  when down). `short` is the direct lever for negative downside-β (round 2);
- `w_overlay` (gross) — LS-TSMOM dollar-neutral momentum overlay weight;
- `struct_short` (sleeve, weight) — permanent sleeve-level net-short via netting;
- `base_mode` ("minvar" or "ew") — the long base leg. **minvar** (default) starves
  high-vol equity to ~5-10% weight; **ew** (equal-weight, like All-Weather's own ~1/n)
  keeps a real equity weight so the gate/short has something to act on (round 2);
- `lookback` (months, default 12) — per-preset override of the trend signal window
  (6m = faster, less lag, more whipsaw).

Per month, each flavor's position is rebuilt from:

1. a **long base leg** (annual refit, cap-respecting, reuses the Fix-1 solver for
   MinVar, or `1/n` capped for EW) — `base_w`, sum = 1;
2. an optional **trend-gate** on the **equity sleeves** of the combo. In `cash` mode:
   `base_w[i] *= 1{trailing-lookback_i > 0}` (long when up, **flat when down**). In
   `short` mode: `base_w[i] *= sign(trailing-lookback_i)` (long when up, **net-short
   when down**). Bonds / gold / diversifiers stay long in both modes;
3. an optional **LS-TSMOM momentum overlay**: `pos += w_overlay · base_w ·
   sign(trailing-lookback)` per sleeve (dollar-neutral, adds `w_overlay` of gross);
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

## 3b. The six `gate_mode=short` / EW-base flavors (round 2)

Round 1's measured verdict (none beat 7.37% with the asymmetric property) diagnosed
three causes: (a) the **cash-gate can't produce negative Dnβ** (it only flats equity);
(b) the **MinVar base starves equity** to ~5-10% weight → little upside to capture and
little to short; (c) the **`asymmetric` score flees equity** (the `upβ−dnβ` term rewards
a combo that is low in *both*). Round 2 fixes all three with `gate_mode=short` (flip
equity to net-short on the downside signal), `base_mode=ew` (equal-weight base keeps a
real equity weight like AW), and the `asymmetric2` score (rewards Upβ + ann return, not
the gap). Three MinVar-base + three EW-base, each with an optional 0.20 LS overlay and a
6m-lookback variant:

### TG-Short
- **Preset:** `trend_gate=True, gate_mode="short", w_overlay=0.0, base_mode="minvar"`.
- **Construction:** long MinVar base, with equity sleeves **flipped to net-short** when
  their own trailing-12m return < 0 (long when up, short when down). Bonds/gold/
  diversifiers stay long.
- **Holds:** the MinVar combo, with equity net-short during a 12m equity drawdown.
  Sleeve-level netting can keep **gross ≤ 1** → **no leverage cost**.
- **When it shorts:** equity sleeves, signal-driven (12m return < 0).
- **Parameters:** `--tsmom-lookback` (gate lookback, default 12).
- **Pros:** the direct lever for negative downside-β while keeping upside-β (long equity
  up, short equity down). Sleeve-level netting → no leverage cost. Reuses the MinVar base.
- **Cons:** MinVar base starves high-vol equity to ~5-10% → little equity to short, so
  both the upside capture AND the short benefit are muted (return floor well below AW).
  12m signal lags: shorts ~12m *into* a drawdown (after the drop), longs ~12m *into* a
  rally (after the rebound). Whipsaw in choppy markets.
- **Regime wins/loses:** wins in a sustained, slow drawdown where 12m momentum flips
  cleanly; loses at drawdown *starts* (lags) and in choppy markets.

### TG-Short-LS
- **Preset:** `trend_gate=True, gate_mode="short", w_overlay=0.20, base_mode="minvar"`.
- **Construction:** TG-Short (short equity on downside) + a 0.20-gross dollar-neutral
  LS-TSMOM overlay — the equity flip *and* the broader momentum crisis-alpha leg.
- **Holds:** the short-on-downside MinVar leg plus a long/short momentum sleeve.
  **Gross can exceed 1** → leverage cost up to ~1.16%/yr.
- **When it shorts:** equity sleeves on the downside signal; the overlay shorts any
  sleeve with negative trailing-12m return.
- **Parameters:** `--tsmom-lookback`, `w_overlay=0.20`, `--lev-rate 0.058`.
- **Pros:** targets the asymmetric goal from two angles (equity flip + momentum crisis
  alpha); smallest Dn-corr of the family in the measured window.
- **Cons:** inherits MinVar-base equity starvation AND the 12m lag AND the overlay
  whipsaw — all three costs. Gross > 1 → leverage cost. Most overfitting surface of the
  TG-Short family; check DSR / bootstrap CI.
- **Regime wins/loses:** wins when the equity flip and the overlay align; loses when
  they conflict or the 12m lag mis-times the flip.

### TG-Short-6m
- **Preset:** `trend_gate=True, gate_mode="short", w_overlay=0.0, base_mode="minvar", lookback=6`.
- **Construction:** TG-Short with a **faster 6m** trend signal — reduces the 12m lag
  (out of drawdowns sooner, into rallies sooner), so the short flip is better timed.
- **Holds:** the MinVar combo, equity net-short during a 6m equity drawdown. Gross ≤ 1.
- **When it shorts:** equity sleeves on the 6m downside signal.
- **Parameters:** `lookback=6`.
- **Pros:** less lag than the 12m TG-Short → better-timed flip; direct lever for
  negative downside-β; gross ≤ 1 (no leverage cost). Highest Sharpe of the TG-Short
  family in the measured window.
- **Cons:** faster signal whipsaws *more* in choppy markets (more false flips); MinVar
  base still starves equity → muted upside capture; shorter lookback → more turnover.
- **Regime wins/loses:** wins in sharper/faster drawdowns (2020 COVID, 2022); whipsaws
  more in chop.

### EW-Short
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", w_overlay=0.0`.
- **Construction:** equal-weight base (like All-Weather's own ~1/n across sleeves) so
  equity keeps a real weight (~12-25%), with equity flipped to net-short on the 12m
  downside signal. Fixes the MinVar-base equity starvation that left TG-Short with
  nothing to short.
- **Holds:** the equal-weight combo, equity net-short during a 12m equity drawdown.
  Gross ≤ 1.
- **When it shorts:** equity sleeves on the 12m downside signal.
- **Parameters:** `--tsmom-lookback`, `base_mode="ew"`.
- **Pros:** real equity weight → the short flip is meaningful and the upside capture is
  AW-like; the direct test of "correlated up, protected down" with AW-like return floor.
- **Cons:** more equity weight → higher vol / drawdown than the MinVar-base flavors.
  The 12m-lagged short on a *real* equity weight **whipsaws hard** (shorts the bottom of
  2018, the 2020 COVID rebound lag, etc.) → return collapses in the measured window.
  Equal-weight ignores covariance.
- **Regime wins/loses:** the strongest direct test of the construction; loses in this
  window because the lagged short sells the bottom.

### EW-Short-LS
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", w_overlay=0.20`.
- **Construction:** EW-Short (real equity weight + short on downside) + a 0.20 LS-TSMOM
  overlay. Highest upside-capture intent of the family.
- **Holds:** the short-on-downside equal-weight leg plus a long/short momentum sleeve.
  Gross can exceed 1 → leverage cost up to ~1.16%/yr.
- **When it shorts:** equity sleeves on the downside signal; the overlay shorts falling
  sleeves.
- **Parameters:** `--tsmom-lookback`, `w_overlay=0.20`, `base_mode="ew"`, `--lev-rate 0.058`.
- **Pros:** targets both beat-AW return (EW base keeps equity) AND asymmetric protection
  (equity flip + overlay).
- **Cons:** the lagged short on real equity weight whipsaws (same as EW-Short) *and* the
  overlay adds gross/leverage cost/whipsaw → lowest return of the family in the measured
  window. Most overfitting surface.
- **Regime wins/loses:** the most aggressive construction; loses in this window on
  whipsaw + leverage cost.

### EW-Short-6m
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", w_overlay=0.0, lookback=6`.
- **Construction:** EW-Short with a faster 6m signal — real equity weight (EW base) AND
  less lag, so the short flip is both meaningful and better timed.
- **Holds:** the equal-weight combo, equity net-short during a 6m equity drawdown.
  Gross ≤ 1.
- **When it shorts:** equity sleeves on the 6m downside signal.
- **Parameters:** `lookback=6`, `base_mode="ew"`.
- **Pros:** directly targets the brief — high upside-β (EW base), negative downside-β
  (short flip), better-timed (6m). Gross ≤ 1 (no leverage cost).
- **Cons:** faster signal whipsaws more; more turnover; higher vol / drawdown than
  MinVar-base flavors (more equity). The lagged short on real equity still mis-times in
  the measured window.
- **Regime wins/loses:** wins in faster drawdowns; whipsaws in chop.

---

## 4. Reproducing the comparison

```bash
# Default-score canonical (legacy objective, 6 schemes) — the validated baseline:
.venv/bin/python risk_parity_eval.py
# → output/risk_parity_eval/report_eval.md

# Asymmetric-score canonical (round 1, the four cash-gate flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,RP-LS-Overlay,StructShort,TG-LS-Overlay
# → output/risk_parity_eval_asym/report_eval.md (§10 = the round-1 menu)

# Asymmetric2-score canonical (round 2, the seven gate_mode=short / EW-base flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym2b
# → output/risk_parity_eval_asym2b/report_eval.md (§10 = the round-2 menu)

# Regression guard (default score, COV-only — existing numbers unchanged):
.venv/bin/python risk_parity_eval.py --ref-mode sleeves --schemes EW,InvVol,InvVar,ERC,MinVar --no-rolling

# Tweak the leverage cost or the trend lookback:
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --lev-rate 0.0 --tsmom-lookback 6
```

---

## 5. Comparison menu — round 2 (measured, out-of-sample)

Ranked table — the seven round-2 TrendProtect flavors (the `gate_mode=short` / EW-base
family) vs All-Weather and the risk-parity (MinVar) winner — over the **TEST 2018-01 →
2026-07** window, net of 10 bps/side turnover cost **and** the 5.8% APR leverage cost
(where gross > 1). Generated as **§10** of the asymmetric2 canonical report:
[`output/risk_parity_eval_asym2b/report_eval.md`](../output/risk_parity_eval_asym2b/report_eval.md).
Sorted by net annualized return.

| Portfolio | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **RP winner (MinVar)** | **9.29%** | 0.921 | −15.65% | −30.50% | 0.432 | 0.585 | 0.747 | 1.00 | 0.00% | — | — |
| **All-Weather (bar)** | 7.37% | **1.055** | −12.31% | −18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| **TrendGate** | 5.95% | 0.640 | −15.78% | −31.85% | 0.265 | 0.489 | 0.631 | 1.00 | 0.00% | −0.67 | [−0.01, 1.48] |
| **TG-Short-6m** | 5.09% | 0.754 | −12.35% | −15.27% | 0.086 | 0.340 | 0.474 | 1.00 | 0.00% | −0.56 | [0.06, 1.72] |
| **TG-Short-LS** | 3.48% | 0.577 | −13.17% | −18.24% | 0.066 | 0.111 | **0.199** | 1.20 | 1.16% | −0.73 | [−0.05, 1.36] |
| **TG-Short** | 3.27% | 0.622 | −10.29% | −13.17% | 0.134 | 0.201 | 0.366 | 1.00 | 0.00% | −0.69 | [0.01, 1.46] |
| **EW-Short-6m** | 3.14% | 0.450 | −17.57% | −18.97% | 0.089 | 0.412 | 0.563 | 1.00 | 0.00% | −0.86 | [−0.19, 1.47] |
| **EW-Short** | 1.01% | 0.176 | −13.63% | −19.46% | 0.005 | 0.436 | 0.629 | 1.00 | 0.00% | −1.13 | [−0.38, 1.08] |
| **LS-TSMOM** | 0.83% | 0.094 | −24.97% | −13.30% | −0.232 | 0.352 | 0.379 | 1.00 | 0.00% | −1.22 | [−0.56, 1.02] |
| **EW-Short-LS** | 0.37% | 0.057 | −15.46% | −21.28% | −0.018 | 0.472 | 0.582 | 1.20 | 1.16% | −1.25 | [−0.46, 0.91] |

Columns: Ann ret = net annualized return (after turnover + leverage cost); Sharpe =
net annualized; MaxDD = worst peak-to-trough; Both-down = annualized return in the 24
TEST months where external SPY **and** AGG are both negative; Upβ = β to equity on
equity-up months; Dnβ = β on equity-down months; Dn-corr = correlation with equity on
equity-down months; Gross = gross notional (Σ|pos|); Lev cost/yr = leverage drag
((gross−1)·5.8%); DSR = Deflated Sharpe (negative = edge **not** significant after
multiple-comparison adjustment); Sharpe CI = block-bootstrap 95% interval.

> **Verdict (measured, honest — round 2).** Two findings, one per half of the brief:
>
> 1. **One flavor beats All-Weather's 7.37% net OOS return — the RP winner (MinVar) at
>    9.29%** — but it is plain long-only risk parity with **no** asymmetry (Dnβ 0.585 >
>    Upβ 0.432, Dn-corr 0.747 ≈ AW). The measured answer to "higher expected return" is
>    **yes, long-only MinVar risk parity beats AW** (9.29% vs 7.37%) — but it does so by
>    holding *more* equity risk, so it is **more** correlated on the downside, not less.
>    Dropping the asymmetry constraint, return is beatable; keeping it, it is not (in this
>    window).
> 2. **No flavor beats 7.37% *with* the asymmetric property.** In **every** flavor Dnβ ≥
>    Upβ — the "correlated up, protected down" shape is not achieved by any construction
>    tested. The `gate_mode=short` lever does buy **real downside-correlation reduction**
>    (TG-Short-LS Dn-corr 0.199, TG-Short 0.366 vs AW 0.793) — partial progress on
>    "protected down" — but at the cost of return (3-5%) **and** upside capture (Upβ also
>    crushed to 0.06-0.13 by the MinVar base + 12m gate). The EW-Short family (real equity
>    weight + short-on-downside) was the strongest direct test of the construction and it
>    **whipsawed to 0.37-3.14%** — the lagged short sells the bottom of 2018 / the 2020
>    COVID rebound.
>
> **Structural blocker (consistent across both rounds):** a trailing 12m/6m momentum
> signal is *lagging* — long into drawdown starts (eats the downside), short/flat into
> rally starts (misses the upside) → Dnβ ≥ Upβ everywhere. Beating AW on return while
> keeping the asymmetric shape needs a **leading/faster downside signal** (MA crossover,
> regime filter, equity-below-its-10m-MA) that exits equity *before* the drawdown and
> re-enters *before* the rally — not more TSMOM lookback tuning (that is overfitting).
> Trust the DSR / bootstrap CI: every flavor's DSR is negative (edge not significant
> after multiple-comparison adjustment), the flavors share sleeves (effective N ≪
> nominal N), and this is one TRAIN/TEST split = one regime.

### Top picks (round 2 — a menu of good options, with the trade-off named)

- **Best return (beats AW, but no asymmetry):** **RP winner (MinVar)** — 9.29% / Sharpe
  0.921, but Dnβ 0.585 > Upβ 0.432, Dn-corr 0.747, both-down −30.50%, MaxDD −15.65%.
  Long-only risk parity; the return champion, the opposite of the asymmetric goal.
- **Best return WITH meaningful downside protection:** **TrendGate** — 5.95% / Sharpe
  0.640, Dn-corr 0.631 (vs AW 0.793), but ~1.4%/yr below AW and Dnβ 0.489 > Upβ 0.265.
- **Lowest downside correlation (the "protected down" leader):** **TG-Short-LS** —
  Dn-corr 0.199 (the lowest of any flavor, vs AW 0.793), Dnβ 0.111, MaxDD −13.17%, but
  3.48% net + 1.16%/yr leverage cost, DSR −0.73. The clearest downside-decorr, at a
  ~4%/yr return cost.
- **Best Sharpe of the short family:** **TG-Short-6m** — Sharpe 0.754, MaxDD −12.35%,
  5.09% net, gross 1.00 (no leverage cost), but Upβ 0.086 / Dnβ 0.340 (still
  Dnβ > Upβ). DSR −0.56.
- **Shallowest both-down of the short family:** **TG-Short** — both-down −13.17%,
  MaxDD −10.29%, Dn-corr 0.366, gross 1.00, but 3.27% net, DSR −0.69.

---

## 5a. Comparison menu — round 1 (measured, out-of-sample)

The round-1 menu (the four cash-gate flavors, `--score-mode asymmetric`) is preserved
at [`output/risk_parity_eval_asym/report_eval.md`](../output/risk_parity_eval_asym/report_eval.md)
§10. Reproduced here for completeness — the four cash-gate TrendProtect flavors vs
All-Weather, the risk-parity (MinVar) winner, and LS-TSMOM, over the same TEST window.
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

> **Round-1 verdict (measured, honest).** None of the four cash-gate flavors beat
> All-Weather's 7.37% net OOS return in this window after the 5.8%/yr leverage cost. The
> flavors buy a much better *risk* profile — TrendGate leads on Sharpe (1.385 vs AW
> 1.055), MaxDD (−4.20% vs −12.31%), both-down (−4.50% vs −18.74%) — at ~3%/yr of return.
> The asymmetric goal is only weakly met: the cash-gate keeps Upβ and Dnβ both low and
> Dnβ slightly exceeds Upβ (the 12m-lag works against the asymmetric shape). This
> round-1 finding motivated the round-2 `gate_mode=short` / EW-base / `asymmetric2`
> constructions in §3b and the §5 menu above.
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

*Research / illustration only. Not investment advice.*