# Handoff — Stock_Price

## Goal
Download all ticker data as far back as Yahoo Finance provides, at the highest
granularity available (daily + monthly).

## Documentation
Full system docs live in `docs/` — start at `docs/README.md`:
- `docs/data_dictionary.md` — every output file, field-by-field
- `docs/coverage.md` — date ranges, per-ticker/asset-class/sector coverage
- `docs/methodology.md` — how values are derived (adjustment, returns, aggregation)
- `docs/nuances_and_caveats.md` — data quirks + integrity-audit triage
- `docs/scripts_reference.md` — the 3 scripts, config, reproducibility
Root `README.md` is the entry point.

## Current state (2026-07-17)
- Branch: `feat/expand-universe-daily-download` (commit 330ab25), **not yet pushed / no PR**.

## Risk-parity peer-review round (2026-07-20, this branch)
A critical peer review of `risk_parity_eval.py` was written to `docs/peer-review.md`
and four methodology fixes were implemented and committed on this branch
(`3c173af`..`c12400e`):

- **Fix 1** (`3c173af`) — per-sleeve cap enforced **inside** the MinVar/ERC solver via
  exact capped-simplex projection (`project_capped_simplex`), not post-hoc clip.
- **Fix 2** (`c9ebe73`) — both-down regime + equity-correlation metric decoupled to
  **external SPY/AGG** (`--ref-mode external`, default); `--ref-mode sleeves` is the
  legacy regression guard.
- **Fix 3 + Fix 4 + cap-integrity refinement** (`23e4471`) — **LS-TSMOM** managed-futures
  scheme folded into the canonical pipeline (TRAIN/TEST/rolling, DSR, bootstrap CIs,
  §9 head-to-head); DSR **effective-N** diagnostic + caveat block; and a numerical
  refinement to Fix 1's projection (residual correction onto interior coords + drop the
  `w/w.sum()` renorm that broke the cap) — verified 0 cap-overshoot, |sum-1|~3e-16.
- **Peer-review doc** (`827a4d6`), **README + .gitignore** (`c12400e`).

Canonical report regenerated: `output/risk_parity_eval/report_eval.md` (NOT tracked —
regenerable with `.venv/bin/python risk_parity_eval.py`). Headline measured answer to
the brief ("a flavor that does well where All-Weather is weak"): the **MinVar** risk-parity
winner (OOS Sharpe 1.518, both-down −11.42%, MaxDD −5.61%, cap 20.00% = exact) **dampens**
the AW weak spot but doesn't flip it positive; **LS-TSMOM** (Sharpe 0.347, both-down
−4.82% — smallest of the three, equity corr 0.129) is the right *direction* but its edge
is **not statistically significant** (DSR −0.964, Sharpe CI [−0.482, 1.213], both-down CI
[−10.45%, +3.14%]). Effective N = 1.2 vs nominal 16,902 (DSR is conservative). Both-down
counts (external ref): TRAIN 17 / TEST 24.

**Note:** the cap-integrity refinement shifted ERC weights, which shifted the
TRAIN-selected LS-TSMOM combo and its numbers slightly between runs — the regenerated
report's numbers are authoritative; the `docs/peer-review.md` "Measured outcomes" block
matches them.

## TrendProtect flavor round (2026-07-20, this branch)
Extended `risk_parity_eval.py` to answer the next brief: *find an All-Weather
variant with higher expected return while keeping equity correlation asymmetric
(correlated up, protected down)*. Two commits on this branch (`817ae65`, `85cd3c5`):

- **Four TrendProtect flavors** as presets of one `_backtest_flavor` engine, each a
  long MinVar base leg plus overlays: **TrendGate** (gate equity sleeves to cash when
  trailing-12m < 0, gross ≤1), **RP-LS-Overlay** (+0.30 dollar-neutral LS-TSMOM overlay,
  gross 1.30), **StructShort** (permanent sleeve-level net-short US Treasuries 0.30,
  netting so gross ≤1), **TG-LS-Overlay** (gate + 0.20 LS overlay, gross 1.20).
- **Asymmetric metrics** in `compute_metrics`: `upside_beta`/`downside_beta`/
  `updown_beta_diff`/`downside_corr_eq`/`up_market_ann`/`down_market_ann` (equity
  ref = external SPY). **`--score-mode asymmetric`** = 0.30·Sharpe + 0.20·(upβ−dnβ)
  + 0.20·(−dn_corr) + 0.15·both-down + 0.15·(−maxDD); selection TRAIN-only (guard
  unchanged). **`--lev-rate 0.058`** (5.8% APR) charged monthly on gross>1.
- **Report §10** = ranked comparison menu (4 flavors + AW + MinVar winner + LS-TSMOM)
  with Upβ/Dnβ/Dn-corr/gross/lev cost/DSR/bootstrap CI + per-flavor pros/cons + verdict.
- **`docs/portfolio-flavors.md`** = full 10-flavor catalog (construction, composition,
  parameters, pros/cons, regime wins/loses) + the measured menu.

Canonical asymmetric run: `output/risk_parity_eval_asym/report_eval.md`
(regenerable: `.venv/bin/python risk_parity_eval.py --score-mode asymmetric`).
**Measured verdict (honest):** **no TrendProtect flavor beats All-Weather's 7.37%
net OOS** after the 5.8% leverage cost in this window. The flavors buy a much better
*risk* profile — **TrendGate** leads on Sharpe (1.385 vs AW 1.055), MaxDD (−4.20% vs
−12.31%), both-down (−4.50% vs −18.74%) — at ~3%/yr of return. The asymmetric goal is
**only weakly met**: the gate keeps Upβ and Dnβ **both low** (gate mostly flats
equity → combos run bond/gold/commodity-heavy) and Dnβ slightly **exceeds** Upβ
(the documented 12m lag works *against* the asymmetric shape). LS-TSMOM is the only
Upβ<0 flavor but DSR −1.22 (insignificant). Regression guard (default score,
COV-only): canonical numbers byte-identical (MinVar 1.518/−11.42%/−5.61; AW
1.055/−18.74%); new code paths are opt-in.

**Honest caveats:** StructShort = sleeve-level netting (gross ≤1, no lev cost) —
ticker-level shorting that *adds* gross is a flagged refinement, not implemented.
Trend-gate lag is a construction property, not a bug. One TRAIN/TEST split = one
regime; flavors share sleeves → DSR conservative (effective N ≪ nominal); trust the
bootstrap CI.

## TrendProtect round 2 — gate_mode=short / EW-base / asymmetric2 (2026-07-20)
Round 1's measured negative result (no flavor beat 7.37% with the asymmetric property)
diagnosed three causes: (a) the **cash-gate can't produce negative Dnβ** (it only flats
equity); (b) the **MinVar base starves equity** to ~5-10% weight → little upside to
capture and little to short; (c) the **`asymmetric` score flees equity** (the `upβ−dnβ`
term rewards a combo low in *both*). Round 2 fixes all three (uncommitted in working
tree — `risk_parity_eval.py` + `docs/portfolio-flavors.md` updated):

- **`gate_mode="short"`** — on the downside signal, *flip* the equity sleeve to net-short
  (`pos *= sign(trailing-lookback)` for equity sleeves) instead of flat. The direct lever
  for negative downside-β the brief's "long-term short a ticker" permission enables.
- **`base_mode="ew"`** — equal-weight base leg (like AW's own ~1/n) so equity keeps a real
  weight (~12-25%) — fixes the MinVar-base equity starvation.
- **`--score-mode asymmetric2`** — `0.30·pct(ann_return_net) + 0.20·pct(upside_beta)
  + 0.15·pct(−downside_beta) + 0.10·pct(−downside_corr_eq) + 0.15·pct(Sharpe)
  + 0.10·pct(−maxDD)` — rewards a high Upβ (real equity weight) AND a high net return,
  so the search keeps equity in the book instead of fleeing to diversifiers.
- **Six new flavors:** TG-Short, TG-Short-LS, TG-Short-6m (MinVar base) + EW-Short,
  EW-Short-LS, EW-Short-6m (EW base). Plus `lookback=6` per-preset override for less lag.
- **`sc` DataFrame fix:** added `ann_return_net` column to the TEST `sc` DataFrame in
  `main()` (the asymmetric2 score needs it; default/asymmetric paths unaffected).

**Canonical run:** `output/risk_parity_eval_asym2b/report_eval.md` (regenerable:
`.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --schemes
EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,
EW-Short-LS,EW-Short-6m --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir
output/risk_parity_eval_asym2b`). 36621 TRAIN trials, 13 schemes.

**Measured verdict (round 2, honest) — two findings, one per half of the brief:**
1. **One flavor beats AW's 7.37% net OOS return: the RP winner (MinVar) at 9.29%** — but
   it is plain long-only risk parity with **no** asymmetry (Dnβ 0.585 > Upβ 0.432, Dn-corr
   0.747 ≈ AW). Dropping the asymmetry constraint, return is beatable; keeping it, it is
   not (in this window).
2. **No flavor beats 7.37% *with* the asymmetric property.** In **every** flavor Dnβ ≥
   Upβ. The `gate_mode=short` lever does buy **real downside-correlation reduction**
   (TG-Short-LS Dn-corr 0.199, TG-Short 0.366 vs AW 0.793) — partial progress on
   "protected down" — but at the cost of return (3-5%) AND upside capture (Upβ also
   crushed to 0.06-0.13). The EW-Short family (real equity + short-on-downside) was the
   strongest direct test and **whipsawed to 0.37-3.14%** — the lagged short sells the
   bottom of 2018 / the 2020 COVID rebound. Every flavor's DSR is negative (edge not
   significant).

**Structural blocker (consistent across both rounds):** trailing 12m/6m momentum is
*lagging* — long into drawdown starts (eats the downside), short/flat into rally starts
(misses the upside) → Dnβ ≥ Upβ everywhere. Beating AW on return while keeping the
asymmetric shape needs a **leading/faster downside signal** (MA crossover, regime filter,
equity-below-10m-MA) that exits equity *before* the drawdown and re-enters *before* the
rally — not more TSMOM lookback tuning (that is overfitting). This is the untested lever
for round 3.

## TrendProtect round 3 — leading-signal gate family (2026-07-20)
Round 2's blocker was diagnosed as a *lagging* signal, not a bad construction. Round 3
(commit `82823b9`) swaps the equity-gate signal for three **leading** downside signals via
a new `gate_signal` knob on `_backtest_flavor` (`"tsmom"`|`"ma"`|`"vol"`|`"dma"`). All
three new presets are EW-base + `gate_mode=short` so equity keeps a real weight AND flips
to net-short on the downside signal:

- **EW-MA-Short** (`gate_signal="ma"`, lookback 10) — price vs 10m SMA crossover.
- **EW-Vol-Short** (`gate_signal="vol"`, 6m realized vol vs its 60m median) — a regime filter.
- **EW-DMA-Short** (`gate_signal="dma"`, fast 3m vs slow 10m SMA) — a smoother crossover.

New `_gate_signal()` helper computes the per-sleeve +/-1/0 gate direction; the existing
`tsmom` gate path is kept **byte-identical** (the gate block branches on `gate_signal`,
defaulting to the inline `mom`-based path), so round-1/2 presets are unchanged. The
leading-signal family needs a longer pre-window (vol uses a 60m median of a 6m realized
vol → ~66m), so the engine pulls `max(lookback, 72)` months of pre-window history.

**Regression guard (default canonical, 6 base schemes, external ref):** §4 byte-identical
to the anchor (MinVar 1.518/−11.42%/−5.61%, AW 7.37%/1.055/−18.74%) — round-3 edits are
opt-in.

**Canonical run:** `output/risk_parity_eval_asym3/report_eval.md` (regenerable:
`.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --schemes
EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,
EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short --rolling-schemes
EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym3`). 45072 TRAIN
trials, 16 schemes.

**Measured verdict (round 3, honest) — the leading-signal hypothesis is PARTIALLY
confirmed, and it isolates the fundamental tension:**
1. **The round-2 downside blocker IS fixed — by EW-MA-Short.** MA crossover achieves the
   **best downside protection in the entire 10-flavor family**: both-down **−11.24%** (vs
   AW −18.74%, vs lagging-TSMOM EW-Short family −18.97% to −20.18%) and Dn-corr **0.259**
   (vs AW 0.793 — the lowest of any flavor, beating round-2 TG-Short-LS 0.347). The MA gate
   exits equity *before* the drawdown. Real, measured progress on "protected down"; confirms
   the round-2 diagnosis.
2. **BUT it trades "miss less downside" for "miss more upside."** Upβ collapsed to **0.014**
   (vs TrendGate 0.265, AW 0.327) — the MA gate exits before rallies too. The shape
   **inverts**: round 2 = "correlated up but NOT protected down"; round 3's EW-MA-Short =
   "protected down but NOT correlated up." Return 4.08% < AW 7.37%. The other two leading
   signals are worse: **EW-Vol-Short** whipsawed to **−1.52%** / MaxDD −31.69% (vol stays
   elevated through the 2020 COVID V-rebound → shorts the bottom); **EW-DMA-Short** was
   mediocre (2.02%).
3. **Still no flavor beats 7.37% *with* the asymmetric property.** Across all three rounds
   (16 flavors), **Dnβ ≥ Upβ in every single one.** RP winner (9.29%) beats on return but
   with the *most* downside correlation. Every flavor's DSR is negative.

**Fundamental tension (the real round-3 finding):** "correlated up, protected down" needs
an **asymmetric signal** — trigger-happy on the downside (exits equity) but relaxed on the
upside (stays long through chop). A **symmetric** price filter (MA / TSMOM / dual-MA /
vol-regime) is equally trigger-happy in both directions: any signal that exits before a
drawdown also exits before *some* rallies. So a symmetric gate can optimize *either* the
downside half (EW-MA-Short) or the upside half (TrendGate/MinVar), not both. **Round 4
lever:** a directionally-asymmetric gate — a fast downside-only trigger (exit on a sharp
drop / vol spike) paired with a slow-or-no upside trigger (stay long through chop), or a
defined-downside insurance overlay (put spreads / trend-downside-stop) that does not cap
the upside. Not yet implemented.

Docs: `docs/portfolio-flavors.md` updated — §3c (three new flavors + `gate_signal` knob) +
§5b (round-3 measured menu + verdict + top picks) + round-3 reproduction command.

## TrendProtect round 4 — asymmetric (hysteretic) gate family (2026-07-20)
Round 3 isolated the fundamental tension: a **symmetric** gate is equally trigger-happy up
and down, so it can optimize *either* the downside half (EW-MA-Short) or the upside half
(TrendGate), never both — Dnβ ≥ Upβ in all 16 prior flavors. Round 4 implements the
round-3 prescription: a **directionally-asymmetric (hysteretic)** gate — fast downside
exit, slow upside re-entry — the direct test of "correlated up, protected down." Two new
`gate_signal` values in `_gate_signal()` (`risk_parity_eval.py`), each a stateful per-sleeve
flip-flop starting LONG:

- **`asym_ma`** (EW-AsymMA-Short) — LONG → SHORT when `price < 3m SMA` (fast exit), SHORT →
  LONG when `price > 12m SMA` (slow re-entry). Hysteresis band = the fast/slow-MA gap.
- **`dd_stop`** (EW-DDStop-Short) — LONG → SHORT once drawdown from the 6m peak > 10%,
  SHORT → LONG once within 3% of the peak ("flee the break, wait for a new high").

Both are EW-base + `gate_mode=short` (real equity weight, flips net-short on the downside
state), gross ≤ 1 (sleeve-level netting, no leverage cost). New helper params
(`fast_exit=3, slow_entry=12, dd_window=6, dd_exit=0.10, dd_entry=0.03`) use helper
defaults (the precompute call passes only `(H, lookback, gate_signal)`); pre_n=72 covers
slow_entry=12 and dd_window=6. The `tsmom`/`ma`/`vol`/`dma` paths and the inline gate block
are **byte-identical** — the new branches are behind `if gate_signal == "asym_ma"/"dd_stop"`,
reached only by the two new presets, so the round-3 regression-guard opt-in guarantee
holds. Sanity-tested: both go LONG in an up-trend, SHORT after a crash; `asym_ma` re-enters
slower (t=42) than `dd_stop` (t=39) — confirms the slow-reentry asymmetry; both causal
(only `lvl[t-1]` and trailing windows).

**Regression guard (default score, external ref, 6 base schemes, with round-4 code):**
`output/rp_reg4c/report_eval.md` — §4 byte-identical to the anchor
`output/rp_reg4/report_eval.md` (verifies opt-in).

**Canonical run:** `output/risk_parity_eval_asym4/report_eval.md` (regenerable:
`.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --schemes
EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,
EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short
--rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym4`).
50706 TRAIN trials, 18 schemes.

**Measured verdict (round 4, honest) — the asymmetry bought a first, but the property is
still not met:**
1. **EW-AsymMA-Short is the FIRST flavor in the entire 18-flavor family (4 rounds) to drive
   Dnβ negative (−0.049) and Dn-corr negative (−0.060).** The hysteretic gate genuinely
   flips the equity sleeve net-short *against* equities on down months — real downside
   protection no symmetric gate achieved (round-3 best EW-MA-Short was Dnβ +0.125). The
   round-3 prescription (an asymmetric signal is the lever) is **confirmed**.
2. **BUT the slow re-entry overshoots — Upβ also went negative (−0.124).** Staying short
   until price reclaims the 12m SMA means the sleeve is still short through the *start* of
   rallies (the V-rebound), so it misses the upside it was supposed to capture. Net shape:
   "negatively correlated *always*" (a short-leaning book), not "correlated up, protected
   down." Upβ (−0.124) < Dnβ (−0.049) — **Upβ > Dnβ is still not achieved.** Return 3.43% <
   AW 7.37%; DSR −0.90.
3. **EW-DDStop-Short failed outright** — Dnβ 0.536 >> Upβ 0.106. A drawdown-percentage stop
   is itself *lagging* (price has already fallen), and re-entering on a "new 6m high"
   *lags* a V-rebound — hysteresis built on two lagging triggers does not produce the
   asymmetry. MaxDD −24.01%, DSR −1.01. Confirms a *leading* fast-exit is necessary.
4. **No flavor beats 7.37% with the asymmetric property.** Across all four rounds (18
   flavors), **Dnβ ≥ Upβ in every single one.** RP winner (9.29%) beats on return with the
   *most* downside correlation. Every flavor's DSR is negative.

**The round-4 finding:** the family has now spanned the full space — round 2 = "correlated
up, NOT protected down"; round 3 = "protected down, NOT correlated up"; round 4 =
"negatively correlated both ways." A single price-gate in one TRAIN/TEST split cannot
satisfy both halves: the slow re-entry that protects the downside *also* suppresses the
upside. The remaining lever is to **decouple the two halves entirely** — keep a long-only
base for the upside (so Upβ stays positive) and add a **defined-downside insurance overlay**
(put spread / explicit downside-stop on a *separate* notional) that caps the downside
*without* flipping the long book short. That is the construction the brief's "long-term
short a ticker" permission hints at, as an overlay not a gate. Not yet implemented.

Docs: `docs/portfolio-flavors.md` updated — §3d (two new hysteretic flavors + `gate_signal`
knob extended) + §5c (round-4 measured menu + verdict + top picks) + round-4 reproduction
command + intro ("four rounds").

## TrendProtect round 4b — hysteretic-gate parameter sweep (2026-07-20)
Round 4's EW-AsymMA-Short drove Dnβ negative (good) but Upβ also negative (the slow 12m
re-entry was *hypothesized* to overshoot the rally). The user directed: **widen the search
before committing to the decoupled-overlay construction** — run a parameter sweep (tune
the hysteresis band, or test an asymmetric vol-gate) to check whether a less-overshooting
hysteretic gate can keep Upβ positive while Dnβ stays negative. Round 4b is that sweep.

Four new presets in `FLAVOR_PRESETS` (`risk_parity_eval.py`), all EW-base + `gate_mode=short`,
gross ≤ 1, no leverage cost:

- **EW-AsymMA-Short-6 / -9** — same `asym_ma` gate, faster re-entry `slow_entry` ∈ {6, 9}
  (vs round-4's 12), `fast_exit=3`. The "less overshoot" hypothesis: a faster re-entry
  re-enters long earlier in a rally → Upβ should recover toward positive.
- **EW-AsymMA-Tight** — `fast_exit=2, slow_entry=6` (tightest band) — the most aggressive
  fast-exit / fastest re-entry.
- **EW-AsymVol-Short** — new `gate_signal="asym_vol"` (a hysteretic *vol* gate): LONG → SHORT
  when `vol > 1.0× trailing-60m median vol` (fast exit on a vol spike); SHORT → LONG when
  `vol < 0.85× median` (slow re-entry — vol must genuinely calm *below* a lower bar). Fixes
  the round-3 EW-Vol-Short, which shorted the 2020 COVID V-rebound because vol stayed
  elevated through the rally (a symmetric vol-gate never re-entered long).

Implementation: `_gate_signal()` gains an `asym_vol` branch (hysteretic vol-regime flip-flop,
state starts LONG) + 4 new kwargs (`vol_window=6, vol_median=60, vol_hi_mult=1.0,
vol_lo_mult=0.85`). `_backtest_flavor` threads the per-preset kwargs
(`g_vol_window, g_vol_median, g_vol_hi, g_vol_lo` and the asym_ma `fast_exit/slow_entry`
override) into the precompute call. **Opt-in verified via rolling-selection byte-identity:**
round 4 vs round 4b, all 9 TEST years 2018-2026 identical (the new branches are behind
`gate_signal` values only the new presets use; existing presets use helper defaults →
byte-identical). No extra regression-guard run needed (rolling selection re-uses the same
`--rolling-schemes EW,MinVar,LS-TSMOM` → MinVar dominates, identical to round 4).

**Canonical run:** `output/risk_parity_eval_asym4b/report_eval.md` (regenerable:
`.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --schemes
EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,
EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,
EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short
--rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym4b`).
61974 TRAIN trials, 22 schemes.

**Measured verdict (round 4b, honest) — the "less overshoot" hypothesis is DISCONFIRMED;
the sweep rules out the re-entry-lag explanation and isolates the structural blocker:**
1. **Faster re-entry did NOT restore Upβ.** Across the whole `asym_ma` family Upβ is pinned
   at ≈ −0.11 regardless of `slow_entry` (−0.124 at 12, −0.113 at 9, −0.113 at 6, −0.111
   tight). Re-entering at 6m doesn't help. So the negative Upβ is **not** a re-entry-lag
   tunable; it is **structural** to `gate_mode=short`: once the gate flips the equity sleeve
   short after any break, that sleeve is short through the early part of recoveries, and
   the EW base's other sleeves (bonds/gold/commodities) don't track equity up-moves — so
   the portfolio's up-month beta is dominated by the (short) equity sleeve and goes
   negative. You cannot fix it by tuning the band.
2. **The downside protection IS robust to the band — Dnβ stays negative.** Every `asym_ma`
   variant holds Dnβ ≤ −0.03 (−0.049, −0.041, −0.026, −0.111) with negative Dn-corr — the
   round-4 finding is robust, not a parameter fluke. **EW-AsymMA-Tight** hits both-down
   **−8.79%** (the best of *any* flavor across all rounds — beats round-3 EW-MA-Short's
   −12.97%) and Dn-corr **−0.254** (most negative of all), Sharpe 0.412 — but Upβ collapses
   to **exactly** Dnβ (−0.111 = −0.111): the asymmetry *vanished* (both negative). The
   tighter the band, the more *symmetric* (both negative), not the more asymmetric.
3. **EW-AsymVol-Short failed** — Sharpe −0.161, Dnβ 0.284 >> Upβ 0.024. Vol hysteresis did
   NOT fix the V-rebound: vol calms late (through rallies), so even the slow 0.85×-median
   re-entry re-enters after the rally's best months, and the gate shorts the rebound. A
   vol-regime gate is the wrong information set for "correlated up, protected down" (vol is
   a *coincident* stress indicator, not a leading one).
4. **No flavor beats 7.37% with the asymmetric property.** Across all four rounds (22
   flavors), **Dnβ ≥ Upβ in every single one** where the betas differ; the Upβ = Dnβ cases
   (EW-AsymMA-Tight, both −0.111) are *symmetric* (both negative), not asymmetric. RP
   winner (9.29%) beats on return with the most downside correlation. Every flavor's DSR
   is negative.

**The round-4b finding (what the sweep settled):** the negative-Dnβ / negative-Upβ coupling
is **structural to shorting equity on a downside gate**, not a tunable lag. The hysteresis
grid is now spanned (slow_entry {6,9,12} × fast_exit {2,3} + a vol-regime gate), and no band
produces Upβ > Dnβ. This confirms the round-4 lever is the only remaining one: **decouple
the two halves entirely** — keep a *long-only* base for the upside (so Upβ stays positive)
and add a **defined-downside insurance overlay** (put spread / explicit downside-stop on a
*separate* notional) that caps the downside *without* flipping the long book short. The
brief's "long-term short a ticker" permission points at exactly this, as an overlay not a
gate. **Round 5 = the decoupled insurance overlay.**

Docs: `docs/portfolio-flavors.md` updated — intro ("five rounds"), §3e (the hysteretic-gate
sweep construction: the slow_entry {6,9} grid, EW-AsymMA-Tight, the asym_vol construction),
§5d (round-4b measured menu + verdict + top picks), round-4b reproduction command, canonical-
reports list.

## TrendProtect round 5 — decoupled insurance overlay (2026-07-20)
Round 4b settled that shorting equity through a single price-gate is structural to killing
Upβ (the gate flips the long book short through recoveries). Round 5 implements the lever
4b identified: **decouple the two halves** — a *long-only base that never flips* (stays at
`base_w` every month → Upβ inherits the long base's positive equity beta) plus a
**separate additive short overlay** on the equity sleeves that fires ONLY on a downside
signal and is flat otherwise. The brief's "long-term short a ticker" permission, applied as
an overlay (not a gate) on a separate notional.

Five new presets in `FLAVOR_PRESETS` (`risk_parity_eval.py`), all EW-base +
`gate_mode="overlay"`, sweeping the overlay size and downside signal:

- **EW-Hedge-DMA-1 / -DMA / -DMA-2** — `w_hedge` ∈ {1.0, 1.5, 2.0}, `gate_signal="dma"`
  (symmetric 12m dual-MA — fast-OFF in recoveries, unlike `asym_ma`).
- **EW-Hedge-MA** — `w_hedge=1.5`, `gate_signal="ma"` (symmetric 12m MA).
- **EW-Hedge-DD** — `w_hedge=1.5`, `gate_signal="dd_stop"` (drawdown stop).

Implementation: `_backtest_flavor` gains a `w_hedge` param (0 default) and a
`gate_mode="overlay"` branch. The long base NEVER flips (stays `base_w`); the overlay
`ol[eq] = -w_hedge * base_w[eq]` activates only on `is_eq & (gd < 0)`, flat otherwise.
`pos_target = long_leg + ol`; **gross is ADDITIVE** (`|long_leg|.sum() + |ol|.sum()`, not
sleeve-netted) → leverage cost charged on the excess gross every month the overlay fires.
`w_hedge > 1` ⇒ net-short equity in down-months. **Opt-in verified two ways:** (1) regression
guard — `output/rp_reg5/report_eval.md` §1–4 byte-identical to the round-4b anchor
`output/risk_parity_eval_asym4b/report_eval.md` (`diff` clean); (2) rolling selection
2018–2026 byte-identical. Existing presets use `w_hedge=0` and `gate_mode` ∈ {cash, short}
→ `ol` stays zeros, gross uses netted `|pos_target|.sum()` → byte-identical to round 4b.

**Canonical run:** `output/risk_parity_eval_asym5/report_eval.md` (regenerable:
`.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 --schemes
EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,
EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,
EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short,EW-Hedge-DMA-1,EW-Hedge-DMA,
EW-Hedge-DMA-2,EW-Hedge-MA,EW-Hedge-DD
--rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym5`).
76059 TRAIN trials, 27 schemes. (Note: adding 5 schemes shifts the percentile-ranked
asymmetric2 score → TRAIN-selected combos differ from round 4b for shared schemes; this is
the documented relative-score nuance, not a regression.)

**Measured verdict (round 5, honest) — the overlay FIXED the upside half but FAILED the
downside half; the brief's property is still not met, now for the opposite reason:**
1. **Upβ is now POSITIVE (0.015–0.240) across all five EW-Hedge presets** — the round-4b
   structural blocker (Upβ stuck at −0.11) is genuinely resolved by the never-flipping
   long base. This is the construction's first-order win.
2. **Dnβ stayed strongly POSITIVE (0.362–0.586), and Dnβ ≫ Upβ in every preset.** The
   property Upβ > Dnβ is **still not met** — now because Dnβ won't come down (round 4b was
   the opposite: Upβ driven negative). An equity-only additive short offsets only the
   equity sleeve's downside; it does NOT offset bonds/gold/commodities, which ALSO fall in
   both-down (stagflation) months. And the `dma`/`ma` downside signal fires too late
   (whipsaw/lag — turns on after the drop), so the months that need hedging are hedged
   late or not at all.
3. **Both-down is WORSE (−20% to −28%) than the round-4b hysteretic family**
   (EW-AsymMA-Tight −10.91%, EW-MA-Short −12.97%). The overlay adds gross → leverage cost
   and whipsaws, but — firing only on equity and only when the lagging signal agrees — it
   buys less downside dampening than it costs in the both-down regime that dominates the
   worst months.
4. **No EW-Hedge preset beats 7.37%/1.055** (best EW-Hedge-MA 3.60%/0.463); every DSR is
   negative (−0.85 to −1.10) with Sharpe-CI lower bounds below zero. Best of family:
   **EW-Hedge-MA** (Sharpe 0.463, Upβ 0.127). Highest Upβ: **EW-Hedge-DMA-1** (0.240).
   The "protected down" champion is STILL a round-4b flavor (EW-AsymMA-Tight / EW-MA-Short),
   not a round-5 one.

**Reporting caveat:** the §10 `Gross` / `Lev cost/yr` columns report the LAST TEST month's
netted `|last_w|.sum()` (and `(that−1)·5.8%`), not the average additive gross — so they
under-report the overlay flavors' leverage cost (which IS charged in net every month it
fires, additive gross at line 980). EW-Hedge-MA's gross 0.90 = overlay net-short equity in
the final month. A future run should report the *average* additive gross / annualized lev
cost for overlay flavors for honesty.

**The round-5 finding (what it settled):** the decoupled overlay is the right *construction*
(Upβ is positive by construction now — round 4b's blocker is gone) but an **equity-only**
downside overlay is the wrong *instrument* — it cannot protect both-down (stagflation)
months where bonds/duration fall with equities, and a slow `dma`/`ma` gate fires too late.
**Round 6 = extend the overlay to short the both-down sleeves (bonds / duration — the
brief's "short a ticker" = short TLT / long-duration as a conditional overlay that fires on
the same downside signal), not equity alone**, and/or use a downside signal that reliably
activates IN equity-down months (a fast equity-drawdown trigger, not the sleeve's own
lagging trend). Shorting duration in both-down is the direct mechanical fix for the
"bonds fall with equities" gap that keeps Dnβ positive.

Docs: `docs/portfolio-flavors.md` updated — intro ("six rounds"), §3f (the decoupled-overlay
construction: the never-flip base, the additive short overlay, the up/down-month
pseudocode, the five presets), §5e (round-5 measured menu + verdict + top picks + the
reporting caveat + the round-6 lever), round-5 reproduction command, canonical-reports list.

## TrendProtect round 6 — duration/bond overlay + fast eq_dd drawdown trigger (2026-07-20)

User directive (verbatim): *"Let's test short duration/TLT in the overlay + a fast
equity-drawdown trigger — the mechanical fix for the 'bonds fall with equities' gap that
keeps Dnβ positive."* Built BOTH levers from the round-5 "next lever" note, in one
parameterized engine (opt-in, defaults preserve existing presets byte-identical).

**Code (`risk_parity_eval.py`, working tree):**
- New `gate_signal="eq_dd"` branch in `_gate_signal` — a symmetric, stateless fast
  drawdown trigger: short a sleeve once it is > `dd_exit` (10%) below its trailing
  `dd_window` (6m) peak; long once back within `dd_entry` (3%) of the peak. Fires FAST in
  down-months, releases FAST in recoveries (no lag-through-recovery Upβ drag).
- New `w_hedge_bd` param + `bonds` param threaded through `backtest` → `_backtest_flavor`
  → `fast_search` → `rolling_full_select` → call sites. In `gate_mode=="overlay"`, after
  the equity short, add a **duration/bond overlay**: `ol[bond] += -w_hedge_bd·base_w[bond]`
  on `is_bond & (gd<0)` — short the bond sleeves on their OWN downside signal
  (self-avoiding flight-to-quality: bonds up → no short; bonds down/stagflation → fires).
- Gross additively includes both overlays: `|long_leg|.sum() + |ol|.sum()` when
  `w_hedge>0 or w_hedge_bd>0`. Default `w_hedge_bd=0` → existing presets unchanged.
- 5 round-6 presets in FLAVOR_PRESETS (EW-Hedge-Dur / -Dur-MA / -Dur-DD / -Dur-2 /
  -Dur-DD2) — `dma`/`ma`/`eq_dd` gate signals × `w_hedge_bd` {1.5, 2.0}; added to SCHEME_ORDER
  and to the `pc` pros/cons dict. `py_compile` + `import risk_parity_eval` OK.

**Opt-in regression guard (verified):** `output/rp_reg6/report_eval.md` (22-scheme round-4b
anchor set + round-6 code) §1–4 byte-identical to `output/risk_parity_eval_asym4b/report_eval.md`
— the new code paths are genuinely opt-in; existing presets are unaffected.

**Canonical run:** `output/risk_parity_eval_asym6/report_eval.md` (32 schemes, 90 144 TRAIN
trials, exit 0).

**Measured verdict (round 6, honest) — the duration overlay did its mechanical job on
both-down but could NOT flip Upβ > Dnβ.** Five EW-Hedge-Dur presets, all Dnβ > Upβ:
- EW-Hedge-Dur (dma): 0.26%/0.030, both-down -14.07%, Upβ -0.024/Dnβ 0.399/Dn-corr 0.430, DSR -1.28.
- **EW-Hedge-Dur-MA (ma): 2.28%/0.296, both-down -12.10% (BEATS AW's -18.74% and round-5's
  -20.17%), Upβ -0.025/Dnβ 0.243/Dn-corr 0.334, DSR -1.02** — duration overlay hedged
  stagflation as designed (best both-down of all 32 flavors), but drove Upβ NEGATIVE.
- EW-Hedge-Dur-2 (dma, bd2.0): -0.35%/-0.040, both-down -12.73%, Upβ -0.060, DSR -1.35 —
  bigger duration hedge → negative net return.
- **EW-Hedge-Dur-DD (eq_dd): 3.29%/0.345, both-down -26.31% (WORSE than AW), Upβ 0.146
  (positive — fast trigger preserved upside)/Dnβ 0.559, DSR -0.97** — fast trigger kept
  Upβ but its 10% bond-drawdown threshold rarely fires for bonds → duration leg quiet →
  Dnβ stayed high; whipsaw made both-down worse.
- EW-Hedge-Dur-DD2 (eq_dd, bd2.0): 3.02%/0.315, both-down -25.75%, Upβ 0.126/Dnβ 0.542, DSR -1.00.

Two failure modes (one per gate): (1) lagging `dma`/`ma` duration short → both-down
better but Upβ dragged negative through recoveries (round-4b failure recurs on duration
leg); (2) fast `eq_dd` → Upβ kept but threshold too high to fire the bond hedge → Dnβ
unmoved + whipsaw cost → both-down worse. No round-6 flavor beats 7.37%; all DSR negative;
no CI excludes zero.

**Cross-investigation result: ALL 32 flavors (six rounds) have Upβ < Dnβ.** The property
is met by zero. The structural reason: "correlated up, not down" needs a downside hedge
with effectively PERFECT timing — fire only in down-months, never in up-months — and no
causal sleeve-level signal on this universe provides it (lagging → drags Upβ; fast →
doesn't fire the hedge). The remaining lever is a LEADING (macro/regime: yield-curve /
real-rate / carry) gate that fires before the equity drawdown, or holding a genuinely
short-duration ticker (short TLT) only inside an ex-ante stagflation regime.

Docs: `docs/portfolio-flavors.md` updated — intro (round-6 sentence), §3g (the duration
overlay + eq_dd construction + 5-preset table + opt-in note), round-6 reproduction command,
canonical-reports list (asym6), §5f (round-6 measured menu + verdict + top picks), and
§0 updated to six rounds / 32 flavors / "all 32 have Upβ < Dnβ" / round-6 row in the
winners table / "lever WAS tested in round 6 and also failed."

## INVESTIGATION CLOSED — final honest conclusion (2026-07-20, after round 6)
After six rounds / 32 TrendProtect flavors, **the brief's property was not achieved**:
no flavor both beats All-Weather's 7.37% / Sharpe 1.055 net OOS AND has Upβ > Dnβ — in
fact ALL 32 flavors have Upβ < Dnβ. Three structural blockers, one per failure mode:
rounds 2-4b shorting equity on a downside gate drives Upβ negative (structural, not
tunable); round 5 decoupling fixes Upβ but an equity-only overlay can't bring Dnβ down
(bonds/duration fall WITH equities in both-down, dma/ma gate fires too late); round 6
shorting duration in the overlay fixes the both-down regime but trades Upβ for it
(lagging duration short drags Upβ negative) while the fast eq_dd trigger keeps Upβ but
its threshold rarely fires the bond hedge so Dnβ stays high. User originally chose "stop
and document" after round 5, then directed round 6 to be run; round 6 was run and also
failed to meet the property.

The synthesized bottom line is **§0 of `docs/portfolio-flavors.md`** ("Bottom line — the
honest conclusion across all six rounds"): the three structural blockers, a "what actually
won by objective" table (AW / RP winner / EW-Hedge-Dur-MA / EW-MA-Short / EW-Hedge-MA /
EW-Hedge-Dur-DD), the statistical-honesty caveat (every DSR negative, one TRAIN/TEST split),
and the remaining lever (a LEADING macro/regime downside signal or a short-duration ticker
held only in an ex-ante stagflation regime) recorded as the single most likely next step.

**Measured practical picks (OOS 2018-2026, NOT statistically significant):**
- Best risk-adjusted long-only benchmark: All-Weather 7.37% / 1.055 (nothing beat its Sharpe).
- Beats AW on return, no asymmetry: RP winner (MinVar) 9.94% / 0.945 (Dnβ 0.619 > Upβ 0.406).
- Best downside protection of all 32: EW-Hedge-Dur-MA (round 6), both-down -12.10%, Dn-corr
  0.334 — but Upβ -0.025 (negative); the duration overlay won the regime at the cost of Upβ.
- Best balance (positive Upβ + downside < AW): EW-MA-Short 4.25% / 0.613, Upβ 0.013,
  both-down -12.97%, Dn-corr 0.224 — STILL the closest any flavor came to the brief across
  all six rounds (no round 5 or 6 preset dethroned it).
- Round-5 best (Upβ fixed by construction): EW-Hedge-MA 3.60% / 0.463, Upβ 0.127, Dnβ 0.362.
- Round-6 best (fast trigger kept Upβ): EW-Hedge-Dur-DD 3.29% / 0.345, Upβ 0.146, Dnβ 0.559.

## Next steps (open) — risk parity
- A proper OOS multiple-comparison test (Holm/Bonferroni over effective-N, or DSR on the
  TRAIN max) — currently only disclosed, not implemented.
- LS-TSMOM vol-scaling (currently equal-weight base for neutrality) + a real T-bill
  collateral return (currently 0%, conservative — real adds ~1-2%/yr).
- Vol-targeting + leverage + a cash/T-bill sleeve (would let risk parity *scale* risk).
- Regime-conditioned allocation / CVaR / carry overlays.
- Push branch + open PR if desired.
- Universe: **342 tickers** (71 original asset-class + 128 individual stocks + 143 new
  mutual funds/ETFs/crypto from user-provided list). Defined in `pull_returns.py`
  (`ASSET_TICKERS` + `STOCK_SECTORS`).
- **Daily data**: `output/daily_prices.parquet` (+ CSV). 24,753 days, 1927-12-30 →
  2026-07-17, 341 tickers with data (only SPAXX empty — money market, only 1d/5d).
  2.7M data cells. Long returns panel: `daily_returns_by_ticker.parquet` (2.71M rows).
- **Monthly data**: `output/monthly_prices.csv` etc. 775 months, 1962-01 → 2026-07,
  336 tickers. 6 fail monthly `period=max`: PADMX, PAGPX, PIGLX, AUBAX, LOMMX, SPAXX.
  (5 of those DO have daily data — Yahoo quirk; monthly aggregate unavailable.)

## How to reproduce
```bash
.venv/bin/python pull_returns.py   # monthly (refresh all 342)
.venv/bin/python pull_daily.py     # daily  (uses cached parquet if present)
```
Deps: `pip install -r requirements.txt` (needs `pyarrow` for parquet).

## Architecture notes
- `_download_batched()` in `pull_returns.py` is the shared download helper (batch=50,
  3s sleep, `yf.config.network.retries=5`, 60s timeout). `pull_daily.py` imports it.
- `pull_daily.py` caches `output/daily_prices.parquet`; delete it to force re-download.
- Outputs: parquet (efficient, tracked) for daily; CSV for monthly. Large daily CSVs
  (daily_prices.csv 31MB, daily_returns_by_ticker.csv 229MB) are gitignored.

## Known caveats
- 5 tickers have daily but not monthly history (PADMX/PAGPX/PIGLX/AUBAX/LOMMX).
- SPAXX empty for both (money market).
- Broad indices (^GSPC/^DJI/^IXIC/^RUT/^VIX) are price-only (no dividends).
- ^TNX/^FVX/^TYX are yield levels, not prices — kept in prices but returns meaningless.
- 24 user-listed tickers are not on Yahoo at all (delisted): CMR, FPIDX, KBONX, PGBDX,
  PGLIX, PINVX, VAB, VCE, VCN, VDAIX, VDMIX, VEE, VFSVX, VFTSX, VFV, VFWIX, VGV,
  VHDYX, VIU, VMMXX, VSP, VTGMX, VTWSX, VXC.

## Data integrity pass (2026-07-17)
- Audited by `audit_integrity.py` (6 dimensions A-F) → `output/integrity_report.csv`,
  triage written up in `output/integrity_findings.md`.
- **Result: 0 FAIL · 27 PASS · 12 WARN — pipeline verified correct.**
- Pipeline correctness proven (D1/D2/B5/D4): returns exactly equal price pct_change;
  monthly==daily-resampled; SPY total-return (30.8×) > ^GSPC price-only (17.0×).
- All 12 WARN explained (none are bugs):
  - C2 extreme returns: 21 real market events (AAPL 2000, AIG 2008, WMB 2002, ^VIX
    spikes) + 2 ancient unadjusted splits (MCD 1968/1969 — Yahoo source gap, not patched).
  - C3 internal NaN (1,106): 99% in money market (VMRXX/VUSXX 227 each) + yield indices
    (^TNX/^FVX/^TYX) which legitimately lack daily data; rest are 1-2 isolated cells.
  - D3 share-class twin divergences: mutual-fund capital-gains-distribution timing in
    Yahoo source across Investor/Admiral share classes (corr ≥0.99, level ratios stable).
  - B3 gaps: VMRXX (money market, expected).
- No data patched; all findings documented for transparency.

## Next steps (open)
- Push branch + open PR if desired.
- Optionally: remove the 6 always-empty tickers from the universe, or re-pull them
  with explicit start/end dates instead of `period=max`.
- `datetime.utcnow()` deprecation warnings in both scripts (cosmetic).
EOF