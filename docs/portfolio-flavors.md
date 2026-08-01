# Portfolio Flavors — Construction, Composition & Measured Comparison

*Research / illustration only. Not investment advice.*

This catalogs every portfolio "flavor" evaluated in `risk_parity_eval.py`: the six
existing schemes (EW, InvVol, InvVar, ERC, MinVar, LS-TSMOM) plus the **TrendProtect**
flavors added to answer the brief — *find an All-Weather variant with higher expected
return while keeping equity correlation asymmetric (correlated on the way up, low/negative
on the way down)*. The TrendProtect family grew in nine rounds: **round 1** added four
cash-gate / overlay / structural-short flavors; **round 2** added six `gate_mode=short`
flavors (flip equity to net-short on the downside signal — the direct lever for negative
downside-β) and an `asymmetric2` score that rewards upside capture + return instead of
fleeing equity; **round 3** added three **leading-signal** flavors (MA crossover,
vol-regime, dual-MA) to fix round 2's lagging-momentum blocker; **round 4** added two
**directionally-asymmetric (hysteretic)** gates (fast downside exit, slow upside re-entry)
— the round-3 prescription made concrete, and the first flavor in the family to drive Dnβ
negative. **Round 4b** widened that hysteretic-gate search — a `slow_entry` ∈ {6, 9, 12}
grid plus a tighter band and a hysteretic vol-gate — to test whether a less-overshooting
re-entry can keep Upβ positive while Dnβ stays negative (it cannot — disconfirmed). **Round
5** then decoupled the two halves: a *long-only base that never flips* (so Upβ stays
positive) plus a *separate additive short overlay* on the equity sleeves, active only on a
downside signal and flat otherwise — the construction the brief's "long-term short a ticker"
permission points at, applied as an overlay not a gate. **Round 6** extended that overlay to
also *short duration* (the bond sleeves, on their own downside signal — directly hedging the
both-down / stagflation months where bonds fall with equities, which round 5's equity-only
overlay could not touch) and added a *fast symmetric drawdown trigger* (`eq_dd`) that fires
in down-months instead of ~12m after. **Round 7** replaced the lagging sleeve-level trend with
a *leading macro gate*: the overlays fire off an *ex-ante inflation regime* (trailing-12m
Commodities return — a signal external to the combo) — shorting duration (and equity) when
inflation is *rising* (stagflation, 2022) and adding a *long-duration tilt* when inflation
is *falling* (disinflation, 2008/2020, where bonds hedge equity for free) — the lever all six
prior rounds had identified but not built; it achieved Upβ > Dnβ for the first time but at
~0 return. **Round 8** narrowed that gate with a *coincident equity-rolling confirmation*
(fire only when inflation is rising **and** equity is already rolling over) — the round-7
verdict's prescribed lever to keep the asymmetry *with* return; it restored the return
(the first inflation-gate flavor to beat 7.37%) but lost the asymmetry, characterizing the
tension from both ends. **Round 9** changed primitive entirely — instead of timing a
*short*, it **scaled gross** (a long-only base multiplied by a per-month scalar, owning
~1.5× in up-months and ~0.3× in down-months, no short to time) — to construct Upβ > Dnβ
*by design*; it beat 7.37% on return (EW-Scale-Mom6 8.50%) but the lagging scalar signal
was leveraged *into* drawdowns and de-risked *into* rallies, so Dnβ > Upβ in all five
presets — the asymmetry reversed, a sixth structural finding. For each flavor: the construction
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
- **Asymmetric2-score canonical** (round 5, +the five decoupled-overlay flavors):
  [`output/risk_parity_eval_asym5/report_eval.md`](../output/risk_parity_eval_asym5/report_eval.md).
- **Asymmetric2-score canonical** (round 6, +the five duration-overlay / eq_dd flavors):
  [`output/risk_parity_eval_asym6/report_eval.md`](../output/risk_parity_eval_asym6/report_eval.md).
- **Asymmetric2-score canonical** (round 7, +the five inflation-regime leading-gate flavors):
  [`output/risk_parity_eval_asym7/report_eval.md`](../output/risk_parity_eval_asym7/report_eval.md).
- **Asymmetric2-score canonical** (round 8, +the five equity-rolling confirmation-gate flavors):
  [`output/risk_parity_eval_asym8/report_eval.md`](../output/risk_parity_eval_asym8/report_eval.md).
- **Asymmetric2-score canonical** (round 9, +the five regime-scaled-gross flavors):
  [`output/risk_parity_eval_asym9/report_eval.md`](../output/risk_parity_eval_asym9/report_eval.md).

See also the peer review: [`docs/peer-review.md`](peer-review.md).

---


> ## ⚠️ Superseded numbers — read this first (2026-08-01)
>
> Every measured figure below predates the bond-data correction. The
> asset-class aggregates had Treasury **yield levels** averaged into the
> `US Treasuries` return sleeve, which *inverted* it (corr −0.51 against a clean
> rebuild, −289 bps/yr). See `docs/nuances_and_caveats.md` Nuance 2.
>
> All 20 evaluation rounds were regenerated on corrected data. **The regenerated
> reports under `output/` are authoritative; the per-round menus in §5–§5i below
> are kept as the research audit trail, not as current numbers.**
>
> What actually changed, measured: only **All-Weather** moved materially.
>
> | Portfolio | Ann ret | Sharpe | Both-down |
> |---|---|---|---|
> | All-Weather | 7.37% → **6.03%** | 1.055 → **0.774** | −18.74% → **−29.27%** |
> | StructShort | 9.35% → 9.34% | 0.771 → 0.771 | −33.96% → −33.94% |
> | RP winner | 8.43% → 8.43% | 0.609 → 0.609 | −43.12% → −43.09% |
> | EW-MA-Short | 4.25% → 4.24% | 0.613 → 0.613 | −12.97% → −12.95% |
>
> The asymmetry is composition, not a second defect: All-Weather is a *fixed*
> book holding **55% US Treasuries**, while every searched flavor selected combos
> containing **no Treasuries at all**. Only the fixed allocation was exposed.
>
> **Consequence for §0's argument.** §0 is written around All-Weather as the
> smooth baseline every flavor is measured against — "nothing beat its Sharpe".
> That premise no longer holds: **StructShort (0.771) ties All-Weather (0.774)
> while earning 331 bps/yr more**. Read §0's *structural* findings (what each
> lever does, and why upside and downside beta trade off) as still valid, and its
> *ranking* claims as superseded.


## The playbook — which tool for which circumstance

The TrendProtect flavors are a toolkit, not a single portfolio. Each one is built for one
circumstance, and the measured out-of-sample numbers (TRAIN 2008–17, TEST 2018–26, net of
10 bps costs and 5.8% leverage cost where gross > 1) tell you when to reach for it. Pick the
row that matches the regime you expect.

| Circumstance | Tool | Ann ret | Sharpe | Upβ | Dnβ | Both-down | Dn-corr |
|---|---|---:|---:|---:|---:|---:|---:|
| **Stagflation** — stocks+bonds both fall (2022) | **EW-Infl-Both** | −0.17% | −0.015 | 0.437 | 0.316 | **−2.70%** | 0.290 |
| **Asymmetry, widest gap** (stagflation, less defensive) | **EW-Infl-BothL** | 0.21% | 0.016 | 0.523 | 0.422 | −7.27% | 0.318 |
| **Disinflation + growth down** (2008/2020) | **EW-Infl-Dur** | 6.79% | 0.587 | 0.541 | 0.712 | −30.08% | 0.674 |
| **Normal / growth up**, lowest drawdown | **All-Weather** | 6.03% | **0.774** | 0.366 | 0.423 | −29.27% | 0.658 |
| **Best return at All-Weather's Sharpe** | **StructShort** | **9.34%** | **0.771** | 0.528 | 0.716 | −33.94% | 0.734 |
| **Trending up** (momentum leads) | **EW-Scale-Mom6** | 8.48% | 0.608 | 0.426 | 0.652 | −46.46% | 0.594 |
| **Growth up**, want return, accept correlated downside | **RP winner (MinVar)** | 8.43% | 0.609 | 0.624 | 0.937 | −43.09% | 0.762 |
| **Balanced** — upside + downside dampening | **EW-MA-Short** | 4.24% | 0.613 | 0.013 | 0.123 | −12.95% | 0.224 |
| **Fast mechanical drawdown hedge** (short duration) | **EW-Hedge-Dur-MA** | 1.92% | 0.238 | −0.032 | 0.248 | −13.41% | 0.329 |
| **Crisis-alpha / uncorrelated sleeve** | **LS-TSMOM** | 2.69% | 0.250 | −0.274 | 0.336 | −10.40% | 0.308 |

> **†** The RP winner is selected by the same `asymmetric2` relative-percentile score pool
> as the TrendProtect flavors, so its TRAIN-best combo shifts when the pool expands (9.94% /
> 0.945 in the r7 measure, 8.43% / 0.609 in the r8 measure). The MinVar engine on a given
> combo is unchanged — only the argmax over combos moved.

How to read it:

- **EW-Infl-Both** is the defensive hedge — the best both-down of the set (−2.69% vs
  All-Weather's −18.74%) and the only flavor with Upβ > Dnβ. Return ≈ 0, so it is a
  protection sleeve for stagflation / both-down, not a return strategy. **EW-Infl-BothL** is
  the wider-gap, less-defensive sibling.
- **EW-Infl-Dur** adds long duration when inflation is *falling* — bonds hedge equity for
  free in disinflation (2008/2020) and it keeps return near All-Weather.
- **All-Weather** is the smoothest ride; nothing beat its Sharpe. Reach for the others when
  you have a view on the regime.
- **EW-Scale-Mom6** scales gross with momentum — owns ~1.27× in up-months, de-risks in
  down-months. It is the trending-market tool; it fails when momentum lags the turn (the
  2022 both-down shows the failure mode).
- **StructShort** is a permanent net-short-duration tilt — no signal, no lag, gross 1.0 so
  no leverage cost. It pays a carry drag in every non-stagflation year.
- **EW-MA-Short** is the balanced pick — positive upside beta, a both-down better than
  All-Weather, and the lowest downside correlation of any flavor with positive return.
- **LS-TSMOM** is long/short trend — positive in 2022 because it shorts the falling legs, but
  its upside beta is negative, so it diversifies rather than captures.

The rest of this document builds every tool (§3a–§3j) and gives each round's measured menu
(§5a–§5i). The full comparison table for all 47 flavors is in
[`output/risk_parity_eval_asym9/report_eval.md`](../output/risk_parity_eval_asym9/report_eval.md) §10.

---

## 0. Bottom line — a regime-conditional toolkit

**The tools specialize by circumstance — the value is the map of which tool to deploy
when, not a single flavor that does everything.** Across nine rounds and **47 TrendProtect
flavors** (plus the 6 base schemes), each round added a tool built for one regime and
isolated the boundary where it stops working. Three families of tools fall out cleanly:

- **Asymmetry tools (Upβ > Dnβ):** **EW-Infl-Both** (0.436 > 0.316) and **EW-Infl-BothL**
  (0.522 > 0.422) — round 7's leading ex-ante inflation-regime broad gate, byte-identical and
  stable through rounds 8 and 9. Both have **Sharpe ≈ 0** (net return ≈ 0): the broad gate
  bleeds carry in every non-crisis reflation month. **Defensive sleeves** for stagflation /
  both-down, not return strategies.
- **Return tools (beat All-Weather's 7.37%):** round 8's narrow inflation-confirmation gate
  (**EW-InflC-Both6** 8.38%; **EW-InflC-Dur** 7.30% / Sharpe 0.671, the first inflation-gate
  flavor with a positive bootstrap-CI lower bound) and round 9's scaled gross
  (**EW-Scale-Mom6** 8.50%, EW-Scale-Mom 7.91%, EW-Scale-MomL 8.05%) — plus the always-on
  RP winner / StructShort / RP-LS-Overlay. All have **Upβ < Dnβ**: use when you accept
  correlated downside.
- **Balanced tool:** **EW-MA-Short** (4.25%, positive Upβ, both-down better than
  All-Weather) — the closest to "correlated up, protected down" with positive return.

Each round isolated the circumstance a tool is right for, and the boundary where it stops
working:

- **Rounds 2–4b: shorting equity on a downside gate drives Upβ negative.** The only flavors
  that ever got Dnβ ≤ 0 were the round-4 hysteretic `asym_ma` family (EW-AsymMA-Short-6/9,
  EW-AsymMA-Tight), and every one of them had Upβ ≈ −0.11 too. Round 4b's sweep
  (`slow_entry` {6,9,12} × `fast_exit` {2,3} + a vol-regime gate) spanned the grid and proved
  this is **structural, not a tunable lag**: a single price-gate that flips the equity sleeve
  short necessarily carries that short through the early part of recoveries, and the EW
  base's other sleeves don't track equity rallies — so the portfolio's up-month beta is
  dominated by the (short) equity sleeve and goes negative. You cannot fix it by tuning the
  band. The tighter the band, the more *symmetric* (both negative), not the more asymmetric.
- **Round 5: decoupling fixes Upβ but an equity-only overlay can't bring Dnβ down.** The
  decoupled insurance overlay (a never-flipping long base + a separate additive short on the
  equity sleeves) made Upβ positive (0.015–0.240) across all five presets — the round-4b
  blocker is genuinely gone. But Dnβ stayed strongly positive (0.362–0.586) and Dnβ ≫ Upβ in
  every preset, because an *equity-only* short cannot touch the both-down (stagflation)
  months where **bonds and duration fall *with* equities**, and the lagging `dma`/`ma`
  downside signal fires ~12m after the drop (whipsaw), so the months that need hedging are
  hedged late or not at all. Both-down came out *worse* (−20% to −28%) than the round-4b
  hysteretic family.
- **Round 6: shorting duration/TLT in the overlay fixes the both-down regime but trades Upβ
  for it — and the fast drawdown trigger keeps Upβ but doesn't fire the hedge.** The
  duration/bond overlay (shorting the bond sleeves on their own downside signal,
  `w_hedge_bd`) plus a fast symmetric `eq_dd` drawdown trigger was the explicit ask, and it
  did mechanically hedge stagflation: the `dma`/`ma`-signal duration presets got both-down to
  **−12.10%** (EW-Hedge-Dur-MA, beating All-Weather's −18.74% and round-5's −20.17%) and
  Dn-corr down to 0.334. **But** adding a *second lagging* short (the bond short on the
  bond's own trend) drove Upβ **negative again** (−0.025 to −0.060) — the round-4b failure
  mode recurs on the duration leg, and the bigger bond hedge (EW-Hedge-Dur-2) went *negative
  net return* (−0.35%). The fast `eq_dd` trigger preserved Upβ (0.126–0.146) but a 10% bond
  drawdown threshold rarely fires for bonds, so the duration leg stayed quiet and Dnβ stayed
  high (0.54–0.56) while whipsaw added cost — its both-down was *worse* (−26%). No round-6
  preset beats 7.37% (best EW-Hedge-Dur-DD 3.29%); all DSR negative (−0.97 to −1.35). The
  brief's specific lever did its mechanical job (duration hedge → better both-down) but
  could not flip Upβ > Dnβ.
- **Round 7: a leading ex-ante macro gate achieves Upβ > Dnβ for the first time — but gives
  back the return.** Replacing the lagging sleeve-level trend with an *ex-ante inflation
  regime* (trailing-12m Commodities return, external to the combo) finally solved the
  timing problem that defeated rounds 2–6: it fires *before* the drop, not 12m after, so
  the short does not drag through recoveries and Upβ stays positive. Shorting **both**
  equity and duration when inflation is rising (the `EW-Infl-Both` / `-BothL` full risk-off)
  delivered the brief's property — Upβ 0.436/0.522 > Dnβ 0.316/0.422 — with the best
  both-down of the entire investigation (**−2.69%** / **−7.26%** vs AW −18.74%). **But** an
  ex-ante regime gate is *broad* (on in every rising-inflation month, drawdown or not), so
  the same hedge bleeds return in non-crisis reflation months (2021, 2024) — net return
  ≈ 0, Sharpe ≈ 0, DSR −1.29/−1.33. The duration-only round-7 presets (no equity short:
  `EW-Infl-Dur/-DurL/-DurL2`) kept AW-like return (6.79–7.30%, Sharpe 0.53–0.59) but failed
  the property (Upβ < Dnβ) with terrible both-down (−30% to −36%) — the long-duration tilt,
  held in *every* disinflation month rather than only drawdowns, compounded the 2022–23
  bond bear. So round 7 splits the brief cleanly: **the equity-short leg delivers the
  asymmetry property but kills the return; the duration-only leg keeps the return but fails
  the asymmetry.** No single round-7 preset has both.
- **Round 8: narrowing the gate with an equity-rolling confirmation restores the return but
  breaks the asymmetry — the gate-width trade-off is fundamental.** The round-7 verdict
  prescribed narrowing the broad inflation gate to fire only when inflation is rising *and*
  equity is already rolling over (`infl_confirm="eq_neg"`, a coincident 3m/6m US Equity
  confirmation AND-gated onto the leading inflation regime). It worked on the **return
  half**: no short in 2021/2024 reflation rallies (equity not rolling) → carry restored —
  **EW-InflC-Both** rose from round-7 EW-Infl-Both's −0.16% to 5.41%, and **EW-InflC-Both6**
  reached **8.38%, the first inflation-gate flavor to beat 7.37%**; EW-InflC-Dur (7.30% /
  Sharpe 0.671) is the first with a positive CI lower bound. **But** all five round-8
  flavors have Upβ < Dnβ (0.360<0.563 … 0.526<0.747) — the property, first met in round 7,
  is **lost**. The mechanism is the mirror image of round 7: the broad gate capped **both**
  Upβ and Dnβ (Dnβ more, since 2022 down-months were a subset of rising-inflation months
  and got shorted) → Upβ > Dnβ but return bled; the narrow gate stops shorting in
  non-rolling up-months → return restored → but it also stops shorting in the many
  equity-down months that are *not* inflation-up, so Dnβ rises back above Upβ. The
  broadness that delivered the asymmetry is the same broadness that bled the return —
  narrowing one fixes the other and breaks the first. **No free lunch in the gate width.**
- **Round 9: scaling gross with a lagging scalar *reverses* the asymmetry — the scaling
  primitive's asymmetry is set by the scalar's lead/lag, not by the scaling itself.**
  Round 9 changed the primitive entirely: instead of timing a *short*, it kept a never-flip
  long EW base and **scaled gross** by a per-month scalar `s_t ∈ [0.3, 1.5]` (`pos_t = s_t ·
  base_w`, long-only, leverage cost on `s_t > 1`) — the most theoretically direct construction
  for "correlated up, protected down" (own more up, less down, no short to time). Three
  scalar signals were tried: `eq_mom` (momentum-gated leverage, `s = clip(1 + k·eq_mom, fl,
  ce)`), `eq_vol` (vol-targeting à la Moreira-Muir, `s = clip(σ_tgt/σ_realized, fl, ce)`),
  and `infl_regime` (the round-7 leading gate reused as a scalar). The **return half was met
  again** — **EW-Scale-Mom6** at **8.50%** and **EW-Scale-MomL** at 8.05% both beat 7.37% —
  but **all five round-9 flavors have Dnβ > Upβ** (0.507<0.787, 0.427<0.651, 0.468<0.706,
  0.364<0.558, 0.563<0.785): the asymmetry came out **reversed**. The mechanism is the same
  lag problem that defeated rounds 2–4b and 5–6, now on the *gross* leg: every available
  scalar (momentum, vol, inflation) **lags**, so `s_t` is HIGH at the start of a drawdown
  (momentum still positive → leveraged *into* the drop → Dnβ amplified) and LOW at the
  start of a rally (momentum still negative → de-risked *into* the rebound → Upβ damped) —
  exactly backwards. Scaling does not *create* asymmetry; it *amplifies whatever lead/lag
  the scalar has*, and no contemporaneous scalar is available ex-ante. This is the sixth
  structural finding, and it generalizes the round-3/4b blocker: the lag problem is
  fundamental to any price/regime signal, whether it gates a *short* (rounds 2–8) or scales
  *gross* (round 9). The only two flavors ever to meet Upβ > Dnβ remain the round-7
  broad-gate shorts (EW-Infl-Both, EW-Infl-BothL), byte-identical in round 9, still
  ~0 return.

**What actually won, by objective (measured, OOS 2018–2026):**

| Objective | Flavor | Ann ret | Sharpe | Upβ | Dnβ | Dn-corr | Both-down |
|---|---|---:|---:|---:|---:|---:|---:|
| Best risk-adjusted long-only (the benchmark) | **All-Weather** | 7.37% | **1.055** | 0.327 | 0.475 | 0.793 | -18.74% |
| Beats AW on return (no asymmetry) | **RP winner (MinVar)** | 8.43%† | 0.609† | 0.625 | 0.937 | 0.762 | -43.12%† |
| **Asymmetry property ACHIEVED (first time, r7)** | **EW-Infl-Both** (r7) | −0.16% | −0.014 | **0.436** | **0.316** | 0.289 | **-2.69%** |
| **Asymmetry + widest Upβ−Dnβ gap (r7)** | **EW-Infl-BothL** (r7) | 0.22% | 0.017 | **0.522** | **0.422** | 0.318 | -7.26% |
| **Beats AW on return within infl-gate family (first time, r8)** | **EW-InflC-Both6** (r8) | **8.38%** | 0.652 | 0.466 | 0.655 | 0.538 | -29.64% |
| **Highest-Sharpe infl-gate + first +ve CI lower bound (r8)** | **EW-InflC-Dur** (r8) | 7.30% | 0.671 | 0.461 | 0.646 | 0.648 | -29.20% |
| **Beats AW on return via scaled-gross primitive (r9)** | **EW-Scale-Mom6** (r9) | **8.50%** | 0.609 | 0.427 | 0.651 | 0.728 | -46.50% |
| Beats AW on return via scaled-gross (r9, 3m mom) | **EW-Scale-Mom** (r9) | 7.91% | 0.616 | 0.507 | 0.787 | 0.728 | -40.90% |
| Beats AW on return via scaled-gross (r9, levered 2×) | **EW-Scale-MomL** (r9) | 8.05% | 0.578 | 0.364 | 0.558 | 0.728 | -45.78% |
| Best downside protection of all 47 (ex-Both) | **EW-Hedge-Dur-MA** (r6) | 2.28% | 0.296 | −0.025 | 0.243 | **0.334** | -12.10% |
| Round-7 return-keeper (no equity short) | **EW-Infl-Dur** (r7) | 6.79% | 0.587 | 0.542 | 0.711 | 0.675 | -30.11% |
| Best balance: positive Upβ + decent downside | **EW-MA-Short** (r3) | 4.25% | 0.613 | 0.013 | 0.123 | 0.224 | -12.97% |
| Round-5 best (Upβ fixed by construction) | **EW-Hedge-MA** (r5) | 3.60% | 0.463 | 0.127 | 0.362 | 0.510 | -20.17% |
| Round-6 best (fast trigger kept Upβ) | **EW-Hedge-Dur-DD** (r6) | 3.29% | 0.345 | 0.146 | 0.559 | 0.613 | -26.31% |

> **†** The RP winner is selected by the same `asymmetric2` relative-percentile score pool
> as the TrendProtect flavors, so its TRAIN-best combo shifts when the pool expands. In the
> round-7 measure (37 schemes) it was 9.94% / Sharpe 0.945 (6-sleeve combo); in the round-8
> measure (42 schemes) it is 8.43% / Sharpe 0.609 (5-sleeve combo). The MinVar engine on a
> given combo is unchanged — only the argmax over combos moved (see §5h opt-in). Both
> measures beat 7.37% on return; neither has the asymmetry (Dnβ > Upβ).

- **If the goal is purely return** and the asymmetric property is relaxed: the **RP winner
  (MinVar)** beats All-Weather on return (9.94% in the r7 measure, 8.43% in the r8 measure
  — see †) — but with Dnβ ≫ Upβ and the worst both-down, it is *more* correlated to
  equities on the way down, the opposite of the brief. Within the inflation-gate family,
  **EW-InflC-Both6** (8.38%, r8) and **EW-InflC-Dur** (7.30%, r8) also beat or match AW on
  return — but likewise with Upβ < Dnβ (property failed).
- **If the asymmetry property is the goal** (Upβ > Dnβ, the brief's core ask — first met in
  round 7): **EW-Infl-Both** (Upβ 0.436 > Dnβ 0.316) and **EW-Infl-BothL** (0.522 > 0.422) —
  the only two flavors in nine rounds with Upβ > Dnβ (byte-identical in rounds 8 and 9), and
  the best both-down of the entire investigation (−2.69% / −7.26% vs AW −18.74%). They are a
  *defensive hedge*: net return ≈ 0 / Sharpe ≈ 0, so they do not beat 7.37% — use as a
  protection sleeve, not a return strategy.
- **If "protected down" is the goal** regardless of upside: **EW-Infl-Both** (−2.69%) is
  the best both-down of any flavor across all nine rounds (Dn-corr 0.289), overtaking
  EW-Hedge-Dur-MA (−12.10%, r6) and EW-AsymMA-Tight (−10.91% in the round-2 measure; later
  re-measures with the larger score pool shifted its TRAIN-best combo). These are downside
  hedges, not "correlated up, protected down" with return.
- **If a balance is the goal** (the closest any flavor came to the brief *with positive
  return*): **EW-MA-Short** is the only flavor with **positive Upβ (0.013) AND both-down
  (−12.97%) better than All-Weather** — but its Dnβ (0.123) still exceeds Upβ, the return
  (4.25%) is well below AW, and Dn-corr is 0.224 (low but positive, not negative). Rounds 7,
  8, and 9 did not dethrone it: the round-7 broad-gate flavors are (property, ~0 return);
  the round-8 narrow-gate flavors are (return, no property); the round-9 scaled-gross
  flavors are (return, **reversed** asymmetry — Dnβ > Upβ).

**Statistical honesty (read before acting on any of the above).** Every flavor's
Deflated Sharpe Ratio is negative (−0.59 to −1.47); the flavors share sleeves (effective
N ≪ nominal N) and the selection is one TRAIN (2008–17) / TEST (2018–26) split = one
regime. The Sharpe 95% CIs almost all span zero — the exceptions are the round-8
confirmation-gate duration family (**EW-InflC-Dur** [0.11, 1.57], **EW-InflC-DurL**
[0.09, 1.53], **EW-InflC-Both6** [0.08, 1.50]) and the round-9 scaled-gross family
(**EW-Scale-Mom** [0.03, 1.46], **EW-Scale-Infl** [0.05, 1.42], **EW-Scale-Mom6**
[−0.02, 1.34], **EW-Scale-MomL** [−0.06, 1.28]), the first inflation-gate and scaled-gross
flavors with a positive (or near-zero) CI lower bound, though still not significant after
multiple-comparison correction (one split, shared sleeves). So **none of the "wins" above
is statistically significant** — this is an honest exploration of what the constructions
*can* do, not a proven edge, and the per-round verdicts below should be read in that light.

**The lever was tested in round 6 and also failed — then round 7 built the leading-macro
version and it delivered the asymmetry tool — then round 8 narrowed it and it delivered the
return tool, the two tools sitting at opposite ends of the gate-width trade-off.** The
round-5 diagnosis pointed to a
concrete mechanical fix: extend the overlay to **short the sleeves that fall in both-down —
bonds / duration (the brief's "long-term short a ticker" = short TLT / long-duration as a
conditional overlay)**, not equity alone, and/or replace the lagging trend gate with a
**fast equity-drawdown trigger** that fires *in* down-months. Round 6 built *both* and ran
them. The result: the duration overlay hedged stagflation as designed (both-down −12.10%
beats AW) but drove Upβ negative on the lagging `dma`/`ma` signal, while the fast `eq_dd`
trigger kept Upβ but its high threshold meant the duration leg rarely fired and Dnβ stayed
high. **Either a lagging short drags Upβ, or a fast short doesn't activate the hedge — the
property needs a hedge that fires reliably in down-months and never in up-months, which no
causal sleeve-level signal on this universe provides.** The remaining lever was a
*leading* (macro/regime) downside signal — a gate that fires *before* the equity drawdown —
or holding a genuinely short-duration *ticker* (short TLT) only inside an ex-ante
stagflation regime, rather than a sleeve-level trend gate. **Round 7 built exactly this** —
an ex-ante inflation regime (trailing-12m Commodities) driving the equity + duration shorts
— and it **achieved Upβ > Dnβ for the first time** (EW-Infl-Both 0.436 > 0.316, EW-Infl-BothL
0.522 > 0.422) with the best both-down on record (−2.69% / −7.26%). The remaining tension was
*return*: the broad ex-ante gate bleeds carry in non-crisis reflation months, so the two
property-meeting flavors have Sharpe ≈ 0. **Round 8 then built the prescribed narrower gate**
— fire only when inflation is rising **and** equity is already rolling over (leading macro
**and** a coincident 3m/6m confirmation) — and it **restored the return** (EW-InflC-Both6
8.38% beats 7.37%; EW-InflC-Dur 7.30% / Sharpe 0.671, first positive CI lower bound) **but
lost the asymmetry**: all five round-8 flavors have Upβ < Dnβ, because the narrow gate
covers too few equity-down months to keep Dnβ capped. The broadness that delivers the
asymmetry is the same broadness that bleeds the return — **no free lunch in the gate width.**
The asymmetry tool and the return tool sit at opposite ends of a **gate-width trade-off**:
broad protects down but bleeds up; narrow restores return but stops protecting. A gate
that is *broad in down-months and absent in up-months* — i.e. itself asymmetric — is what
would bridge them, and that is the round-4b hysteretic price-gate family, which flips the
base and drives Upβ negative. The never-flip additive-overlay construction (rounds 5–8)
avoids that Upβ drag but cannot be both broad and narrow at once. This is the **fifth
structural finding**: the asymmetry tool and the return tool are separated by the
gate-width trade-off, and the only construction that bridges it (a hysteretic asymmetric
gate) costs the upside beta. **Round 9 tried the last untried primitive — scaling gross
instead of timing a short** — and built the **trending tool** (EW-Scale-Mom6 8.50% beats
7.37%), but the lagging scalar **reverses the asymmetry**: every available scalar lags, so
it leverages *into* drawdowns and de-risks *into* rallies, giving Dnβ > Upβ in all five
presets. The lag problem that bounds the gating tools (rounds 2–4b, 5–6) is the same
problem that bounds the scaling tool — it is fundamental to any price/regime signal,
whether it gates a short or scales gross, and no contemporaneous scalar is available
ex-ante. This is the **sixth structural finding**: the trending tool is the wrong one at
the turn, for the same lag reason the price-gate tools are the wrong one for "correlated
up."

### How the tools fit together

After nine rounds, 47 TrendProtect flavors, and six structural findings, the picture is a
**regime-conditional toolkit**: the asymmetry tools and the return tools are built for
different circumstances, and the structural findings are the map of which tool is right
where. The tools, by job:

- **The asymmetry tools (Upβ > Dnβ):** round 7's leading ex-ante inflation-regime broad gate
  — **EW-Infl-Both** (0.436 > 0.316) and **EW-Infl-BothL** (0.522 > 0.422), byte-identical and
  stable through rounds 8 and 9. Both have **Sharpe ≈ 0**: the broad gate bleeds carry in
  every non-crisis reflation month. **Use as a defensive sleeve** for stagflation /
  both-down, not as a return strategy.
- **The return tools (beat 7.37%):** two primitives — round 8's narrow
  inflation-confirmation gate (**EW-InflC-Both6** 8.38%) and round 9's scaled gross
  (**EW-Scale-Mom6** 8.50%, EW-Scale-MomL 8.05%), plus the always-on RP winner / StructShort /
  RP-LS-Overlay. All have **Upβ < Dnβ** — use when you accept correlated downside (growth-up,
  trending, or a structural short-duration view).
- **The balanced tool:** **EW-MA-Short** (4.25%, positive Upβ, both-down better than
  All-Weather) — the closest to "correlated up, protected down" with positive return.

The six findings map to **three primitive families** plus the price-gate short, each with
the circumstance where its tool is right and the boundary where it is the wrong one:

- **Broad gate (round 7) → asymmetry tool.** Right for stagflation / both-down. Wrong when
  you need return: the broadness that caps Dnβ also bleeds carry in every non-crisis
  reflation month (Sharpe ≈ 0).
- **Narrow gate (round 8) → return tool.** Right for "inflation rising *and* equity rolling
  over." Wrong when you need the both-down hedge: it covers too few equity-down months to
  keep Dnβ capped — **no free lunch in the gate width**.
- **Scaled gross (round 9) → trending tool.** Right for trending up-markets. Wrong at the
  turn: every available scalar lags, so it leverages *into* drawdowns and de-risks *into*
  rallies, **reversing** the asymmetry — the same lag that bounds the short-leg gates bounds
  the gross-leg scaler.
- **Price-gate short (rounds 2–4b, 5–6) → crisis-alpha sleeve.** Right for an outright
  negative downside beta. Wrong for "correlated up": a single price-gate that flips the
  equity sleeve short necessarily carries that short through early recoveries, driving Upβ
  negative too. A hysteretic asymmetric gate on the never-flip overlay (shorting both equity
  and duration) is the natural next tool for the both-down hedge with positive upside beta;
  it inherits the same gate-width tension on a different axis (overlay size × re-entry
  speed) and is left as the open next step.

**Statistical caveat (unchanged):** every flavor's DSR is negative; almost all Sharpe CIs
span zero (the round-8 duration and round-9 scaled-gross families have positive/near-zero
lower bounds, still not significant after multiple-comparison correction); one TRAIN/TEST
split = one regime. This is an honest exploration of what the constructions *can* do, not a
proven edge. **The measured practical picks stand as documented above and in §5a–§5i.**

The rest of this document is the full per-flavor catalog (§3a–§3j build each tool) and the
per-round measured menus (§5a–§5i) from which this toolkit is synthesized.

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

## 3f. The decoupled insurance overlay (round 5)

Round 4b **disconfirmed** the "less overshoot" hypothesis and isolated the structural
blocker: in every `gate_mode="short"` flavor, the equity sleeve is **flipped** (long →
short) on the downside signal and sleeve-**netted** into the base, so through recoveries
the sleeve is still short until a re-entry trigger → Upβ goes negative. No band tuning
fixes it (Upβ pinned at ≈ −0.11 across the whole hysteresis grid). Round 5 is the
construction round 4b pointed to as the only remaining lever: **decouple the two halves
entirely** — keep a *long-only* base that **never flips** (so Upβ stays that of the
long-only base, **positive**) and add a **defined-downside insurance overlay** that is a
*separate notional* (additive gross, not sleeve-netted) short on the equity sleeves,
active only on a downside signal and **flat otherwise**. The brief's "long-term short a
ticker" permission is applied as an *overlay*, not a *gate*.

### The mechanical difference (the key innovation)
In `gate_mode="short"`, the equity sleeve weight is **multiplied** by the gate direction
(`base_w[eq] *= gd`): when `gd<0` the sleeve *becomes* negative — netted into one weight,
gross ≤ 1, no leverage cost, but the sleeve is short in up-months too until re-entry.
In `gate_mode="overlay"` (new), the long base is untouched (`long_leg = base_w` always),
and a **separate** short overlay `ol` is added: `ol[eq] = −w_hedge · base_w[eq]` only when
the signal is down, else 0. The return is `(base + ol) · R` (netted for P&L), but the
**gross is additive**: `gross = |base|.sum() + |ol|.sum() = 1 + w_hedge·(equity fraction)`
when active → leverage cost on the excess. This is the explicit price of decoupling (the
sleeve-netted flip was "free" gross-wise but killed Upβ; the additive overlay costs gross
but keeps Upβ positive). Per month:

```
up-month   (gd>0): ol = 0           → pos = base_w (fully long), gross = 1, no lev cost → Upβ = base Upβ ≈ +0.3
down-month (gd<0): ol = −w_hedge·base_w[eq] → pos[eq] = base_w[eq]·(1−w_hedge), gross = 1 + w_hedge·w_eq → Dnβ ↓
```

`w_hedge > 1` ⇒ net **short** equity in down-months (needed to push Dnβ negative); the
long base is still fully long in up-months (overlay flat). The overlay signal must be
**fast-off** in recoveries (the *opposite* hysteresis of round 4's `asym_ma`): a symmetric
signal (`dma` / `ma`) or `dd_stop` — **not** `asym_ma`, whose slow re-entry would drag the
rally exactly as in round 4. New `gate_mode="overlay"` branch in `_backtest_flavor`
(opt-in: existing presets set `w_hedge=0` and use `gate_mode` ∈ {cash, short} → the
overlay branch is never entered, `ol` stays zeros, gross uses the netted `|pos|.sum()` →
byte-identical).

### EW-Hedge-DMA-1 / EW-Hedge-DMA / EW-Hedge-DMA-2
- **Presets:** EW base, `gate_mode="overlay"`, `gate_signal="dma"` (fast 3m/10m dual-MA),
  `w_hedge` ∈ {1.0, 1.5, 2.0}. Brackets the hedge size: 1.0 = net equity to ~0 in
  down-months (a "cash on the downside" hedge, Dnβ reduced but likely still positive);
  1.5 = net **short** equity (the sizing expected to drive Dnβ negative with Upβ
  positive); 2.0 = strongest clip (most Dnβ reduction, most leverage cost + whipsaw).
- **Construction / holds / shorts:** long-only EW base (gross 1, never gated) held in
  *every* month; a separate short of `w_hedge · base_w` on each equity sleeve, active
  only when the dma signal is down. Additive gross → leverage cost only in down-months.
- **Parameters:** `w_hedge` ∈ {1.0, 1.5, 2.0}; `gate_signal="dma"`; `base_mode="ew"`.
- **Why these:** the w_hedge grid spans "hedge to cash" → "net short" → "net short 1×"
  to find the smallest w_hedge that drives Dnβ < 0 with Upβ > 0 (the unmet property),
  priced against the leverage cost and whipsaw.

### EW-Hedge-MA
- **Preset:** `gate_signal="ma"` (single 10m SMA), `w_hedge=1.5`. A slower, smoother
  downside trigger than dma → fewer false flips in chop, but deactivates slower in a
  V-rebound (price reclaims the 10m SMA late) → can drag the start of the rally (milder
  than round 4 because the base is always long). Tests signal choice on the overlay.

### EW-Hedge-DD
- **Preset:** `gate_signal="dd_stop"` (drawdown), `w_hedge=1.5`. The overlay shorts once
  an equity sleeve is >10% below its trailing 6m peak and deactivates once within 3% of
  the peak — "hedge the break, un-hedge the new high." The drawdown signal deactivates
  *naturally* when equity recovers (drawdown shrinks) → fast-off in V-rebounds without a
  separate re-entry MA. The most direct map to the brief's shape, now on a separate
  overlay (not a flip). Lagging trigger (misses the first 10% of the drawdown).

## 3g. The duration overlay + fast drawdown trigger (round 6)

Round 5 fixed the upside half (Upβ positive, by the never-flipping base) but left the
downside half broken for a diagnosed reason: an **equity-only** additive overlay cannot
touch the **both-down (stagflation) months where bonds and duration fall *with* equities**
(that gap is what kept Dnβ positive at 0.36–0.59), and the `dma`/`ma` downside signal
fires ~12m too late (whipsaw/lag — it turns on *after* the drop). Round 6 attacks both
halves of that diagnosis with two additive changes to the round-5 construction:

1. **A duration/bond overlay (`w_hedge_bd`).** Alongside the equity short
   (`ol[eq] = -w_hedge·base_w[eq]` when the equity sleeve's signal is down), the overlay
   **also** shorts the **bond** sleeves on **bonds' own** downside signal:
   `ol[bond] += -w_hedge_bd·base_w[bond]` when the bond sleeve's `gd < 0`. This reuses the
   same per-sleeve `gd` (no new signal plumbing) and is **self-avoiding flight-to-quality**:
   when bonds *rise* (2008 Q4, 2020 Q1 — equities down, bonds up) their `gd ≥ 0` so no bond
   short fires → no bleed in the very months an equity-down hedge would lose; when bonds
   *fall* (2022 stagflation) their `gd < 0` so the short fires → clips the both-down loss
   the equity-only overlay missed. `w_hedge_bd > 1` ⇒ net-short duration in bond-down
   months — the brief's "long-term short a ticker" (short TLT / long-duration) as a
   *conditional* overlay, not a permanent structural short.
2. **A fast equity-drawdown trigger (`gate_signal="eq_dd"`).** A **symmetric, stateless**
   drawdown gate: short a sleeve once it is > `dd_exit` (10%) below its trailing
   `dd_window` (6m) peak, long once back within `dd_entry` (3%) of the peak. Unlike round
   5's `dma`/`ma` (which need a ~12m trend to flip) and unlike `dd_stop` (hysteretic —
   stays short through chop), `eq_dd` **fires IN down-months and releases fast in
   recoveries**, the direct fix for the "fires too late" half of the diagnosis. The price
   is more whipsaw near peaks (no hysteresis dead-band beyond dd_exit/dd_entry).

**The mechanical difference (round 6, per month t):**

```
long_leg = base_w                         # NEVER flips (Upβ stays positive) — round 5
ol = 0
if equity sleeve signal gd[eq] < 0:       # round-5 equity overlay
    ol[eq]  = -w_hedge    * base_w[eq]
if w_hedge_bd > 0 and bond sleeve signal gd[bond] < 0:   # round-6 duration overlay
    ol[bond] = -w_hedge_bd * base_w[bond]
pos_target = long_leg + ol                # both shorts are SEPARATE notionals
gross      = |long_leg|.sum() + |ol|.sum()  # additive -> leverage cost on the excess
```

Up-month (everything up): `gd ≥ 0` on both equity and bonds → `ol = 0` → full long base,
**Upβ inherits the long-only EW base** (positive). Equity-down-only month
(flight-to-quality: equities down, bonds up): equity `gd < 0` → equity short fires; bonds
`gd ≥ 0` → **no bond short** (no flight-to-quality bleed). Both-down month (stagflation:
equities and bonds both down): **both** shorts fire → the portfolio is net-short equity
*and* net-short duration → this is the regime round 5 could not hedge and the one round 6
directly targets. The five presets sweep the signal (`dma`/`ma`/`eq_dd`) and the duration
size (`w_hedge_bd` 1.5 / 2.0):

| Preset | Equity signal | `w_hedge` | Bond signal | `w_hedge_bd` |
|---|---|:--:|---|:--:|
| **EW-Hedge-Dur** | dma | 1.5 | dma (own) | 1.5 |
| **EW-Hedge-Dur-MA** | ma | 1.5 | ma (own) | 1.5 |
| **EW-Hedge-Dur-DD** | **eq_dd** (fast) | 1.5 | dma (own) | 1.5 |
| **EW-Hedge-Dur-2** | dma | 1.5 | dma (own) | **2.0** |
| **EW-Hedge-Dur-DD2** | **eq_dd** (fast) | 1.5 | dma (own) | **2.0** |

EW-Hedge-Dur-DD is the user's literal ask (short duration in the overlay + a fast
equity-drawdown trigger); EW-Hedge-Dur-DD2 turns both levers to maximum. Opt-in: existing
presets keep `w_hedge_bd = 0` and `gate_signal ∈ {tsmom,ma,vol,dma,asym_ma,dd_stop,asym_vol}`
→ no bond overlay, no eq_dd path → byte-identical to round 5 (verified by the regression
guard §1–4 vs the round-4b anchor). The measured menu and verdict are in §5f.

## 3h. The inflation-regime leading gate (round 7)

Rounds 2–6 all gated the overlays off a *sleeve's own* price signal (trend / MA / vol /
drawdown), and every such signal is either **lagging** (fires ~12m after the drop, drags
through recoveries → kills Upβ) or **coincident/fast** (fires in down-months but whipsaws
near peaks and, for bonds, a 10% drawdown threshold rarely fires → Dnβ unmoved). The one
signal class never tried was a **leading** one — a macro/regime signal that fires *before*
the equity drawdown. Round 7 builds it: the overlays fire off an **ex-ante inflation
regime**, defined as the trailing-12m return of an **inflation-proxy sleeve** (Commodities by
default, read from the full `ret_full` panel — a macro signal *external to the combo*, so
it is available even when Commodities is not in the selected combo). Commodities *lead*
equities in the stagflation case (they topped before equities in 2022), making this the
first genuinely leading gate in the family.

The construction is **regime-conditional and symmetric** — the key design choice that
distinguishes round 7 from round 6. The never-flip long EW base is unchanged (Upβ stays
positive by construction). The overlays then act on the inflation regime:

- **Inflation RISING** (`infl_mom > 0`, stagflation risk-off — 2022): short the **bond**
  sleeves (`ol[bond] += -w_hedge_bd · base_w[bond]`) and, if `w_hedge > 0`, the **equity**
  sleeves too. Both asset classes fall in this regime, so the short clips the both-down loss
  the round-5/6 lagging gates missed or fired too late.
- **Inflation FALLING** (`infl_mom ≤ 0`, disinflation — 2008 Q4, 2020 Q1): add a
  **long-duration tilt** (`ol[bond] += +w_long_bd · base_w[bond]`) — *own more* of the bonds
  that rally in flight-to-quality. This is the regime where bonds hedge equity *for free*,
  and the tilt is the lever that can drag **Dnβ toward or below zero** (the round-5/6
  constructions had no long-duration lever, only shorts).

The per-month mechanical difference (round 7, `gate_signal="infl_regime"`, `gate_mode="overlay"`):

```
base_w          = EW weights (capped), never flipped (Upβ-positive base)
infl_mom_t       = prod(1 + Commodities[t-12:t]) - 1            # external macro signal
infl_up_t        = infl_mom_t > 0
long_leg         = base_w                                     # NEVER flipped
ol               = 0
if infl_up_t:                                             # stagflation risk-off
    ol[eq]    += -w_hedge    * base_w[eq]     (if w_hedge    > 0)
    ol[bond] += -w_hedge_bd  * base_w[bond]   (if w_hedge_bd > 0)
elif w_long_bd > 0:                                        # disinflation: flight-to-quality
    ol[bond] += +w_long_bd  * base_w[bond]
pos_target      = long_leg + ol
gross_notional  = |long_leg|.sum() + |ol|.sum()              # additive, leverage cost
```

The five round-7 presets isolate the levers:

| Flavor | `w_hedge` (eq short, infl↑) | `w_hedge_bd` (bond short, infl↑) | `w_long_bd` (bond long, infl↓) |
|---|:--:|:--:|:--:|
| **EW-Infl-Dur** | 0.0 | 1.5 | 0.0 |
| **EW-Infl-DurL** | 0.0 | 1.5 | **1.5** |
| **EW-Infl-Both** | **1.5** | 1.5 | 0.0 |
| **EW-Infl-BothL** | **1.5** | 1.5 | **1.5** |
| **EW-Infl-DurL2** | 0.0 | 1.5 | **2.0** |

EW-Infl-Dur isolates the duration-regime short (no equity short, no long tilt); EW-Infl-DurL
adds the flight-to-quality long tilt (the symmetric regime switch on duration); EW-Infl-Both
adds the equity short in stagflation (the full risk-off); EW-Infl-BothL is the maximal
three-leg regime switch; EW-Infl-DurL2 pushes the long-tilt hardest to drive Dnβ most
negative. Opt-in: existing presets keep `w_long_bd = 0` and `gate_signal ≠ "infl_regime"` →
the infl_regime branch is never entered, `_gate_signal` returns zeros for it, and the gross
condition adds `w_long_bd > 0` only for round-7 presets → byte-identical to round 6 (verified
by the regression guard §1–4 vs the round-4b anchor). The measured menu and verdict are in §5g.

---

## 3i. The equity-rolling confirmation gate (round 8)

Round 7's verdict (§5g) named the single remaining lever: the leading inflation gate is
*broad* — it shorts in *every* rising-inflation month, drawdown or not, so the
property-meeting flavors bleed return in non-crisis reflation months (2021, 2024) and the
duration-only flavors that keep the return fail the property because the long-tilt is held
in *every* disinflation month (including 2022–23, when bonds fell *during* the equity
recovery). The fix is to **narrow WHEN the gate fires** without touching the leading
macro signal itself: keep the ex-ante inflation regime (still leading, still external), but
require a **coincident equity-rolling confirmation** before either overlay leg acts.

Round 8 adds one knob, `infl_confirm` (default `""` = off → round-7 behavior byte-identical).
The only implemented mode is `"eq_neg"`: a per-month flag `eq_rolling` that is **true when
the external equity proxy** (US Equity, from `ret_full` — the same external panel as the
inflation proxy, *outside the combo*) **has a negative trailing-`eq_confirm_lookback` return**
(default 3m). The overlays then fire only when their regime condition is **confirmed** by
equity actually rolling over:

- **Short legs** (`w_hedge` / `w_hedge_bd`): fire when `infl_up AND eq_rolling` — inflation
  rising *and* equity already falling. This is the 2022 stagflation regime (commodities up,
  equities down) and *not* the 2021/2024 reflation rallies (commodities up, equities *also*
  up → `eq_rolling` false → no short → return preserved).
- **Long-duration tilt** (`w_long_bd`): fires when `(NOT infl_up) AND eq_rolling` —
  disinflation *and* equity falling. This is the **true flight-to-quality** regime (2008 Q4,
  2020 Q1: disinflation + equity crash + bonds rally) and *not* 2022–23 (disinflation but
  equities recovering → `eq_rolling` false → no long-tilt → the round-7 `EW-Infl-DurL` both-
  down bleed is removed).

The leading macro gate stays ex-ante (it still fires *before* the drop on the inflation
side); the confirmation only narrows the *when*. The per-month mechanical difference
(round 8, `gate_signal="infl_regime"`, `gate_mode="overlay"`, `infl_confirm="eq_neg"`):

```
base_w          = EW weights (capped), never flipped (Upβ-positive base)
infl_mom_t       = prod(1 + Commodities[t-12:t]) - 1            # external, LEADING macro
infl_up_t        = infl_mom_t > 0
eq_mom_t         = prod(1 + US Equity[t-3:t]) - 1               # external, COINCIDENT confirm
eq_rolling_t     = eq_mom_t < 0                                 # (infl_confirm="eq_neg" only)
# (infl_confirm off  OR  no equity proxy  ->  eq_rolling = True  =>  round-7 behavior)
long_leg         = base_w                                     # NEVER flipped
ol               = 0
if infl_up_t and eq_rolling_t:                                # stagflation + eq rolling over
    ol[eq]    += -w_hedge    * base_w[eq]     (if w_hedge    > 0)
    ol[bond] += -w_hedge_bd  * base_w[bond]   (if w_hedge_bd > 0)
elif (not infl_up_t) and eq_rolling_t and w_long_bd > 0:      # flight-to-quality (eq rolling)
    ol[bond] += +w_long_bd  * base_w[bond]
pos_target      = long_leg + ol
gross_notional  = |long_leg|.sum() + |ol|.sum()              # additive, leverage cost
```

The five round-8 presets (`infl_confirm="eq_neg"`, `eq_confirm_lookback=3` unless noted)
isolate the levers — they are the round-7 grid with the confirmation gate layered on:

| Flavor | `w_hedge` (eq short) | `w_hedge_bd` (bond short) | `w_long_bd` (bond long) | `eq_confirm_lookback` |
|---|:--:|:--:|:--:|:--:|
| **EW-InflC-Both** | **1.5** | 1.5 | 0.0 | 3 |
| **EW-InflC-BothL** | **1.5** | 1.5 | **1.5** | 3 |
| **EW-InflC-Dur** | 0.0 | 1.5 | 0.0 | 3 |
| **EW-InflC-DurL** | 0.0 | 1.5 | **1.5** | 3 |
| **EW-InflC-Both6** | **1.5** | 1.5 | 0.0 | **6** |

`EW-InflC-Both` is the direct test of the round-7 verdict's lever: does narrowing the broad
inflation short to "inflation up AND equity rolling" restore the return (no short in 2021/2024)
while keeping Upβ > Dnβ and the 2022 both-down protection (inflation up + equity falling → short
fires)? `EW-InflC-BothL` adds the gated long-tilt (flight-to-quality only) — does it add
flight-to-quality carry (2008/2020) without the 2022–23 disinflation-with-bonds-falling bleed?
`EW-InflC-Dur` / `-DurL` test whether the confirmation alone lifts the round-7 duration-only
return above 7.37% AND recovers the both-down (gated long-tilt fires only in true
flight-to-quality). `EW-InflC-Both6` is a 6m-confirmation sensitivity (slower, less whipsaw-prone).

**Opt-in:** `infl_confirm` defaults to `""`, so the 37 pre-round-8 presets take the
`eq_rolling = True` branch → the round-8 `if infl_up and eq_rolling:` reduces to
`if infl_up:` and `elif (not infl_up) and eq_rolling and w_long_bd > 0:` reduces to
`elif w_long_bd > 0:` → **byte-identical to round 7** (the regression guard §1 confirms no
crash on the new code paths; the shared-scheme §10 diff confirms zero engine-output regressions).
The measured menu and verdict are in §5h.

---

## 3j. Regime-scaled gross — vol-targeting / momentum-gated leverage (round 9)

Rounds 1–8 all shared **one primitive**: a fixed-gross long base plus a *timing-gated
short* overlay (or a base flip). The round-8 verdict — "no free lunch in gate width: a
broad short gate delivers Upβ > Dnβ but bleeds return; a narrow one keeps return but
covers too few down-months" — is a tension **of that primitive**. Round 9 tries a
genuinely different primitive: **scale gross itself**, long-only, with no short to time.

The never-flip long EW base is multiplied each month by a scalar `s_t ∈ [scale_floor,
scale_ceil]`:

```
pos_t = s_t · base_w          # long-only, never flips; base_w = EW (capped), sum=1
gross_t = s_t                 # |pos|.sum() = s_t  (base_w ≥ 0, sums to 1)
lev_cost_t = max(0, s_t − 1) · lev_rate/12      # 5.8% APR funding on the leveraged gross
```

`s_t > 1` (leverage) in up/calm months → own *more* of the base; `s_t < 1` (de-risk) in
down/stress months → own *less*. Because the base never flips and there is no short,
**Upβ > Dnβ is constructed by design**: Upβ is *amplified* in up-months (≈ `scale_ceil`×
invested) while Dnβ is *damped* in down-months (≈ `scale_floor`× invested) — no
Upβ-drag-through-recoveries (the round-4b blocker) and no short-timing tension (the
round-7/8 blocker). The return comes from being fully + leveraged invested in up-months;
the price is the 5.8% funding cost on `s_t > 1` and the momentum/vol lag (still leveraged
at the *start* of a drawdown, de-risked at the *start* of a rally — a whipsaw cost, but
one that caps rather than flips beta).

Three scalar signals (`scale_signal`, default `""` = off → all existing presets
byte-identical, opt-in):

```
eq_mom      s_t = clip(1 + scale_k · eq_mom_t,            floor, ceil)
            eq_mom_t = ∏(1 + US Equity[t-L:t]) − 1        # L = scale_lookback (external proxy)
            → momentum-gated leverage: own more when equity up, less when down.

eq_vol      s_t = clip(target_vol / realized_eq_vol_ann,  floor, ceil)
            realized_eq_vol_ann = std(US Equity[t-L:t]) · √12
            → vol-targeting (Moreira-Muir): de-risk when vol high (stress), lever when low (calm).

infl_regime s_t = floor  if infl_up   (stagflation: de-risk the long base)
            s_t = ceil   otherwise    (disinflation: lever up)
            → the round-7 LEADING inflation gate applied as a SCALAR, not a short:
              tests whether de-risking the long base in stagflation (vs round-7 SHORTING
              it, which bled return or broke the property) delivers the asymmetry WITH return.
```

The five round-9 presets (all `base_mode="ew"`, `trend_gate=False`, no overlay/short —
pure scaled long base):

| Flavor | `scale_signal` | `scale_k` | `scale_lookback` | `scale_floor` | `scale_ceil` | other |
|---|---|---|---|---|---|---|
| **EW-Scale-Mom** | `eq_mom` | 2.0 | 3 | 0.3 | 1.5 | — |
| **EW-Scale-Mom6** | `eq_mom` | 2.0 | **6** | 0.3 | 1.5 | slower window (less whipsaw) |
| **EW-Scale-Vol** | `eq_vol` | — | 6 | 0.3 | 1.5 | `scale_target_vol=0.12` |
| **EW-Scale-MomL** | `eq_mom` | **3.0** | 3 | 0.3 | **2.0** | aggressive lever (push return) |
| **EW-Scale-Infl** | `infl_regime` | — | — | 0.4 | 1.3 | `infl_lookback=12` (round-7 gate as scalar) |

`EW-Scale-Mom` is the headline test of the new primitive: does scaling gross (vs timing a
short, rounds 1–8) deliver **both halves** — beat 7.37% **and** Upβ > Dnβ — in one flavor?
`EW-Scale-Mom6` / `-Vol` probe robustness to the signal (slower momentum / vol-targeting).
`EW-Scale-MomL` pushes the up-month lever harder to close the return gap. `EW-Scale-Infl`
retests the round-7 leading gate under the new primitive (de-risk the base in stagflation
rather than short it).

**Opt-in:** `scale_signal` defaults to `""`, so `s_t = 1.0` and `pos_target · 1.0` is a
no-op → all 45 pre-round-9 presets are byte-identical (the new params are read but unused;
the new code paths are fully guarded by `if scale_signal != ""`). The measured menu and
verdict are in §5i.

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

# Asymmetric2-score canonical (round 5, +five decoupled-overlay flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short,EW-Hedge-DMA-1,EW-Hedge-DMA,EW-Hedge-DMA-2,EW-Hedge-MA,EW-Hedge-DD \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym5
# → output/risk_parity_eval_asym5/report_eval.md (§10 = the round-5 decoupled-overlay menu)

# Asymmetric2-score canonical (round 6, +five duration-overlay / eq_dd flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short,EW-Hedge-DMA-1,EW-Hedge-DMA,EW-Hedge-DMA-2,EW-Hedge-MA,EW-Hedge-DD,EW-Hedge-Dur,EW-Hedge-Dur-MA,EW-Hedge-Dur-DD,EW-Hedge-Dur-2,EW-Hedge-Dur-DD2 \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym6
# → output/risk_parity_eval_asym6/report_eval.md (§10 = the round-6 duration-overlay menu)

# Asymmetric2-score canonical (round 7, +five inflation-regime leading-gate flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short,EW-Hedge-DMA-1,EW-Hedge-DMA,EW-Hedge-DMA-2,EW-Hedge-MA,EW-Hedge-DD,EW-Hedge-Dur,EW-Hedge-Dur-MA,EW-Hedge-Dur-DD,EW-Hedge-Dur-2,EW-Hedge-Dur-DD2,EW-Infl-Dur,EW-Infl-DurL,EW-Infl-Both,EW-Infl-BothL,EW-Infl-DurL2 \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym7
# → output/risk_parity_eval_asym7/report_eval.md (§10 = the round-7 inflation-regime menu)

# Asymmetric2-score canonical (round 8, +five equity-rolling confirmation-gate flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --schemes EW,InvVol,InvVar,ERC,MinVar,LS-TSMOM,TrendGate,TG-Short,TG-Short-LS,TG-Short-6m,EW-Short,EW-Short-LS,EW-Short-6m,EW-MA-Short,EW-Vol-Short,EW-DMA-Short,EW-AsymMA-Short,EW-DDStop-Short,EW-AsymMA-Short-6,EW-AsymMA-Short-9,EW-AsymMA-Tight,EW-AsymVol-Short,EW-Hedge-DMA-1,EW-Hedge-DMA,EW-Hedge-DMA-2,EW-Hedge-MA,EW-Hedge-DD,EW-Hedge-Dur,EW-Hedge-Dur-MA,EW-Hedge-Dur-DD,EW-Hedge-Dur-2,EW-Hedge-Dur-DD2,EW-Infl-Dur,EW-Infl-DurL,EW-Infl-Both,EW-Infl-BothL,EW-Infl-DurL2,EW-InflC-Both,EW-InflC-BothL,EW-InflC-Dur,EW-InflC-DurL,EW-InflC-Both6 \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym8
# → output/risk_parity_eval_asym8/report_eval.md (§10 = the round-8 confirmation-gate menu)

# Asymmetric2-score canonical (round 9, +five regime-scaled-gross flavors):
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
  --rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym9
# → output/risk_parity_eval_asym9/report_eval.md (§10 = the round-9 scaled-gross menu)
# (--schemes defaults to all 50 SCHEME_ORDER; --ref-mode external and --lev-rate 0.058
#  are the defaults. 2817 × 50 = 140 850 TRAIN trials.)

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
> *also* suppresses the upside (Upβ goes negative with it), so a single price-gate cannot
> deliver both the asymmetry and the return in one TRAIN/TEST split. The
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

## 5e. Comparison menu — round 5 (measured, out-of-sample)

Round 5 implemented the lever round 4b identified: a **decoupled insurance overlay**
(§3f). The long base never flips (stays at `base_w` every month → Upβ inherits the
long-only base's positive equity beta), and a *separate additive* short overlay on the
equity sleeves fires only on a downside signal and is flat otherwise. Five presets sweep
the overlay size (`w_hedge` 1.0 / 1.5 / 2.0) and the downside signal (`dma`, `ma`,
`dd_stop`). The canonical run is `output/risk_parity_eval_asym5/report_eval.md`
(27 schemes, 76,059 TRAIN trials; §1–4 byte-identical to the round-4b anchor, confirming
the new code path is opt-in).

Menu (the five EW-Hedge presets in context with AW, the RP winner, and the strongest
prior flavors). Reading the asymmetric columns: Upβ = β to equity on equity-up months;
Dnβ = β on equity-down months; Dn-corr = corr with equity on equity-down months.

| Portfolio | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev cost/yr | DSR | Sharpe CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| RP winner (MinVar) | 9.94% | **0.945** | -15.98% | -31.91% | 0.406 | 0.619 | 0.708 | 1.00 | 0.00% | — | — |
| EW-AsymMA-Tight (r4b) | 3.85% | **0.642** | -13.82% | -10.91% | 0.057 | 0.271 | 0.417 | 1.00 | 0.00% | -0.67 | [-0.01, 1.58] |
| EW-MA-Short (r3) | 4.25% | **0.613** | -14.02% | -12.97% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | -0.70 | [-0.08, 1.40] |
| **EW-Hedge-MA** | 3.60% | **0.463** | -18.19% | -20.17% | 0.127 | 0.362 | 0.510 | 0.90 | 0.00%¹ | -0.85 | [-0.20, 1.34] |
| **EW-Hedge-DMA-1** | 3.53% | **0.393** | -20.55% | -25.35% | 0.240 | 0.583 | 0.642 | 1.00 | 0.00%¹ | -0.92 | [-0.18, 1.31] |
| **EW-Hedge-DD** | 3.16% | **0.346** | -22.43% | -26.08% | 0.182 | 0.586 | 0.645 | 1.00 | 0.00%¹ | -0.97 | [-0.29, 1.30] |
| **EW-Hedge-DMA** | 2.03% | **0.234** | -22.43% | -22.50% | 0.129 | 0.524 | 0.581 | 1.00 | 0.00%¹ | -1.08 | [-0.37, 1.15] |
| **EW-Hedge-DMA-2** | 2.03% | **0.207** | -18.12% | -28.02% | 0.015 | 0.391 | 0.400 | 1.00 | 0.00%¹ | -1.10 | [-0.40, 0.93] |

> ¹ The `Gross` / `Lev cost/yr` columns report the **last TEST month's netted**
> `|last_w|.sum()` and `(that − 1)·5.8%`, *not* the average additive gross. The overlay's
> leverage cost **is** charged in the net return every month it fires (additive
> `|long_leg| + |overlay|` gross, line 980); the column simply under-reports it because it
> snapshots one netted month. EW-Hedge-MA's gross 0.90 means the overlay was net-short
> equity in the final month (the −1.5× hedge netted the equity sleeve past zero and pulled
> `|pos|.sum()` below 1).

### What round 5 changed, measured

- **The decoupled overlay FIXED Upβ.** All five EW-Hedge presets have **positive Upβ
  (0.015–0.240)** — exactly the round-4b structural blocker (Upβ stuck at −0.11 because a
  `gate_mode=short` gate flips the long book short through recoveries) is resolved by the
  never-flipping long base. This is the construction's first-order win: the upside is now
  genuinely *kept*.
- **But Dnβ did NOT go negative.** Dnβ stayed **strongly positive (0.362–0.586)** across
  all five presets, and **Dnβ ≫ Upβ in every single one** (the property Upβ > Dnβ is still
  not met). The additive equity short (`w_hedge·base_w[eq]`) only offsets the *equity*
  sleeve's downside; it does not offset the bond / gold / commodity sleeves that *also*
  fall in both-down (stagflation) months, and the `dma`/`ma` downside signal does not
  reliably fire *in* the down-months (whipsaw / lag — the signal turns on after the drop),
  so the months that actually need hedging are often hedged late or not at all.
- **Both-down is WORSE than the round-4b hysteretic family.** EW-Hedge both-down is
  **−20% to −28%**, vs EW-AsymMA-Tight's **−10.91%** and EW-MA-Short's **−12.97%**. The
  additive overlay adds gross (→ leverage cost) and whipsaws, but — firing only on equity
  and only when the lagging signal agrees — it does not buy enough downside dampening to
  cover its cost in the both-down regime that dominates the worst months.
- **Return is below AW in every preset** (best EW-Hedge-MA 3.60% < AW 7.37%), and every
  preset's DSR is negative (−0.85 to −1.10) with a Sharpe CI whose lower bound is below
  zero — i.e. none is statistically significant, and the family shares sleeves
  (effective N ≪ nominal N) on one TRAIN/TEST split.

### Verdict (round 5)

The decoupled overlay is a **genuine structural fix for the upside half** (Upβ is positive
by construction now, the round-4b blocker is gone) but it **failed on the downside half**:
Dnβ is still strongly positive and in fact *larger* than Upβ, so the brief's
"correlated up, **not** down" property is **still not satisfied** — now for the *opposite*
reason than round 4b (round 4b: Upβ driven negative; round 5: Dnβ won't come down). An
**equity-only** downside overlay cannot protect the both-down (stagflation) months where
bonds and duration fall *with* equities, and a slow `dma`/`ma` gate fires too late to
hedge the months that actually hurt. No EW-Hedge preset beats All-Weather's 7.37% / 1.055
net OOS.

### Top picks (round 5 — the menu updated)

- **Best of the EW-Hedge family (and the round-5 representative):** **EW-Hedge-MA** —
  3.60% / Sharpe 0.463, Upβ **0.127 (positive)**, Dnβ 0.362, Dn-corr 0.510, gross 0.90,
  DSR −0.85. The `ma` (symmetric 12m) signal whipsawed least and kept the highest Sharpe
  of the family; Upβ is genuinely positive (the never-flip base working). But Dnβ 0.362 >
  Upβ 0.127 — the asymmetric property is not met, and return is < AW.
- **Highest Upβ of the family (purest "kept the upside"):** **EW-Hedge-DMA-1** — Upβ
  **0.240** (highest of any round-5 preset), Dnβ 0.583. The smallest hedge (w_hedge 1.0)
  disturbs the long base least → most upside kept → but also the least downside hedge.
- **"Protected down" champion is STILL a round-4b flavor, not a round-5 one:**
  **EW-AsymMA-Tight** (both-down −10.91%, Dn-corr 0.417) and **EW-MA-Short** (both-down
  −12.97%, Upβ 0.013) both protect the both-down regime better than *any* EW-Hedge preset.
  Round 5's overlay did not dethrone them on downside; it only fixed Upβ — at the cost of
  making both-down worse.
- **Best return (beats AW, no asymmetry):** **RP winner (MinVar)** — 9.94% / Sharpe 0.945,
  Dnβ 0.619 > Upβ 0.406. Unchanged (long-only risk parity).
- **The next lever (round 6, not yet run):** the overlay must short the sleeves that fall
  in both-down — **bonds / duration** (the brief's "long-term short a ticker" = short
  TLT / long-duration as a *conditional* overlay that fires on the same downside signal),
  not equity alone — and/or use a downside signal that reliably activates *in* equity-down
  months (e.g. a fast equity-drawdown trigger rather than the sleeve's own lagging trend).
  Shorting duration in the both-down regime is the direct mechanical fix for the
  "bonds fall with equities" gap that keeps Dnβ positive.

## 5f. Comparison menu — round 6 (measured, out-of-sample)

Round 6 ran the two levers identified at the end of §5e **together**: (a) a
**duration/bond overlay** that additively shorts the *bond* sleeves on their own
downside signal (`ol[bond] += -w_hedge_bd · base_w[bond]` when the sleeve's gate signal is
negative — a self-avoiding flight-to-quality short: bonds *up* → no short, bonds
*down*/stagflation → short fires), and (b) a **fast symmetric equity-drawdown trigger**
(`gate_signal="eq_dd"`) that shortens a sleeve once it is >10% below its trailing 6-month
peak and re-longs it once back within 3% of the peak — a stateless, fast-in / fast-out
trigger designed to fire *in* equity-down months and release quickly in recoveries (no
lagging-through-recovery Upβ drag). Five presets combine these: `dma`/`ma` gate signals at
`w_hedge=1.5, w_hedge_bd=1.5` (EW-Hedge-Dur, EW-Hedge-Dur-MA) and the fast `eq_dd` signal at
the same and a larger bond-hedge (`w_hedge_bd=2.0`: EW-Hedge-Dur-DD, EW-Hedge-Dur-DD2), plus
a bigger duration hedge on the `dma` signal (EW-Hedge-Dur-2).

Canonical report: `output/risk_parity_eval_asym6/report_eval.md` (32 schemes, 90 144 TRAIN
trials; opt-in verified — `output/rp_reg6/report_eval.md` §1–4 byte-identical to the
round-4b anchor; existing presets are unchanged because `w_hedge_bd` and `eq_dd` default
off).

| Flavor | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev/yr | DSR | Sharpe CI |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| **All-Weather** (ref) | 7.37 | 1.055 | −12.31 | −18.74 | 0.327 | 0.475 | 0.793 | 1.00 | ~0 | — | — |
| **RP winner** (MinVar) | 9.94 | 0.945 | −15.98 | −31.91 | 0.406 | 0.619 | 0.708 | 1.00 | ~0 | — | — |
| EW-MA-Short (best prior balance) | 4.25 | 0.613 | — | −12.97 | 0.013 | 0.123 | — | 1.00 | ~0 | — | — |
| **EW-Hedge-Dur** (dma) | 0.26 | 0.030 | −28.01 | −14.07 | −0.024 | 0.399 | 0.430 | 1.00 | ~0 | −1.28 | [−0.68, 1.07] |
| **EW-Hedge-Dur-MA** (ma) | 2.28 | 0.296 | −21.40 | −12.10 | −0.025 | 0.243 | 0.334 | 0.90 | ~0 | −1.02 | [−0.49, 1.30] |
| **EW-Hedge-Dur-2** (dma, bd2) | −0.35 | −0.040 | −30.47 | −12.73 | −0.060 | 0.373 | 0.392 | 1.00 | ~0 | −1.35 | [−0.77, 0.98] |
| **EW-Hedge-Dur-DD** (eq_dd) | 3.29 | 0.345 | −23.63 | −26.31 | 0.146 | 0.559 | 0.613 | 1.00 | ~0 | −0.97 | [−0.32, 1.33] |
| **EW-Hedge-Dur-DD2** (eq_dd, bd2) | 3.02 | 0.315 | −24.03 | −25.75 | 0.126 | 0.542 | 0.593 | 1.00 | ~0 | −1.00 | [−0.37, 1.31] |

(All rows measured over the TEST window 2018-01 → 2026-07. "Both-down" = annualized return
in months where the equity reference (SPY) *and* bond reference (AGG) are both down. Upβ /
Dnβ are the upside/downside betas vs SPY. DSR = Deflated Sharpe Ratio effective-N over the
round-6 trial count; Sharpe CI = 80% block-bootstrap interval.)

### Verdict (round 6)

**Shorting duration/TLT in the overlay — the user's specific ask — did NOT achieve
Upβ > Dnβ either.** Every EW-Hedge-Dur preset still has Dnβ > Upβ (Dnβ 0.24–0.56 vs Upβ
−0.060 to +0.146). Two distinct failure modes, one per gate signal:

1. **The `dma`/`ma`-signal duration presets (EW-Hedge-Dur, -Dur-MA, -Dur-2) drove Upβ
   negative again** (−0.024, −0.025, −0.060). The duration short *does* mechanically hedge
   stagflation — both-down improved to −12.10% / −14.07% / −12.73% (EW-Hedge-Dur-MA's
   −12.10% beats All-Weather's −18.74% and round-5's best EW-Hedge-MA −20.17%), and Dn-corr
   fell to 0.334–0.430 — *exactly the regime the lever was designed for*. But adding a
   *second lagging* short (the bond short on the bond's own `dma`/`ma` trend) reintroduced
   the round-4b failure mode on the bond side: the signal stays short through bond
   *recoveries*, and those recoveries frequently coincide with equity-up months (a
   rebound out of a growth scare), so the bond short drags Upβ negative — *despite* the
   never-flipping long base. The bigger bond hedge (EW-Hedge-Dur-2, `w_hedge_bd=2.0`) made
   this worse, pushing the net return *negative* (−0.35%) and Upβ to −0.060. So the
   duration overlay trades Upβ for both-down — the same tension as every lagging short,
   now on the duration leg.

2. **The fast `eq_dd` trigger kept Upβ positive** (EW-Hedge-Dur-DD 0.146, -DD2 0.126 — the
   fast-in/fast-out drawdown gate does *not* drag through recoveries, confirming the
   design intent) **but did not help Dnβ and made both-down *worse*** (−26.31% / −25.75%,
   worse than All-Weather). The reason: a 10% bond drawdown threshold rarely fires for
   bonds (far less volatile than equities), so the duration leg stays quiet outside a true
   bond rout — the duration hedge *didn't actually activate much* under `eq_dd`, leaving
   Dnβ high (0.54–0.56). And where the gate *did* toggle near equity drawdowns it whipsawed
   (short ↔ long near the 3%/10% dead-zone), and the leverage cost + whipsaw outweighed the
   hedge in the both-down months.

No round-6 flavor beats All-Weather's 7.37% / 1.055 (best is EW-Hedge-Dur-DD 3.29% /
0.345); every DSR is negative (−0.97 to −1.35); one split bootstrap CI straddles zero
(EW-Hedge-Dur-DD [−0.32, 1.33]) — none is significant. This is now **six rounds / 32
flavors** and **zero** of them has Upβ > Dnβ. Scanning the full round-6 §10 menu (all 32
flavors re-measured in one report), *every single one* has Upβ < Dnβ — the property is met
by no flavor, not just no round-6 flavor.

**Structural reason (the honest conclusion across all six rounds):** the "correlated up,
**not** down" property requires a downside hedge with effectively *perfect* timing — fire
*only* in down-months, *never* in up-months. On this universe (US/intl equity + REIT +
preferred + 4 bond sleeves + gold/silver/commodities/currency) no causal signal provides
that timing: every *lagging* signal (trend/`dma`/`ma`/`vol`) stays short through
recoveries and drags Upβ; every *fast* signal (`eq_dd` drawdown gate) whipsaws near peaks
and either doesn't activate the hedge (bonds' threshold too high) or adds leverage cost
without offsetting downside. The round-5 decoupled overlay fixed the *upside* half (Upβ
positive by construction) but the *downside* half — Dnβ coming down *below* Upβ — needs a
hedge that fires reliably in equity-down months and never in equity-up months, which
sleeve-level overlays on these sleeves cannot deliver.

### Top picks (round 6 — the menu updated)

- **Best both-down of the entire investigation:** **EW-Hedge-Dur-MA** — both-down **−12.10%**
  (beats All-Weather's −18.74% and is the best of all 32 flavors on the stagflation
  regime), Dn-corr 0.334 (lowest of the round-6 family). The duration overlay *did* its job
  for the both-down regime. But Upβ −0.025 (negative) and net 2.28% << 7.37%, so the brief
  is not met — Upβ was sacrificed to win both-down.
- **Best Upβ of the round-6 family (purest "kept the upside"):** **EW-Hedge-Dur-DD** — Upβ
  **0.146** (positive, the fast `eq_dd` trigger preserved the upside), Dnβ 0.559, both-down
  −26.31% (worse than AW). Fast trigger keeps Upβ but doesn't hedge duration — the
  inverse trade-off.
- **Best-balance flavor across ALL six rounds is STILL a round-4b flavor, not a round-6
  one:** **EW-MA-Short** (4.25% / Sharpe 0.613, Upβ 0.013, Dnβ 0.123, both-down −12.97%).
  Still the closest to the brief — smallest Dnβ, positive Upβ, decent both-down — but
  return < 7.37% and Dnβ 0.123 > Upβ 0.013. No round 5 or 6 preset dethroned it.
- **Best return (beats AW, no asymmetry):** **RP winner (MinVar)** — 9.94% / Sharpe 0.945,
  Dnβ 0.619 > Upβ 0.406. Unchanged (long-only risk parity).
- **Remaining levers (not yet run):** the property would require a hedge with leading (not
  lagging) downside timing — e.g. a macro/conditional overlay (yield-curve, real-rate, or
  carry-based regime switch) that fires *before* the equity drawdown rather than on a
  sleeve's own lagging trend or a coincident drawdown — or a genuinely short-duration
  *ticker* (e.g. short TLT directly) held *only* in a defined stagflation regime
  identified by an ex-ante macro signal, rather than a sleeve-level trend gate. The
  evidence (32 flavors, every one Upβ < Dnβ) suggests the asymmetric property is very hard
  to achieve with sleeve-level overlays on this universe under a 5.8% leverage cost and a
  lagging/coincident gate.

## 5g. Comparison menu — round 7 (measured, out-of-sample)

Round 7 built the lever §5f named as "remaining": a **leading macro gate** — the overlays
fire off an *ex-ante inflation regime* (trailing-12m Commodities return, a series
**external to the combo**) instead of a sleeve's own lagging trend. The construction is
**regime-conditional and symmetric** (see §3h for the full formula): when inflation is
**rising** (`infl_up`), short equity (`w_hedge`) and/or duration (`w_hedge_bd`) — the
stagflation/2022 both-down regime the round-5/6 lagging gates could only hedge *after* the
drop; when inflation is **falling**, add a *long-duration tilt* (`w_long_bd`) to own the
bonds that rally in flight-to-quality (2008 Q4, 2020 Q1). Five presets span the grid:
duration-short only (`EW-Infl-Dur`), duration-short + long-tilt (`-DurL`, `-DurL2`), and the
full risk-off that **also shorts equity** (`-Both`, `-BothL`). All use the never-flipping
EW base so Upβ stays positive by construction; the overlays are additive. Measured OOS
2018–2026, `--score-mode asymmetric2`, `--ref-mode external`:

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather (ref) | US Equity, US Treasuries, Gold, Commodities | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| RP winner (ref) | US Equity, US REIT, Preferred Stock, US Treasuries, Gold, Silver | 9.94% | **0.945** | -15.98% | -31.91% | 0.406 | 0.619 | 0.708 | 1.00 | 0.00% | — | — |
| EW-MA-Short (r3 best-balance ref) | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 4.25% | 0.613 | -14.02% | -12.97% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | -0.70 | [-0.08, 1.40] |
| EW-Hedge-Dur-MA (r6 best both-down ref) | US Equity, Preferred Stock, US Treasuries, EM Bonds, Commodities | 2.28% | 0.296 | -21.40% | -12.10% | -0.025 | 0.243 | 0.334 | 0.90 | 0.00% | -1.02 | [-0.49, 1.30] |
| **EW-Infl-Dur** | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 6.79% | **0.587** | -24.32% | -30.11% | 0.542 | 0.711 | 0.675 | 0.90 | 0.00% | -0.72 | [0.03, 1.42] |
| **EW-Infl-DurL** | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 7.17% | **0.541** | -28.98% | -34.68% | 0.628 | 0.817 | 0.646 | 0.90 | 0.00% | -0.77 | [-0.00, 1.37] |
| **EW-Infl-DurL2** | US Equity, International Equity, Preferred Stock, EM Bonds, Commodities | 7.30% | **0.526** | -30.53% | -36.21% | 0.656 | 0.853 | 0.636 | 0.90 | 0.00% | -0.78 | [-0.00, 1.36] |
| **EW-Infl-Both** | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | -0.16% | **-0.014** | -22.69% | **-2.69%** | **0.436** | **0.316** | 0.289 | 0.50 | 0.00% | -1.33 | [-0.63, 0.55] |
| **EW-Infl-BothL** | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | 0.22% | **0.017** | -27.42% | **-7.26%** | **0.522** | **0.422** | 0.318 | 0.50 | 0.00% | -1.29 | [-0.56, 0.59] |

**The verdict — round 7 is the first round to achieve Upβ > Dnβ.** After six rounds in
which *every one of 32 flavors* had Upβ < Dnβ, the leading inflation-regime gate finally
flips the sign: **EW-Infl-Both** has Upβ 0.436 > Dnβ 0.316, and **EW-Infl-BothL** has Upβ
0.522 > Dnβ 0.422 — *correlated on the way up, protected on the way down*, the brief's
property, met for the first time. And the protection is excellent: both-down **−2.69%** and
**−7.26%** vs All-Weather's −18.74% — shorting *both* equity and duration when inflation
rises is exactly the 2022-stagflation hedge the round-5/6 lagging gates could not time, and
here it fires off an *ex-ante* signal (Commodities topped before equities in 2022). The
never-flipping EW base keeps Upβ positive (0.436/0.522) because the equity short is an
additive overlay, not a base flip — the round-4b failure mode (short drags through
recoveries) does not recur.

**But the return is gone.** The two property-meeting flavors have Sharpe ≈ 0 and net
return **−0.16% / +0.22%** — they are a *defensive hedge, not a return strategy*. The
inflation-regime risk-off shorts equity and duration in *every* rising-inflation month,
not just drawdowns, so equity-up + inflation-up months (2021, 2024 reflation) take a
drag on both legs with no offsetting crisis alpha. Gross nets down to 0.50 (the shorts
offset the long base), so there is no leverage cost — but there is also no carry left.
This does **not** beat All-Weather's 7.37%; it trades *all* the return for the asymmetric
property. Every DSR is negative (−0.72 to −1.33) and every bootstrap Sharpe CI straddles
zero — none is statistically significant.

**The duration-only presets keep the return but fail the property.** `EW-Infl-Dur`,
`-DurL`, `-DurL2` (no equity short — short duration only when inflation rising) retain
AW-like return (6.79%–7.30%) and Sharpe 0.53–0.59 — *nearly matching All-Weather's 7.37%*.
But they have Upβ < Dnβ (0.54 < 0.71, 0.63 < 0.82, 0.66 < 0.85) and **terrible both-down**
(−30% to −36%, far *worse* than AW's −18.74%). The reason is the **long-duration tilt**
(`w_long_bd`): it is held in *every* disinflation month, not just equity drawdowns, so in
2022–23 — when bonds fell *during* the equity recovery (inflation rolling over but rates
still climbing) — the 1.5–2.0× long-bond weight compounded the loss. The symmetric
regime switch that should have produced flight-to-quality gains instead stacked a
duration bull-blear into a bond bear. The bigger the tilt (DurL2 → 2.0×), the worse the
both-down (−36%). So round 7 splits the brief cleanly in two: **the equity-short leg
delivers the asymmetry property but kills the return; the duration-only leg keeps the
return but fails the asymmetry property.** No single round-7 preset has both.

**Structural reason (the round-7 update):** a *leading* ex-ante macro gate *does* solve the
timing problem that defeated rounds 2–6 — it fires before the drop, not 12m after, so it
can short into the both-down regime without dragging the short through recoveries (Upβ
stays positive). The cost is that an ex-ante regime gate is *broad* (it is on in every
rising-inflation month, drawdown or not), so the hedge that protects the asymmetric
property also bleeds return in non-crisis reflation months. The brief's two requirements —
*beat 7.37%* AND *Upβ > Dnβ* — remain in tension: the only construction on this universe
that delivers Upβ > Dnβ (short both legs on a leading macro signal) gives back the return
in the non-crisis months the same signal keeps it short. A narrower trigger (short only
when inflation rising *and* equity already rolling over — leading macro AND a coincident
confirmation) is the next lever; round 7 did not build it.

### Top picks (round 7 — the menu updated)

- **First flavor in seven rounds to meet the asymmetry property:** **EW-Infl-Both** —
  Upβ **0.436** > Dnβ **0.316**, both-down **−2.69%** (best of the entire investigation,
  vs AW −18.74%), Dn-corr 0.289. The brief's "correlated up, not down" is literally
  satisfied. But net −0.16% / Sharpe −0.014 — it hedges, it does not grow. Use as a
  *defensive sleeve*, not a standalone return strategy.
- **Asymmetry property + slightly less both-down, still ~0 return:** **EW-Infl-BothL** —
  Upβ 0.522 > Dnβ 0.422, both-down −7.26%, net 0.22% / Sharpe 0.017. The long-duration
  tilt in disinflation adds a little flight-to-quality carry but not enough to rescue
  the return; the asymmetry gap (0.10) is the widest of the family.
- **Round-7's answer to "keep the return":** **EW-Infl-Dur** — 6.79% / Sharpe 0.587,
  *within 0.6pt of All-Weather's 7.37%*, gross 0.90 (no leverage cost), DSR −0.72. The
  leading inflation gate on duration only (no equity short) preserves return — but
  Upβ 0.542 < Dnβ 0.711 and both-down −30.11%, so the property is failed. The
  *return*-goal's best round-7 flavor; the *asymmetry*-goal's worst.
- **Best-balance flavor across ALL seven rounds is STILL a round-3 flavor:** **EW-MA-Short**
  (4.25% / Sharpe 0.613, Upβ 0.013, Dnβ 0.123, both-down −12.97%). Round 7 did not dethrone
  it — round 7's flavors are either (property, ~0 return) or (return, no property), while
  EW-MA-Short sits at the moderate middle. It remains the closest single flavor to the
  brief, but still return < 7.37% and Dnβ 0.123 > Upβ 0.013 (property not met).
- **Best return (beats AW, no asymmetry):** **RP winner (MinVar)** — 9.94% / Sharpe 0.945,
  Dnβ 0.619 > Upβ 0.406. Unchanged (long-only risk parity).

### Opt-in / regression verification (round 7)

The round-7 code paths are gated behind `gate_signal="infl_regime"` (only the five
`EW-Infl-*` presets set it) and the new `w_long_bd` / `w_hedge_bd` / `w_hedge` knobs (all
default 0 in the 32 pre-existing presets, which keep their own `gate_signal`). Verified
two ways:

1. **Regression guard** (`--ref-mode sleeves --schemes EW,InvVol,InvVar,ERC,MinVar`,
   default score — no TrendProtect flavors, no asymmetric score): the COV-only core-scheme
   run completes exit 0 with no crash on the new code paths.
2. **Shared-scheme §10 diff (asym7 vs asym6, same args):** of the 29 pre-round-7 schemes
   present in both reports, **26 are byte-for-byte identical** (same TRAIN-best combo *and*
   same metrics) — e.g. All-Weather, RP winner, TrendGate, TG-Short, EW-MA-Short, EW-Short,
   EW-Hedge-DD/DMA/DMA-1/Dur/Dur-2/Dur-DD/Dur-DD2/Dur-MA/MA, EW-AsymMA-Short/-6/-9, EW-Vol/DMA/DDStop-Short,
   LS-TSMOM, TG-Short-6m/-LS. The 3 that differ — **EW-AsymMA-Tight, EW-Hedge-DMA-2,
   EW-Short-LS** — each changed their *TRAIN-best combo* (not their engine output): because
   `asymmetric2` is a *relative percentile-rank* score across all schemes, expanding the
   pool 32 → 37 schemes shifts the percentile landscape, so schemes near a score boundary
   select a different TRAIN-best combo. The per-(scheme, combo) engine output is unchanged
   (the 26 identical rows prove the engine is byte-identical); only the argmax over combos
   moved for those 3. This is the expected, benign effect — **zero engine-output
   regressions** from the round-7 additions.

Reproduce: `.venv/bin/python risk_parity_eval.py --score-mode asymmetric2` →
[`output/risk_parity_eval_asym7/report_eval.md`](../output/risk_parity_eval_asym7/report_eval.md)
(37 schemes, 104229 = 2817×37 TRAIN trials).

## 5h. Comparison menu — round 8 (measured, out-of-sample)

Round 8 built the single lever §5g named as "remaining": **narrow WHEN the leading
inflation gate fires** without touching the ex-ante macro signal itself. A coincident
**equity-rolling confirmation** (`infl_confirm="eq_neg"` — true when the external US Equity
proxy has a negative trailing-3m return) is AND-gated onto the round-7 regime: the short
legs fire only when `infl_up AND eq_rolling` (inflation rising *and* equity already rolling
over — 2022, not 2021/2024), and the long-duration tilt fires only when
`(NOT infl_up) AND eq_rolling` (disinflation *and* equity falling — true flight-to-quality
2008 Q4 / 2020 Q1, not 2022–23 disinflation-with-bonds-falling). See §3i for the full
formula. Five presets span the round-7 grid with the confirmation layered on. Measured OOS
2018–2026, `--score-mode asymmetric2`, `--ref-mode external`:

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather (ref) | US Equity, US Treasuries, Gold, Commodities | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| EW-Infl-Both (r7 ref, broad gate) | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | -0.16% | **-0.014** | -22.69% | **-2.69%** | **0.436** | **0.316** | 0.289 | 0.50 | 0.00% | -1.33 | [-0.63, 0.55] |
| EW-Infl-BothL (r7 ref, broad gate) | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | 0.22% | **0.017** | -27.42% | **-7.26%** | **0.522** | **0.422** | 0.318 | 0.50 | 0.00% | -1.29 | [-0.56, 0.59] |
| **EW-InflC-Both** | US Equity, International Equity, US REIT, EM Bonds, Commodities | 5.41% | **0.430** | -25.74% | -26.10% | 0.360 | 0.563 | 0.449 | 1.00 | 0.00% | -0.88 | [-0.13, 1.25] |
| **EW-InflC-BothL** | US Equity, International Equity, US REIT, EM Bonds, Commodities | 5.97% | **0.427** | -30.01% | -28.44% | 0.427 | 0.680 | 0.468 | 1.00 | 0.00% | -0.88 | [-0.11, 1.28] |
| **EW-InflC-Dur** | US Equity, International Equity, US Corporate Bonds, EM Bonds, Commodities | 7.30% | **0.671** | -21.91% | -29.20% | 0.461 | 0.646 | 0.648 | 1.00 | 0.00% | -0.64 | [0.11, 1.57] |
| **EW-InflC-DurL** | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 7.28% | **0.606** | -26.20% | -28.93% | 0.526 | 0.747 | 0.600 | 1.00 | 0.00% | -0.71 | [0.09, 1.53] |
| **EW-InflC-Both6** | US Equity, International Equity, US REIT, EM Bonds, Commodities | **8.38%** | **0.652** | -25.74% | -29.64% | 0.466 | 0.655 | 0.538 | 1.00 | 0.00% | -0.66 | [0.08, 1.50] |

**The verdict — round 8 solved the return half but broke the asymmetry half.** The
round-7 verdict prescribed "narrow the gate to fire only when inflation rising *and* equity
already rolling over" to keep the asymmetry with return. Round 8 built exactly that — and
the **return half worked**: the confirmation gate stopped shorting in 2021/2024 reflation
rallies (inflation up but equity *not* rolling → `eq_rolling` false → no short), so the
carry came back. **EW-InflC-Both** rose from round-7 **EW-Infl-Both's −0.16% to 5.41%**, and
**EW-InflC-Both6** (the slower 6m confirmation) reaches **8.38% — the first inflation-gate
flavor to beat All-Weather's 7.37% on net return.** **EW-InflC-Dur** at 7.30% / Sharpe 0.671
is the highest-Sharpe inflation-gate flavor of any round, and the first with a **positive
bootstrap-CI lower bound** ([0.11, 1.57]) — joined by EW-InflC-DurL [0.09, 1.53] and
EW-InflC-Both6 [0.08, 1.50].

**But the asymmetry half broke.** All five round-8 flavors have **Upβ < Dnβ**
(0.360<0.563, 0.427<0.680, 0.461<0.646, 0.526<0.747, 0.466<0.655) — the property,
achieved for the first time in round 7, is **lost** when the gate is narrowed. The
mechanism is the mirror image of round 7: the round-7 *broad* gate shorted in *every*
rising-inflation month, which capped **both** Upβ and Dnβ — but capped Dnβ *more* (because
the 2022 equity-down months were a subset of rising-inflation months and got shorted), so
Upβ > Dnβ emerged. That same broadness was what bled the return. Round 8 removed the bleed
(no short in 2021/2024 up-months) → return restored → but the confirmation only fires
**after** equity is already rolling over (a coincident 3m signal) **and** only in
inflation-up months, so the many equity-down months that are *not* inflation-up (2018 Q4,
2025 pullbacks, etc.) are **not** hedged, and Dnβ rises back above Upβ. The broadness that
delivered the asymmetry is the same broadness that bled the return — narrowing one fixes
the other and breaks the first.

**The two round-7 broad-gate flavors are unchanged and still the only property-meeting
flavors.** Because `infl_confirm` defaults to `""`, EW-Infl-Both and EW-Infl-BothL are
**byte-identical** in the round-8 report (−0.16% / 0.436>0.316 and 0.22% / 0.522>0.422,
same combos, same metrics — verified in the opt-in diff below). After eight rounds and 42
TrendProtect flavors, **the asymmetry property is still met only by those two**, and they
still have Sharpe ≈ 0. Round 8 traded round 7's "(property, ~0 return)" for "(return, no
property)" — the asymmetry tool and the return tool are two different tools for two
different circumstances, and round 8 marks where they diverge.

**A return win without the property.** EW-InflC-Both6 at 8.38% beats All-Weather on net
return — but with Dnβ 0.655 > Upβ 0.466, Dn-corr 0.538, and both-down **−29.64%** (far
*worse* than AW's −18.74%), it is *more* correlated to equities on the way down, the
opposite of the brief. It is a reflation-timing return strategy, not a "correlated up,
protected down" strategy. The same is true of EW-InflC-Dur / -DurL (both-down −29.20% /
−28.93%, worse than AW) — the gated long-tilt did NOT recover the round-7 duration-only
both-down bleed (the 3m confirmation still lets the tilt fire in some 2022–23
disinflation months where bonds kept falling).

**Structural reason (the round-8 update):** the asymmetry tool and the return tool are in
**fundamental tension on this universe**, now characterized from both directions. The
asymmetry requires a hedge that is **broad enough to cover most equity-down months** (so
Dnβ is capped below Upβ); but a hedge that broad necessarily shorts in non-crisis up-months
too, bleeding the return. A **narrow** hedge (only confirmed roll-overs) preserves the return
but covers too few down-months to keep Dnβ < Upβ. There is no free lunch in the gate width:
width buys asymmetry and costs return; narrowness buys return and costs asymmetry. Round 7
found the width end (the asymmetry tool); round 8 found the narrow end (the return tool).
Bridging them would require a hedge that is *broad in down-months and absent in up-months*
— i.e. a gate that is itself asymmetric (fires on equity-down regardless of inflation, but
never on equity-up) — which is precisely the round-4b hysteretic price-gate family that
drove Upβ negative (it flipped the base, dragging the short through recoveries). The
never-flip additive-overlay construction (rounds 5–8) avoids that Upβ drag but cannot make
the overlay broad-in-down / absent-in-up without either bleeding return (broad) or missing
down-months (narrow). This is the fifth structural finding.

### Top picks (round 8 — the menu updated)

- **First inflation-gate flavor to beat All-Weather on return:** **EW-InflC-Both6** —
  8.38% / Sharpe 0.652 (vs AW 7.37% / 1.055), gross 1.00 (no leverage cost), DSR −0.66, CI
  [0.08, 1.50]. The 6m equity-rolling confirmation is the most stable confirmation window.
  **But** Upβ 0.466 < Dnβ 0.655 and both-down −29.64% (worse than AW) — return win, property
  lost; more correlated down, not less.
- **Highest-Sharpe inflation-gate flavor + first positive CI lower bound:** **EW-InflC-Dur**
  — 7.30% / Sharpe 0.671, CI [0.11, 1.57], gross 1.00, DSR −0.64. The confirmed
  duration-only short (no equity short) keeps return within 0.1pt of AW and is the only
  inflation-gate flavor whose bootstrap CI lower bound is positive. **But** Upβ 0.461 <
  Dnβ 0.646 and both-down −29.20% (worse than AW) — property failed; the gated long-tilt did
  not recover the round-7 duration-only both-down bleed.
- **The property is STILL met only by the two round-7 broad-gate flavors:** **EW-Infl-Both**
  (−0.16%, Upβ 0.436 > Dnβ 0.316, both-down −2.69% — best of all 42) and **EW-Infl-BothL**
  (0.22%, Upβ 0.522 > Dnβ 0.422, both-down −7.26%). Both byte-identical in round 8. Use as
  a *defensive sleeve*, not a return strategy.
- **Best-balance flavor across ALL eight rounds is STILL a round-3 flavor:** **EW-MA-Short**
  (4.25% / Sharpe 0.613, Upβ 0.013, Dnβ 0.123, both-down −12.97%) — unchanged, still the
  closest single flavor to the brief with positive return (no round 5/6/7/8 preset
  dethroned it on the combined return+property view; round 8 beats it on return alone but
  loses on the property).
- **Best return (beats AW, no asymmetry):** **RP winner (MinVar)** — 8.43% / Sharpe 0.609
  in the round-8 measure (the score-pool expansion 37→42 shifted its TRAIN-best combo from
  the round-7 9.94% 6-sleeve combo to a 5-sleeve combo; the MinVar engine on a given combo
  is unchanged — see opt-in below). Dnβ 0.937 > Upβ 0.625.

### Opt-in / regression verification (round 8)

The round-8 code paths are gated behind `infl_confirm="eq_neg"` (only the five `EW-InflC-*`
presets set it; the 37 pre-round-8 presets keep `infl_confirm=""`). Verified three ways:

1. **Regression guard** (`--ref-mode sleeves --schemes EW,InvVol,InvVar,ERC,MinVar`,
   default score — no TrendProtect, no asymmetric score):
   [`output/rp_reg8/report_eval.md`](../output/rp_reg8/report_eval.md) — the COV-only
   core-scheme run completes exit 0, no crash on the new code paths.
2. **`py_compile` + import:** `risk_parity_eval.py` compiles; `import risk_parity_eval`
   succeeds with `SCHEME_ORDER` length 45 and all five `EW-InflC-*` presets present.
3. **Shared-scheme §10 diff (asym8 vs asym7, same args):** of the 34 pre-round-8 schemes
   present in both reports' §10 menus, **29 are byte-for-byte identical** (same TRAIN-best
   combo *and* same metrics) — including **EW-Infl-Both and EW-Infl-BothL**, the two
   round-7 broad-gate flavors, proving the `infl_confirm` default-off path is byte-identical
   to round 7. The 5 that differ — **RP winner, TG-Short, EW-AsymMA-Tight, EW-Infl-DurL2,
   EW-AsymVol-Short** — each changed their *TRAIN-best combo* (not their engine output):
   `asymmetric2` is a *relative percentile-rank* score across all schemes, so expanding the
   pool 37 → 42 schemes shifts the percentile landscape and schemes near a score boundary
   select a different TRAIN-best combo (e.g. the RP winner moved from its round-7 9.94%
   6-sleeve combo to an 8.43% 5-sleeve combo — the MinVar engine on a given combo is
   unchanged, only the argmax moved). The per-(scheme, combo) engine output is unchanged
   (the 29 identical rows prove the engine is byte-identical); only the argmax over combos
   moved for those 5. This is the expected, benign effect — **zero engine-output
   regressions** from the round-8 additions.

Reproduce: `.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
--rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym8` →
[`output/risk_parity_eval_asym8/report_eval.md`](../output/risk_parity_eval_asym8/report_eval.md)
(42 schemes, 118 314 = 2817×42 TRAIN trials).

---

## 5i. Comparison menu — round 9 (measured, out-of-sample)

Round 9 changed the primitive entirely. Rounds 1–8 all *timed a short* (flipped the base,
gated a sleeve to cash/short, or added an additive short overlay). Round 9 keeps a
**never-flip long EW base** and instead **scales gross** by a per-month scalar `s_t ∈
[0.3, 1.5]`: `pos_t = s_t · base_w`, long-only, `gross_t = s_t`, leverage cost
`max(0, s_t − 1) · lev_rate/12` when `s_t > 1`. This is the most theoretically direct
construction for "correlated up, protected down" — own *more* in up-months, *less* in
down-months, no short to time, leverage explicitly allowed. See §3j for the full formula.
Three scalar signals were tried: `eq_mom` (momentum-gated leverage, `s = clip(1 + k·eq_mom,
fl, ce)`), `eq_vol` (vol-targeting à la Moreira-Muir, `s = clip(σ_tgt/σ_realized, fl, ce)`),
and `infl_regime` (the round-7 leading inflation gate reused as a scalar). Five presets
span the scalar-signal × lookback × leverage grid. Measured OOS 2018–2026,
`--score-mode asymmetric2`, `--ref-mode external`:

| Portfolio | Combo | Ann ret | Sharpe | MaxDD | Both-down | Upβ | Dnβ | Dn-corr | Gross | Lev/yr | DSR | Sharpe CI |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All-Weather (ref) | US Equity, US Treasuries, Gold, Commodities | 7.37% | **1.055** | -12.31% | -18.74% | 0.327 | 0.475 | 0.793 | 1.00 | 0.00% | — | — |
| EW-Infl-Both (r7 ref, broad gate) | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | -0.16% | **-0.014** | -22.69% | **-2.69%** | **0.436** | **0.316** | 0.289 | 0.50 | 0.00% | -1.33 | [-0.63, 0.55] |
| EW-Infl-BothL (r7 ref, broad gate) | US Equity, International Equity, US REIT, Preferred Stock, EM Bonds | 0.22% | **0.017** | -27.42% | **-7.26%** | **0.522** | **0.422** | 0.318 | 0.50 | 0.00% | -1.29 | [-0.56, 0.59] |
| **EW-Scale-Mom** | US Equity, International Equity, US REIT, US Corporate Bonds, Commodities | 7.91% | **0.616** | -22.61% | -40.90% | 0.507 | 0.787 | 0.728 | 1.30 | 1.76% | -0.69 | [0.03, 1.46] |
| **EW-Scale-Mom6** | US Equity, International Equity, Preferred Stock, US Corporate Bonds, Silver | **8.50%** | **0.609** | -22.88% | -46.50% | 0.427 | 0.651 | 0.594 | 1.27 | 1.56% | -0.70 | [-0.02, 1.34] |
| **EW-Scale-Vol** | US Equity, International Equity, US REIT, Preferred Stock, US Corporate Bonds | 3.04% | **0.280** | -18.55% | -42.53% | 0.468 | 0.706 | 0.726 | 0.74 | 0.00% | -1.03 | [-0.24, 0.96] |
| **EW-Scale-MomL** | US Equity, International Equity, Preferred Stock, US Corporate Bonds, Silver | 8.05% | **0.578** | -23.11% | -45.78% | 0.364 | 0.558 | 0.548 | 1.45 | 2.64% | -0.73 | [-0.06, 1.28] |
| **EW-Scale-Infl** | US Equity, International Equity, Preferred Stock, US Corporate Bonds, Commodities | 7.04% | **0.587** | -26.63% | -24.72% | 0.563 | 0.785 | 0.664 | 0.40 | 0.00% | -0.72 | [0.05, 1.42] |
| EW-MA-Short (r3 best balance) | US Equity, Preferred Stock, US Corporate Bonds, EM Bonds, Commodities | 4.25% | 0.613 | -14.02% | -12.97% | 0.013 | 0.123 | 0.224 | 1.00 | 0.00% | -0.70 | [-0.08, 1.40] |

**The verdict — round 9 met the return half again but REVERSED the asymmetry.** The
scaling primitive is the most theoretically direct construction for "correlated up,
protected down": long-only (no short to time), own more up / less down, leverage explicitly
allowed. The **return half worked** — **EW-Scale-Mom6** at **8.50%** and **EW-Scale-MomL**
at 8.05% both beat All-Weather's 7.37% (after the 5.8%/yr leverage cost), and EW-Scale-Mom
(7.91%) and EW-Scale-Infl (7.04%) essentially match it. Three of the five also have a
**positive or near-zero bootstrap-CI lower bound** (EW-Scale-Mom [0.03, 1.46],
EW-Scale-Infl [0.05, 1.42], EW-Scale-Mom6 [−0.02, 1.34]) — the scaled-gross family is the
second family (after round-8's confirmation-gate duration family) to clear that bar.

**But the asymmetry half reversed.** All five round-9 flavors have **Dnβ > Upβ**
(0.507<0.787, 0.427<0.651, 0.468<0.706, 0.364<0.558, 0.563<0.785) — the opposite of the
brief. The mechanism is the **lag problem, now on the gross leg**: every available scalar
(momentum, vol, inflation) **lags**, so `s_t` is HIGH at the *start* of a drawdown (momentum
still positive from the prior rally → the portfolio is *leveraged into* the drop → Dnβ
amplified) and LOW at the *start* of a rally (momentum still negative from the prior drop
→ the portfolio is *de-risked into* the rebound → Upβ damped) — exactly backwards. The
both-down numbers tell the story brutally: the momentum scalars (EW-Scale-Mom/Mom6/MomL)
show both-down of **−40.9% / −46.5% / −45.8%** — *worse than All-Weather's −18.74%* and
*worse than the un-leveraged EW base* — because they carried full-or-leveraged gross
*into* the 2022 both-down. Only EW-Scale-Infl (the leading inflation scalar, which de-risks
*before* the drop) gets both-down back near AW (−24.72%) — but it too has Dnβ 0.785 >
Upβ 0.563, because it is also de-risked *into* the rebound.

**Scaling does not create asymmetry; it amplifies the scalar's lead/lag.** The theory
("own more up, less down → Upβ > Dnβ by construction") assumes `s_t` is *contemporaneous*
with the equity return — high *in* up-months, low *in* down-months. No ex-ante scalar is:
momentum is trailing, vol is trailing, even the inflation regime lags the turn by months.
A contemporaneous scalar would be the equity return itself — usable in hindsight, not
ex-ante. So a lagging scalar gives Dnβ > Upβ (leveraged into drawdowns, de-risked into
rallies), a *leading* scalar (none found on this universe) would give Upβ > Dnβ, and the
round-9 family lands on the lagging side. This is the **sixth structural finding**: the
scaling primitive's asymmetry is set by the scalar's **lead/lag**, not by the scaling
itself, and every available scalar lags. It generalizes the round-3/4b blocker — the lag
problem is fundamental to any price/regime signal, whether it gates a *short* (rounds 2–8)
or scales *gross* (round 9).

**The two round-7 broad-gate flavors are STILL the only property-meeting flavors.**
Because `scale_signal` defaults to `""` (scale off, `s_t = 1.0`, `pos_t = base_w`), every
pre-round-9 preset is byte-identical in round 9. **EW-Infl-Both** (−0.16%, Upβ 0.436 >
Dnβ 0.316) and **EW-Infl-BothL** (0.22%, Upβ 0.522 > Dnβ 0.422) are unchanged (verified in
the opt-in diff below) — still the only two flavors in nine rounds with Upβ > Dnβ, still
Sharpe ≈ 0. After nine rounds and 47 TrendProtect flavors, the asymmetry tool (round 7,
broad gate) and the return tool (round 8 narrow gate, round 9 scaled gross) remain distinct
tools: *timing a short* with a broad gate gives the property at ~0 return; a narrow gate
gives return without the property; and *scaling gross* with a lagging scalar gives return
with the asymmetry **reversed** — three primitives, three circumstances, one toolkit.

### Top picks (round 9 — the menu updated)

- **Best return via scaled-gross (beats AW):** **EW-Scale-Mom6** — 8.50% / Sharpe 0.609
  (vs AW 7.37% / 1.055), gross 1.27, lev cost 1.56%/yr, DSR −0.70, CI [−0.02, 1.34]. The
  slower 6m momentum window is smoother than the 3m (less whipsaw in `s_t`). **But**
  Upβ 0.427 < Dnβ 0.651, both-down −46.50% (far worse than AW) — return win, asymmetry
  **reversed**; leveraged into the 2022 both-down.
- **Most aggressive scaled-gross (beats AW, 2× ceiling):** **EW-Scale-MomL** — 8.05% /
  Sharpe 0.578, gross 1.45, lev cost 2.64%/yr, CI [−0.06, 1.28]. The `scale_k=3, ceil=2.0`
  preset owns up to 2.0× in strong up-months. **But** Upβ 0.364 < Dnβ 0.558, both-down
  −45.78% — return win at the cost of the worst both-down of the return-beaters.
- **Only scaled-gross flavor with near-AW both-down:** **EW-Scale-Infl** — 7.04% /
  Sharpe 0.587, gross 0.40 (mostly de-risked, no leverage cost), CI [0.05, 1.42]. The
  *leading* inflation scalar de-risks *before* the drop, so both-down −24.72% is the only
  round-9 flavor not catastrophically worse than AW on both-down. **But** Upβ 0.563 <
  Dnβ 0.785 — still reversed, because it is also de-risked *into* the rebound; and return
  7.04% is just below AW.
- **Vol-targeting scalar underperformed:** **EW-Scale-Vol** — 3.04% / Sharpe 0.280, gross
  0.74. The Moreira-Muir vol-target (`s = σ_tgt/σ_realized`) was the *worst* of the three
  scalars on return: realized vol is high *after* drawdowns (so `s` is low → de-risked at
  the bottom) and low *after* rallies (so `s` is high → leveraged at the top) — the same
  lag, and the target (12%) kept gross below 1 most of the time, forfeiting the leverage
  the round was built to use. Confirms the lag finding on a second scalar.
- **The property is STILL met only by the two round-7 broad-gate flavors:** **EW-Infl-Both**
  (−0.16%, Upβ 0.436 > Dnβ 0.316, both-down −2.69% — best of all 47) and **EW-Infl-BothL**
  (0.22%, Upβ 0.522 > Dnβ 0.422, both-down −7.26%). Both byte-identical in round 9. Use as
  a *defensive sleeve*, not a return strategy.
- **Best-balance flavor across ALL nine rounds is STILL a round-3 flavor:** **EW-MA-Short**
  (4.25% / Sharpe 0.613, Upβ 0.013, Dnβ 0.123, both-down −12.97%) — unchanged, still the
  closest single flavor to the brief with positive return. No round 5/6/7/8/9 preset
  dethroned it on the combined return+property view: the round-9 scaled-gross flavors beat
  it on return alone but **reverse** the property (Dnβ > Upβ).

### Opt-in / regression verification (round 9)

The round-9 code paths are gated behind `scale_signal` (only the five `EW-Scale-*`
presets set it; the 42 pre-round-9 presets keep `scale_signal=""` → `s_t = 1.0` →
`pos_t = base_w` byte-identical). Verified three ways:

1. **`py_compile` + import:** `risk_parity_eval.py` compiles; `import risk_parity_eval`
   succeeds with `SCHEME_ORDER` length 50 and all five `EW-Scale-*` presets present.
2. **Shared-scheme §10 diff (asym9 vs asym8, same args):** of the 42 pre-round-9 schemes
   present in both reports' §10 menus, **39 are byte-for-byte identical** (same TRAIN-best
   combo *and* same metrics) — including **EW-Infl-Both and EW-Infl-BothL**, the two
   property-meeting flavors, proving the `scale_signal=""` default-off path is
   byte-identical to round 8. The 3 that differ — **EW-AsymMA-Short-6, EW-AsymMA-Short-9,
   EW-AsymVol-Short** — each changed their *TRAIN-best combo* (not their engine output):
   `asymmetric2` is a *relative percentile-rank* score across all schemes, so expanding
   the pool 42 → 50 shifts the percentile landscape and schemes near a score boundary
   select a different TRAIN-best combo. The per-(scheme, combo) engine output is
   unchanged (the 39 identical rows prove the engine is byte-identical); only the argmax
   over combos moved for those 3. **Zero engine-output regressions** from the round-9
   additions, and the 2 property-meeting flavors are stable across the pool expansion —
   strong evidence the engine is truly opt-in.

Reproduce: `.venv/bin/python risk_parity_eval.py --score-mode asymmetric2 \
--rolling-schemes EW,MinVar,LS-TSMOM --bootstrap 2000 --out-dir output/risk_parity_eval_asym9` →
[`output/risk_parity_eval_asym9/report_eval.md`](../output/risk_parity_eval_asym9/report_eval.md)
(50 schemes, 140 850 = 2817×50 TRAIN trials).

*Research / illustration only. Not investment advice.*