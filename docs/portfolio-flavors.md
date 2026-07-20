# Portfolio Flavors — Construction, Composition & Measured Comparison

*Research / illustration only. Not investment advice.*

This catalogs every portfolio "flavor" evaluated in `risk_parity_eval.py`: the six
existing schemes (EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM) plus the **TrendProtect**
flavors added to answer the brief — *find an All-Weather variant with higher expected
return while keeping equity correlation asymmetric (correlated on the way up, low/negative
on the way down)*. The TrendProtect family grew in five rounds: **round 1** added four
cash-gate / overlay / structural-short flavors; **round 2** added six `gate_mode=short`
flavors (flip equity to net-short on the downside signal — the direct lever for negative
downside-β) and an `asymmetric2` score that rewards upside capture + return instead of
fleeing equity; **round 3** added three **leading-signal** flavors (MA crossover,
vol-regime, dual-MA) to fix round 2's lagging-momentum blocker; **round 4** added two
**directionally-asymmetric (hysteretic)** gates (fast downside exit, slow upside re-entry)
— the round-3 prescription made concrete, and the first flavor in the family to drive Dnβ
negative. **Round 4b** widened that hysteretic-gate search — a `slow_entry` ∈ {6, 9, 12}
grid plus a tighter band and a hysteretic vol-gate — to test whether a less-overshooting
re-entry can keep Upβ positive while Dnβ stays negative. For each flavor: the construction
formula, what it holds (gross / net, when it shorts), its parameters, the measured
out-of-sample metrics, and pros / cons.

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
- **Asymmetric2-score canonical** (round 3, +the three leading-signal flavors):
  [`output/risk_parity_eval_asym3/report_eval.md`](../output/risk_parity_eval_asym3/report_eval.md).
- **Asymmetric2-score canonical** (round 4, +the two hysteretic/asymmetric-gate flavors):
  [`output/risk_parity_eval_asym4/report_eval.md`](../output/risk_parity_eval_asym4/report_eval.md).
- **Asymmetric2-score canonical** (round 4b, +the four hysteretic-sweep flavors):
  [`output/risk_parity_eval_asym4b/report_eval.md`](../output/risk_parity_eval_asym4b/report_eval.md).

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
  (6m = faster, less lag, more whipsaw);
- `gate_signal` ("tsmom" | "ma" | "vol" | "dma" | "asym_ma" | "dd_stop", default "tsmom")
  — **round 3** (first four) / **round 4** (last two). Which signal drives the equity gate.
  **tsmom** = trailing-`lookback` return (the round-1/2 signal, *lagging* — long into
  drawdown starts, short/flat into rally starts). **ma** = price vs `lookback`-month SMA
  crossover (a *leading* signal — the MA crosses before the lookback-return flips sign).
  **dma** = fast 3m SMA vs slow `lookback`-month SMA (a smoother/faster crossover). **vol**
  = 6m realized vol vs its trailing 60m median (a *regime* filter — vol spikes lead
  drawdowns; different information set from price). **asym_ma** = *hysteretic* MA gate
  (round 4): LONG → SHORT when price < 3m SMA (fast exit), SHORT → LONG when price > 12m
  SMA (slow re-entry) — directionally **asymmetric**, the round-3 prescription. **dd_stop**
  = *hysteretic* trailing-stop (round 4): LONG → SHORT once drawdown from the 6m peak
  exceeds 10%, SHORT → LONG once within 3% of the peak. The new signals need a pre-window
  long enough for `slow_entry=12` / `dd_window=6`, so the engine pulls `max(lookback, 72)`
  months of pre-window history; the leading `vol` signal needs ~66m (a 60m median of a 6m
  realized vol), also covered.

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

## 3c. The three leading-signal flavors (round 3)

Round 2's measured negative result diagnosed a **structural blocker**, not a
parameter-tuning problem: trailing 12m/6m TSMOM momentum is a *lagging* signal — long
into drawdown starts (eats the downside), short/flat into rally starts (misses the
upside) → Dnβ ≥ Upβ in *every* round-2 flavor. Round 3 swaps the gate signal for three
**leading** downside signals (the `gate_signal` knob above), all EW-base + `gate_mode=short`
so equity keeps a real weight AND flips to net-short on the downside signal. The
hypothesis: a leading signal exits equity *before* the drawdown and re-enters *before* the
rally, breaking the lag.

### EW-MA-Short
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", gate_signal="ma",
  w_overlay=0.0, struct_short=None, lookback=10`.
- **Construction:** EW-Short driven by a **price-vs-10m-SMA crossover** — long equity when
  last month's level > the 10m SMA, net-short when below it. An MA crosses *before* a
  lookback-return flips sign, so the gate turns before the TSMOM gate would.
- **Holds:** the equal-weight combo, equity net-short when price < 10m SMA. Gross ≤ 1.
- **When it shorts:** equity sleeves when price is below its 10m SMA.
- **Parameters:** `gate_signal="ma"`, `lookback=10`, `base_mode="ew"`.
- **Pros:** the **leading** signal — best downside protection in the entire 10-flavor
  family (both-down −11.24% vs AW −18.74%, Dn-corr 0.259 vs AW 0.793 — both best-in-class),
  beating the lagging-TSMOM EW-Short family (−18.97% / 0.563) decisively. The round-2
  downside blocker is genuinely fixed. Gross ≤ 1 (no leverage cost).
- **Cons:** trades "miss less downside" for "miss more upside" — Upβ collapsed to 0.014
  (vs TrendGate 0.265): the MA gate exits before rallies too. So the shape inverts to
  "protected down, NOT correlated up." MA crossover whipsaws in sideways tape.
- **Regime wins/loses:** wins in sustained trends (2008, 2022); whipsaws in choppy
  sideways markets (2015, 2023).

### EW-Vol-Short
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", gate_signal="vol",
  w_overlay=0.0, struct_short=None`.
- **Construction:** EW-Short driven by a **vol-regime filter** — net-short equity when 6m
  realized vol exceeds its trailing 60m median (a vol spike = risk-off regime), long when
  vol is calm. A different information set from price (vol, not trend).
- **Holds:** the equal-weight combo, equity net-short in high-vol regimes. Gross ≤ 1.
- **When it shorts:** equity sleeves when 6m realized vol > its 60m median.
- **Parameters:** `gate_signal="vol"`, `vol_window=6`, `vol_median=60`, `base_mode="ew"`.
- **Pros:** diversifies the signal family (vol, not price); the 60m median is a stable
  regime reference. Real equity weight (EW base).
- **Cons:** **disaster in this window** — −1.52% return, −31.69% MaxDD (worst in the
  family). Vol spikes *coincide* with drawdowns but *persist through rebounds* (vol stayed
  elevated through the 2020 COVID V-rebound), so the signal shorted the bottom of the
  rebound. Vol is coincident-to-lagging, not leading, for equity drawdowns. DSR −1.49.
- **Regime wins/loses:** wins in vol-clustered bear markets (2008); loses badly in
  V-shaped rebounds where vol stays high (2020).

### EW-DMA-Short
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", gate_signal="dma",
  w_overlay=0.0, struct_short=None, lookback=10`.
- **Construction:** EW-Short driven by a **dual-MA crossover** — fast 3m SMA vs slow 10m
  SMA. Long equity when the fast MA > slow MA, net-short when below. The slow MA smooths
  the reference (fewer false flips than the single-MA gate, in theory).
- **Holds:** the equal-weight combo, equity net-short when 3m SMA < 10m SMA. Gross ≤ 1.
- **When it shorts:** equity sleeves on the fast/slow MA bearish cross.
- **Parameters:** `gate_signal="dma"`, `fast=3`, `slow=10`, `base_mode="ew"`.
- **Pros:** leading signal; the slow-MA reference should smooth chop. Real equity weight.
- **Cons:** **mediocre** — 2.02% return, −20.92% MaxDD. The fast 3m SMA is too noisy
  (whipsaws) and the slow 10m MA adds lag vs the single-MA gate — the worst of both. Dn-corr
  0.495 (worse than EW-MA-Short 0.259). DSR −1.04.
- **Regime wins/loses:** between EW-MA-Short and EW-Short on every axis; no clear win.

---

## 3d. The two asymmetric (hysteretic) gate flavors (round 4)

Rounds 1-3 all used **symmetric** gate signals — a price/vol rule that is equally
trigger-happy in both directions, so any signal that exits before a drawdown also exits
before *some* rallies, and **Dnβ ≥ Upβ in every single one of the 16 prior flavors**.
Round 4 makes the round-3 prescription concrete: a **directionally-asymmetric (hysteretic)**
gate — *fast* to flee equity on the downside (exit on a small break), *slow* to return on
the upside (re-enter only on a clear recovery). The state is a per-sleeve flip-flop with
hysteresis; it starts LONG and holds through chop above the fast trigger, so it stays
correlated on the way up and only goes net-short after a clear break. Two new
`gate_signal` values (`"asym_ma"`, `"dd_stop"`) implement this in `_gate_signal`; the
existing `tsmom`/`ma`/`vol`/`dma` paths are untouched. The engine pulls `max(lookback,
72)` months of pre-window history (enough for `slow_entry=12` and `dd_window=6`).

### EW-AsymMA-Short
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", gate_signal="asym_ma",
  w_overlay=0.0, struct_short=None, lookback=10`.
- **Construction:** EW-Short driven by a **hysteretic MA gate**. State starts LONG. LONG →
  SHORT when `price < 3m SMA` (fast exit on a break); SHORT → LONG when `price > 12m SMA`
  (slow re-entry only on a clear recovery). The fast/slow-MA gap is the hysteresis band:
  once short, the sleeve needs a *new 12m-high-style* recovery to flip back, so it does not
  whipsaw on every bounce. Equity net-short in the SHORT state, net-long in the LONG state;
  bonds/gold/diversifiers stay long. Gross ≤ 1 (sleeve-level netting).
- **Holds:** the equal-weight combo; equity long through chop above the 3m SMA, net-short
  once price breaks below it, back to long only once price reclaims the 12m SMA.
- **When it shorts:** equity sleeves after a fast-MA break, until a slow-MA recovery.
- **Parameters:** `gate_signal="asym_ma"`, `fast_exit=3`, `slow_entry=12`, `base_mode="ew"`.
- **Pros:** the round-3 prescription made concrete — asymmetric by construction (fast exit,
  slow re-entry). Real equity weight (EW base). The first flavor in the whole 18-flavor
  family to drive Dnβ **negative** (−0.049) and Dn-corr **negative** (−0.060) — real,
  measured downside protection (the sleeve genuinely moves *against* equities on down
  months).
- **Cons:** the slow 12m re-entry overshoots — it stays short through the start of rallies
  too, so **Upβ also goes negative** (−0.124). Net shape: "negatively correlated *always*"
  (a short-leaning book), not "correlated up, protected down" — Upβ (−0.124) < Dnβ (−0.049),
  so the asymmetric property is **still not met**. Return 3.43% < AW 7.37%; MaxDD −17.22%;
  DSR −0.90. Stateful + two MA horizons → more overfitting surface; one split = one regime.
- **Regime wins/loses:** wins on downside protection (negative Dnβ/Dn-corr — unique in the
  family); loses on upside capture (negative Upβ) and return. The hysteresis moved the
  betas from "protected down, not up" (round 3) into "negative both ways" — closer in
  *direction* to the goal but it overshot the upside half.

### EW-DDStop-Short
- **Preset:** `trend_gate=True, gate_mode="short", base_mode="ew", gate_signal="dd_stop",
  w_overlay=0.0, struct_short=None, lookback=10`.
- **Construction:** EW-Short driven by a **hysteretic trailing-stop gate** — the most direct
  map to the brief. State starts LONG. LONG → SHORT once the sleeve's drawdown from its
  trailing 6m peak exceeds 10% (fast exit — a clear break); SHORT → LONG once it recovers
  inside 3% of the peak (slow re-entry, near a new high). "Flee the break, wait for a new
  high." Inherently asymmetric: the trigger is "you've fallen >10%", the re-entry is "you've
  made a new high" — quick to flee, slow to return. Equity net-short in the SHORT state;
  bonds/gold/diversifiers stay long. Gross ≤ 1 (sleeve-level netting).
- **Holds:** the equal-weight combo; equity long near a 6m high, net-short once it has
  fallen >10% off that high, back to long only once it makes a new ~6m high.
- **When it shorts:** equity sleeves after a >10% drawdown from the trailing 6m peak.
- **Parameters:** `gate_signal="dd_stop"`, `dd_window=6`, `dd_exit=0.10`, `dd_entry=0.03`,
  `base_mode="ew"`.
- **Pros:** the most literal asymmetric shape — the exit trigger and the re-entry trigger
  are different *quantities* (a 10% loss vs a new high), so hysteresis is structural, not
  just a wider band. Real equity weight (EW base); the direct "flee the break" downside
  insurance the brief asked for.
- **Cons:** **failed on the asymmetric property** — Dnβ 0.536 >> Upβ 0.106 (the gap is the
  *wrong way* and large). A slow grind-down (2018, 2022) hits the 10% stop *late* (price has
  already fallen), and re-entering on a "new 6m high" *lags* a V-rebound (2020) — both
  triggers are themselves lagging, so the hysteresis does not help. Return 2.71%, MaxDD
  −24.01%, both-down −23.75%, DSR −1.01 — the worst of the four leading/asymmetric flavors.
  Drawdown thresholds (10%/3%) and the 6m window are tuned → overfitting surface; one
  split = one regime.
- **Regime wins/loses:** loses on nearly every axis — the lagging triggers defeat the
  asymmetry. Confirms that a *leading* fast-exit (as in EW-AsymMA-Short) is needed; a
  drawdown-percentage stop is itself a lagging signal.

---

## 3e. The hysteretic-gate sweep (round 4b)

Round 4's EW-AsymMA-Short drove Dnβ negative (−0.049) — a first — but its slow 12m
re-entry also drove Upβ negative (−0.124): the sleeve stayed short through the *start* of
rallies, so the "less overshoot" hypothesis was that a *faster* re-entry could keep Upβ
positive while Dnβ stayed negative. Round 4b tests that directly by widening the
hysteretic-gate band. The `_backtest_flavor` engine now threads per-preset hysteresis
params (`slow_entry`, `fast_exit`, `dd_*`, vol thresholds) into `_gate_signal` — the
helper defaults are used when a preset omits them, so the round-4 / round-3 / round-1-2
presets are **byte-identical** to their originals (verified: the rolling re-enumeration
over the 3 base schemes is byte-identical between the round-4 and round-4b runs, and
EW-AsymMA-Short / EW-DDStop-Short produce identical numbers). Four new presets:

### EW-AsymMA-Short-6 / EW-AsymMA-Short-9 / EW-AsymMA-Tight
- **Presets:** EW-AsymMA-Short with `slow_entry` ∈ {6, 9} (vs the round-4 default 12) and
  `fast_exit` = 3; plus **EW-AsymMA-Tight** with `slow_entry=6, fast_exit=2` (the tightest
  band: fastest to flee, fastest to return). All else equal to EW-AsymMA-Short.
- **Construction / holds / shorts:** identical to EW-AsymMA-Short — only the hysteresis
  band changes. Faster re-entry re-loads equity on a smaller recovery.
- **Parameters:** `gate_signal="asym_ma"`, `slow_entry` ∈ {6, 9}, `fast_exit` ∈ {2, 3}.
- **Why these three:** bracket the Upβ-vs-Dnβ trade-off across the band. The grid
  {12, 9, 6} × fast_exit 3, plus the tight {6}×{2} corner, spans "slow re-entry (most
  downside protection, most upside overshoot)" → "fast re-entry (least overshoot, most
  whipsaw)."

### EW-AsymVol-Short
- **Preset:** `gate_signal="asym_vol"`, EW-base, `gate_mode="short"`, gross ≤ 1.
- **Construction:** a **hysteretic vol-regime** gate — LONG → SHORT once the prior month's
  6m realized vol exceeds its trailing 60m median (fast exit on stress), SHORT → LONG once
  vol falls back below 0.85× the median (slow re-entry — wait for genuine calm). The
  hysteresis band = 0.85–1.0× the median; a vol spike flees, vol must *genuinely* calm to
  return. New `asym_vol` branch in `_gate_signal` (gated, opt-in).
- **Why:** fixes the round-3 EW-Vol-Short, which shorted the 2020 COVID V-rebound (vol
  stayed elevated through the rally → the symmetric vol-gate never re-entered long →
  −1.52% / −31.69% MaxDD). A hysteretic lower-bar re-entry waits for vol to actually
  calm. Different information set from price-MA → diversifies the signal family.

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

# Asymmetric2-score canonical (round 3, +three leading-signal flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym3
# → output/risk_parity_eval_asym3/report_eval.md (§10 = the round-3 menu)

# Asymmetric2-score canonical (round 4, +two hysteretic/asymmetric-gate flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym4
# → output/risk_parity_eval_asym4/report_eval.md (§10 = the round-4 menu)

# Asymmetric2-score canonical (round 4b, +four hysteretic-sweep flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym4b
# → output/risk_parity_eval_asym4b/report_eval.md (§10 = the round-4b sweep menu)

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
---

## 5b. Comparison menu — round 3 (measured, out-of-sample)

Ranked table — all ten TrendProtect flavors (the round-2 `gate_mode=short` / EW-base
family **plus** the three round-3 leading-signal flavors) vs All-Weather and the
risk-parity (MinVar) winner — over the **TEST 2018-01 → 2026-07** window, net of 10 bps/side
turnover cost **and** the 5.8% APR leverage cost (where gross > 1). Generated as **§10** of
the round-3 asymmetric2 canonical report:
[`output/risk_parity_eval_asym3/report_eval.md`](../output/risk_parity_eval_asym3/report_eval.md).
Sorted by net annualized return.

| Portfolio | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **RP winner (MinVar)** | **9.29%** | 0.921 | −15.65% | −30.50% | 0.432 | 0.585 | 0.747 | 1.00 | 0.00% | — | — |
| **All-Weather (bar)** | 7.37% | **1.055** | −12.31% | −18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| **TrendGate** | 5.95% | 0.640 | −15.78% | −31.85% | 0.265 | 0.489 | 0.631 | 1.00 | 0.00% | −0.67 | [−0.01, 1.48] |
| **TG-Short-6m** | 5.09% | 0.754 | −12.35% | −15.27% | 0.086 | 0.340 | 0.474 | 1.00 | 0.00% | −0.56 | [0.06, 1.72] |
| **TG-Short-LS** | 4.13% | 0.448 | −20.50% | −23.99% | 0.056 | 0.294 | 0.347 | 1.20 | 1.16% | −0.86 | [−0.25, 1.29] |
| **EW-MA-Short** *(new)* | 4.08% | 0.687 | −12.46% | **−11.24%** | 0.014 | 0.125 | **0.259** | 1.00 | 0.00% | −0.62 | [−0.02, 1.52] |
| **TG-Short** | 3.27% | 0.622 | −10.29% | −13.17% | 0.134 | 0.201 | 0.366 | 1.00 | 0.00% | −0.69 | [0.01, 1.46] |
| **EW-Short-6m** | 3.30% | 0.414 | −20.58% | −20.18% | 0.091 | 0.460 | 0.542 | 1.00 | 0.00% | −0.90 | [−0.24, 1.43] |
| **EW-DMA-Short** *(new)* | 2.02% | 0.273 | −20.92% | −15.83% | 0.035 | 0.396 | 0.495 | 1.00 | 0.00% | −1.04 | [−0.38, 1.26] |
| **EW-Short** | 1.01% | 0.176 | −13.63% | −19.46% | 0.005 | 0.436 | 0.629 | 1.00 | 0.00% | −1.13 | [−0.38, 1.08] |
| **LS-TSMOM** | 1.87% | 0.159 | −34.71% | −17.12% | −0.315 | 0.462 | 0.392 | 1.00 | 0.00% | −1.15 | [−0.64, 1.11] |
| **EW-Short-LS** | 0.37% | 0.057 | −15.46% | −21.28% | −0.018 | 0.472 | 0.582 | 1.20 | 1.16% | −1.25 | [−0.46, 0.91] |
| **EW-Vol-Short** *(new)* | −1.52% | −0.182 | −31.69% | −13.96% | −0.006 | 0.275 | 0.277 | 1.00 | 0.00% | −1.49 | [−0.75, 0.49] |

Columns: Ann ret = net annualized return (after turnover + leverage cost); Sharpe =
net annualized; MaxDD = worst peak-to-trough; Both-down = annualized return in the 24
TEST months where external SPY **and** AGG are both negative; Upβ = β to equity on
equity-up months; Dnβ = β on equity-down months; Dn-corr = correlation with equity on
equity-down months; Gross = gross notional (Σ|pos|); Lev cost/yr = leverage drag
((gross−1)·5.8%); DSR = Deflated Sharpe (negative = edge **not** significant after
multiple-comparison adjustment); Sharpe CI = block-bootstrap 95% interval.

> **Verdict (measured, honest — round 3).** The leading-signal hypothesis is
> **partially confirmed — and it isolates the fundamental tension.**
>
> 1. **The round-2 downside blocker IS fixed — by EW-MA-Short.** The MA crossover (a
>    *leading* signal) achieves the **best downside protection in the entire 10-flavor
>    family**: both-down **−11.24%** (vs AW −18.74%, and vs the lagging-TSMOM EW-Short
>    family −18.97% to −20.18%) and Dn-corr **0.259** (vs AW 0.793, vs EW-Short 0.629 —
>    the lowest of any flavor, beating the round-2 TG-Short-LS 0.347). The MA gate
>    genuinely exits equity *before* the drawdown. This is real, measured progress on the
>    "protected down" half of the brief, and it confirms the round-2 diagnosis (the blocker
>    was the lagging signal, not the construction).
> 2. **BUT it trades "miss less downside" for "miss more upside."** Upβ collapsed to
>    **0.014** (vs TrendGate 0.265, AW 0.327) — the MA gate exits before rallies too (false
>    positives). So the asymmetric shape **inverts**: round 2 was "correlated up but NOT
>    protected down"; round 3's EW-MA-Short is "**protected down but NOT correlated up**."
>    Return 4.08% < AW 7.37%. The other two leading signals are worse: **EW-Vol-Short**
>    whipsawed to **−1.52%** / MaxDD −31.69% (vol stays elevated through the 2020 COVID
>    V-rebound → the signal shorts the bottom); **EW-DMA-Short** was mediocre (2.02%).
> 3. **Still no flavor beats 7.37% *with* the asymmetric property.** Across all three
>    rounds (16 flavors), **Dnβ ≥ Upβ in every single one** — no construction achieves
>    "correlated up, protected down." The RP winner (9.29%) beats on return but with the
>    *most* downside correlation (Dnβ 0.585 > Upβ 0.432). Every flavor's DSR is negative.
>
> **The fundamental tension (the real round-3 finding):** "correlated up, protected down"
> requires an **asymmetric signal** — confident/trigger-happy on the downside (exits
> equity) but relaxed on the upside (stays long through chop). A **symmetric** price
> filter — MA, TSMOM, dual-MA, vol-regime — is equally trigger-happy in both directions:
> any signal that exits before a drawdown also exits before *some* rallies. So a symmetric
> gate can optimize *either* the downside half (EW-MA-Short: great Dn-corr, no upside) or
> the upside half (TrendGate/MinVar: decent Upβ, no downside protection), but not both.
> Breaking this needs a **directionally-asymmetric** gate for round 4 — e.g. a fast
> downside-only trigger (exit on a sharp drop / vol spike) paired with a slow-or-no upside
> trigger (stay long through chop), or a defined-downside insurance overlay (put spreads /
> trend-downside-stop) that does not cap the upside. Trust the DSR / bootstrap CI: every
> flavor's DSR is negative, the flavors share sleeves (effective N ≪ nominal N), and
> this is one TRAIN/TEST split = one regime.

### Top picks (round 3 — the menu updated)

- **Best downside protection of all 16 flavors (the "protected down" champion):**
  **EW-MA-Short** — both-down −11.24%, Dn-corr 0.259, MaxDD −12.46%, gross 1.00 (no
  leverage cost), Sharpe 0.687. The leading MA signal fixes the round-2 lag. The cost is
  upside: Upβ 0.014, return 4.08% (< AW). DSR −0.62.
- **Best return (beats AW, but no asymmetry):** **RP winner (MinVar)** — 9.29% / Sharpe
  0.921, but Dnβ 0.585 > Upβ 0.432, Dn-corr 0.747, both-down −30.50%. Unchanged from
  round 2 (long-only risk parity).
- **Best return WITH meaningful downside protection:** **TrendGate** — 5.95% / Sharpe
  0.640, Dn-corr 0.631, but ~1.4%/yr below AW and Dnβ 0.489 > Upβ 0.265. Unchanged.
- **Best Sharpe of the short family:** **TG-Short-6m** — Sharpe 0.754, MaxDD −12.35%,
  5.09% net, gross 1.00, but Dnβ 0.340 > Upβ 0.086. Unchanged.
- **Avoid:** **EW-Vol-Short** (−1.52%, −31.69% MaxDD — vol-regime shorts the 2020 rebound)
  and **EW-DMA-Short** (2.02%, no edge over EW-MA-Short).

## 5c. Comparison menu — round 4 (measured, out-of-sample)

Round 4 tests the round-3 prescription directly: two **directionally-asymmetric (hysteretic)**
gates — fast downside exit, slow upside re-entry — vs the full prior 16-flavor family,
All-Weather, and the MinVar winner. Net of the 5.8%/yr leverage cost on gross > 1. Source:
`output/risk_parity_eval_asym4/report_eval.md` §10 (18 schemes, 50706 TRAIN trials).

| Portfolio | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather | 7.37% | **1.055** | −12.31% | −18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| RP winner | 9.29% | **0.921** | −15.65% | −30.50% | 0.432 | 0.585 | 0.747 | 1.00 | 0.00% | — | — |
| EW-MA-Short *(r3)* | 4.08% | **0.687** | −12.46% | −11.24% | 0.014 | 0.125 | 0.259 | 1.00 | 0.00% | −0.62 | [−0.02, 1.52] |
| TG-Short *(r2)* | 3.27% | **0.622** | −10.29% | −13.17% | 0.134 | 0.201 | 0.366 | 1.00 | 0.00% | −0.69 | [0.01, 1.46] |
| TG-Short-6m *(r2)* | 4.62% | **0.588** | −16.31% | −20.18% | 0.110 | 0.421 | 0.513 | 1.00 | 0.00% | −0.72 | [−0.07, 1.61] |
| TG-Short-LS *(r2)* | 4.13% | **0.448** | −20.50% | −23.99% | 0.056 | 0.294 | 0.347 | 1.20 | 1.16% | −0.86 | [−0.25, 1.29] |
| EW-Short-6m *(r2)* | 3.30% | **0.414** | −20.58% | −20.18% | 0.091 | 0.460 | 0.542 | 1.00 | 0.00% | −0.90 | [−0.24, 1.43] |
| **EW-AsymMA-Short** *(new)* | 3.43% | **0.406** | −17.22% | −17.76% | **−0.124** | **−0.049** | **−0.060** | 1.00 | 0.00% | −0.90 | [−0.28, 1.15] |
| EW-Short *(r2)* | 2.67% | **0.348** | −20.06% | −16.68% | 0.018 | 0.561 | 0.607 | 1.00 | 0.00% | −0.96 | [−0.25, 1.50] |
| **EW-DDStop-Short** *(new)* | 2.71% | **0.299** | −24.01% | −23.75% | 0.106 | 0.536 | 0.587 | 1.00 | 0.00% | −1.01 | [−0.35, 1.27] |
| EW-DMA-Short *(r3)* | 2.02% | **0.273** | −20.92% | −15.83% | 0.035 | 0.396 | 0.495 | 1.00 | 0.00% | −1.04 | [−0.38, 1.26] |
| EW-Vol-Short *(r3)* | −1.52% | **−0.182** | −31.69% | −13.96% | −0.006 | 0.275 | 0.277 | 1.00 | 0.00% | −1.49 | [−0.75, 0.49] |

> **Verdict (measured, honest — round 4).** The asymmetric-gate hypothesis is **partially
> confirmed, and it produces a first — but the property is still not met.**
> 1. **EW-AsymMA-Short is the first flavor in the entire 18-flavor family (4 rounds) to drive
>    Dnβ negative (−0.049) and Dn-corr negative (−0.060).** The hysteretic gate (fast 3m-MA
>    exit, slow 12m-MA re-entry) genuinely flips the equity sleeve net-short *against*
>    equities on down months — real, measured downside protection that no symmetric gate
>    achieved. This is a step-change: round-3's best (EW-MA-Short) had Dnβ +0.125; round 4
>    takes it negative.
> 2. **BUT the slow re-entry overshoots — Upβ also went negative (−0.124).** Staying short
>    until price reclaims the 12m SMA means the sleeve is still short through the *start* of
>    rallies (the V-rebound), so it misses the upside it was supposed to capture. Net shape:
>    "**negatively correlated *always***" (a short-leaning book), not "correlated up,
>    protected down." Upβ (−0.124) < Dnβ (−0.049), so **Upβ > Dnβ is still not achieved** —
>    the asymmetric property the brief wants remains unsatisfied, now in its 4th direct test.
>    Return 3.43% < AW 7.37%; DSR −0.90 (insignificant).
> 3. **EW-DDStop-Short failed outright.** Dnβ 0.536 >> Upβ 0.106 — the gap is the *wrong way*
>    and large. A drawdown-percentage stop (exit at −10% off a 6m peak) is itself a *lagging*
>    signal (price has already fallen), and re-entering on a "new 6m high" *lags* a
>    V-rebound — so the hysteresis, built on two lagging triggers, does not produce the
>    asymmetry. MaxDD −24.01%, both-down −23.75%, DSR −1.01 — the worst of the four
>    leading/asymmetric flavors. Confirms a *leading* fast-exit (as in EW-AsymMA-Short) is
>    necessary; a drawdown stop is not it.
> 4. **No flavor beats 7.37% with the asymmetric property.** Across all four rounds (18
>    flavors), **Dnβ ≥ Upβ in every single one.** The RP winner (9.29%) beats on return with
>    the *most* downside correlation. Every flavor's DSR is negative.
>
> **The round-4 finding (what the asymmetry bought and what it cost):** hysteresis *can*
> flip Dnβ negative — the round-3 prescription was right that an asymmetric signal is the
> lever for downside protection. But the same slow re-entry that protects the downside
> *also* suppresses the upside (Upβ goes negative with it), so the two halves of the brief
> still cannot both be satisfied by a single price-gate in one TRAIN/TEST split. The
> family has now spanned the full space: round 2 = "correlated up, NOT protected down";
> round 3 = "protected down, NOT correlated up"; round 4 = "negatively correlated both ways."
> The remaining lever is to **decouple the two halves entirely** — keep a *long-only* base
> for the upside (so Upβ stays positive) and add a **defined-downside insurance overlay**
> (put spread / explicit downside-stop on a separate notional) that does not flip the long
> book short. That keeps the upside capture while capping the downside — the construction
> the brief's "long-term short a ticker" permission hints at, but as an *overlay*, not a
> gate that replaces the long. Not yet implemented. Trust the DSR / bootstrap CI: every
> flavor's DSR is negative, the flavors share sleeves (effective N ≪ nominal N), and this
> is one TRAIN/TEST split = one regime.

### Top picks (round 4 — the menu updated)

- **Best downside protection of all 18 flavors (the "protected down" champion):**
  **EW-AsymMA-Short** — the only flavor with **negative** Dnβ (−0.049) and Dn-corr (−0.060);
  both-down −17.76%, gross 1.00 (no leverage cost), Sharpe 0.406. The hysteretic gate is the
  round-3 prescription made concrete. The cost is upside: Upβ −0.124 (also negative — the
  slow re-entry shorts the rally start), return 3.43% (< AW). DSR −0.90.
- **Best downside protection *with* positive upside (round-3 champion still stands):**
  **EW-MA-Short** — both-down −11.24%, Dn-corr 0.259, MaxDD −12.46%, Upβ 0.014 (still
  positive), Sharpe 0.687. Round 4 did not displace it: EW-AsymMA-Short has lower (negative)
  Dnβ but threw away the upside to get it. Pick by whether you want the upside floor
  (EW-MA-Short) or the purest downside hedge (EW-AsymMA-Short).
- **Best return (beats AW, but no asymmetry):** **RP winner (MinVar)** — 9.29% / Sharpe
  0.921, but Dnβ 0.585 > Upβ 0.432, Dn-corr 0.747. Unchanged across all four rounds
  (long-only risk parity).
- **Avoid:** **EW-DDStop-Short** (Dnβ 0.536 >> Upβ 0.106, MaxDD −24.01% — lagging triggers
  defeat the asymmetry), **EW-Vol-Short** (−1.52%, −31.69% MaxDD — shorts the 2020
  rebound), and **EW-DMA-Short** (2.02%, no edge).

## 5d. Comparison menu — round 4b (measured, out-of-sample)

Round 4b widens the hysteretic-gate search to test the "less overshoot" hypothesis: can a
*faster* re-entry (round 4's slow_entry=12 drove Upβ negative) keep Upβ **positive** while
Dnβ stays **negative**? Four new presets — the `slow_entry` ∈ {6, 9} grid, the tight
{6}×{2} band, and a hysteretic vol-gate — vs the prior family, All-Weather, and the MinVar
winner. Net of the 5.8%/yr leverage cost. Source: `output/risk_parity_eval_asym4b/report_eval.md`
§10 (22 schemes, 61974 TRAIN trials).

| Portfolio | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather | 7.37% | **1.055** | −12.31% | −18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| RP winner | 9.29% | **0.921** | −15.65% | −30.50% | 0.432 | 0.585 | 0.747 | 1.00 | 0.00% | — | — |
| TrendGate | 7.32% | **0.719** | −17.99% | −27.88% | 0.310 | 0.543 | 0.628 | 1.00 | 0.00% | −0.59 | [0.07, 1.68] |
| TG-Short *(r2)* | 3.27% | **0.622** | −10.29% | −13.17% | 0.134 | 0.201 | 0.366 | 1.00 | 0.00% | −0.69 | [0.01, 1.46] |
| EW-MA-Short *(r3)* | 4.25% | **0.613** | −14.02% | −12.97% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | −0.70 | [−0.08, 1.40] |
| TG-Short-6m *(r2)* | 4.62% | **0.588** | −16.31% | −20.18% | 0.110 | 0.421 | 0.513 | 1.00 | 0.00% | −0.72 | [−0.07, 1.61] |
| **EW-AsymMA-Short-6** *(new)* | 4.80% | **0.565** | −14.83% | −17.03% | −0.113 | −0.026 | −0.032 | 1.00 | 0.00% | −0.75 | [−0.10, 1.30] |
| **EW-AsymMA-Short-9** *(new)* | 4.27% | **0.508** | −14.10% | −16.70% | −0.107 | −0.041 | −0.050 | 1.00 | 0.00% | −0.80 | [−0.14, 1.23] |
| TG-Short-LS *(r2)* | 4.13% | **0.448** | −20.50% | −23.99% | 0.056 | 0.294 | 0.347 | 1.20 | 1.16% | −0.86 | [−0.25, 1.29] |
| EW-Short-6m *(r2)* | 3.30% | **0.414** | −20.58% | −20.18% | 0.091 | 0.460 | 0.542 | 1.00 | 0.00% | −0.90 | [−0.24, 1.43] |
| **EW-AsymMA-Tight** *(new)* | 1.99% | **0.412** | −14.05% | **−8.79%** | **−0.111** | **−0.111** | **−0.254** | 1.00 | 0.00% | −0.90 | [−0.34, 1.14] |
| EW-AsymMA-Short *(r4)* | 3.43% | **0.406** | −17.22% | −17.76% | −0.124 | −0.049 | −0.060 | 1.00 | 0.00% | −0.90 | [−0.28, 1.15] |
| EW-Short *(r2)* | 2.67% | **0.348** | −20.06% | −16.68% | 0.018 | 0.561 | 0.607 | 1.00 | 0.00% | −0.96 | [−0.25, 1.50] |
| EW-DDStop-Short *(r4)* | 2.71% | **0.299** | −24.01% | −23.75% | 0.106 | 0.536 | 0.587 | 1.00 | 0.00% | −1.01 | [−0.35, 1.27] |
| EW-Vol-Short *(r3)* | 1.77% | **0.247** | −22.29% | −13.87% | 0.040 | 0.383 | 0.436 | 1.00 | 0.00% | −1.06 | [−0.38, 1.35] |
| EW-DMA-Short *(r3)* | 1.78% | **0.206** | −24.53% | −18.48% | 0.038 | 0.448 | 0.486 | 1.00 | 0.00% | −1.11 | [−0.41, 1.16] |
| **EW-AsymVol-Short** *(new)* | −1.16% | **−0.161** | −24.10% | −11.70% | 0.024 | 0.284 | 0.335 | 1.00 | 0.00% | −1.47 | [−0.70, 0.48] |

> **Verdict (measured, honest — round 4b). The "less overshoot" hypothesis is
> DISCONFIRMED — the sweep rules out the re-entry-lag explanation and isolates the
> structural blocker.**
> 1. **Faster re-entry did NOT restore Upβ.** Across the whole `asym_ma` family Upβ is
>    pinned at ≈ −0.11 regardless of `slow_entry` (−0.124 at 12, −0.107 at 9, −0.113 at 6,
>    −0.111 tight). The "slow 12m re-entry overshoots the rally" story from round 4 is
>    wrong — re-entering at 6m doesn't help. So the negative Upβ is **not** a re-entry-lag
>    tunable; it is **structural** to the `gate_mode=short` construction: once the gate
>    flips the equity sleeve short after any break, that sleeve is short through the early
>    part of recoveries, and the EW base's other sleeves (bonds/gold/commodities) don't
>    track equity up-moves — so the portfolio's up-month beta is dominated by the (short)
>    equity sleeve and goes negative. You cannot fix it by tuning the band.
> 2. **The downside protection IS robust to the band — Dnβ stays negative.** Every
>    `asym_ma` variant holds Dnβ ≤ −0.03 (−0.049, −0.041, −0.026, −0.111) with negative
>    Dn-corr. The hysteretic gate reliably flips equity short *against* the market on down
>    months — that part of round 4's finding is robust, not a parameter fluke. The
>    **EW-AsymMA-Tight** band (fast_exit=2, slow_entry=6) even hits both-down **−8.79%**
>    (the best of *any* flavor across all rounds — better than round-3 EW-MA-Short's
>    −12.97%) and Dn-corr **−0.254** (the most negative of all), Sharpe 0.412 — but at the
>    cost of Upβ collapsing to **exactly** Dnβ (−0.111 = −0.111): the asymmetry *vanished*
>    (both negative). The tighter the band, the more symmetric (both negative), not the
>    more asymmetric.
> 3. **EW-AsymVol-Short failed** — Sharpe −0.161, Upβ 0.024 / Dnβ 0.284 (Dnβ >> Upβ). Vol
>    hysteresis did **not** fix the V-rebound problem: vol stays elevated *through* rallies
>    (vol calms late), so even the slow 0.85×-median re-entry re-enters after the rally's
>    best months, and the gate shorts the rebound. The vol-regime gate is the wrong
>    information set for "correlated up, protected down" (vol is a *coincident* stress
>    indicator, not a leading one — it rises *as* price falls, not before).
> 4. **No flavor beats 7.37% with the asymmetric property.** Across all four rounds
>    (22 flavors), **Dnβ ≥ Upβ in every single one** where the betas differ; the two
>    flavors with Upβ = Dnβ (EW-AsymMA-Tight, both −0.111) are *symmetric* (both negative),
>    not asymmetric. The RP winner (9.29%) beats on return with the most downside
>    correlation. Every flavor's DSR is negative.
>
> **The round-4b finding (what the sweep settled):** the negative-Dnβ / negative-Upβ
> coupling is **structural to shorting equity on a downside gate**, not a tunable lag.
> A single price-gate that flips the equity sleeve short cannot be "correlated up,
> protected down" — shorting equity through recoveries necessarily kills the upside.
> This rules out further band-tuning (the grid is now spanned: 6/9/12 × 2/3 + vol) and
> confirms the round-4 lever is the only remaining one: **decouple the two halves
> entirely** — keep a *long-only* base for the upside (so Upβ stays positive) and add a
> **defined-downside insurance overlay** (put spread / explicit downside-stop on a
> *separate* notional) that caps the downside *without* flipping the long book short. The
> brief's "long-term short a ticker" permission points at exactly this, as an overlay not
> a gate. Trust the DSR / bootstrap CI: every flavor's DSR is negative, the flavors share
>    sleeves (effective N ≪ nominal N), and this is one TRAIN/TEST split = one regime.

### Top picks (round 4b — the menu updated)

- **Best downside protection of all 22 flavors (the "protected down" champion):**
  **EW-AsymMA-Tight** — both-down **−8.79%** (best of any flavor across all rounds),
  Dn-corr **−0.254** (most negative of all), MaxDD −14.05%, gross 1.00, Sharpe 0.412.
  The tightest hysteretic band. BUT Upβ = Dnβ = −0.111 (the asymmetry vanished — both
  negative; it's a symmetric short-leaning book, not "correlated up, protected down").
  Return 1.99% (< AW). DSR −0.90. Pick this if pure downside hedge is the goal.
- **Best return of the hysteretic family:** **EW-AsymMA-Short-6** — 4.80% / Sharpe 0.565
  (best of the asym_ma family), Dnβ −0.026 / Dn-corr −0.032 (still negative), gross 1.00.
  The faster re-entry lifted Sharpe and return vs round-4's slow_entry=12 — but Upβ is
  still −0.113 (negative). DSR −0.75. The "less overshoot" hypothesis failed on Upβ but
  the faster band is a better risk-adjusted *short-leaning* book.
- **Best downside protection *with* positive upside (round-3 champion still stands):**
  **EW-MA-Short** — both-down −12.97%, Dn-corr 0.224, Upβ **0.013 (positive)**, Sharpe
  0.613. The hysteretic family beat it on downside protection but threw away the upside
  to do it; if the upside floor matters, EW-MA-Short remains the pick.
- **Best return (beats AW, but no asymmetry):** **RP winner (MinVar)** — 9.29% / Sharpe
  0.921, Dnβ 0.585 > Upβ 0.432. Unchanged (long-only risk parity).
- **Avoid:** **EW-AsymVol-Short** (−1.16%, Dnβ 0.284 >> Upβ 0.024 — vol hysteresis shorts
  the rebound), **EW-DDStop-Short** (lagging triggers), and the round-3 laggards.

*Research / illustration only. Not investment advice.*