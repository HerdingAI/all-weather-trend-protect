# Is a factor sleeve a third uncorrelated return source?

Generated 2026-08-01 by `factor_axis_test.py` and `compare_candidates.py`.
Supersedes nothing; extends `report.md`.

## The question

Not "is DFA a good manager", and not "how much small value should we hold".
The question asked was:

> does having uncorrelated sources of return help us — in the same way gold and
> long duration are non-correlated sources of return?

Gold and long Treasuries earned their place by a measured property: they protect
on different crisis axes, so each covers the other's failure. This asks whether a
small-value sleeve clears **the same bar**.

## Answer

**No — it is not a third protective axis. It is a diversifying return sleeve,
and at the drawdown ceilings that matter it is roughly a wash.**

The two halves of that split matter separately, because they point opposite ways.

### It IS partially independent at regime frequency

36-month overlapping windows, excess vs the market, 1993-03..2026-07:

```
correlation between the excess series
                gold   duration   smallval
  gold         1.000      0.646      0.404
  duration     0.646      1.000      0.376
  smallval     0.404      0.376      1.000
```

Small value's excess is **less** correlated with gold (0.404) and duration
(0.376) than gold and duration are with each other (0.646). On this lens it is
not a market clone.

> **A correction, because the first version of this test was wrong.** The rule
> was originally written with an absolute bar of |corr| < 0.30. Running it
> showed that bar rejects gold and duration themselves — the very pair it was
> meant to describe. The cause is mechanical: every excess series shares a
> `-market` term, so when the market falls, everything-not-market looks good at
> once. Raw gold and duration correlate 0.192; their *excesses* correlate 0.646.
> The rule is now calibrated against the gold/duration pair as a control, the
> same device as GLD/IAU for "what agreement looks like". That recalibration
> flipped small value from FAIL to PASS on this criterion.

### It AMPLIFIES the tail the ladder constrains

Worst decile of market months (n=41, market −7.70%/mo):

| sleeve | corr | mean/mo | months up |
|---|---:|---:|---:|
| Gold | +0.332 | **+0.99%** | 56% |
| Long Treasuries | −0.004 | **+1.64%** | 61% |
| Small value | +0.749 | **−8.40%** | **2%** |
| Micro cap | +0.791 | −8.25% | 5% |

Gold and duration *offset*. Small value falls **harder than the market itself**
and was up in 1 month of 41. Whatever it is, it is not a hedge.

Also `corr(smallval, microcap) = 0.952` — micro cap and small value are one
decision, not two. DFSCX adds nothing DFSVX does not.

## What it does to the actual books

Grid declared in `candidates.py` before running: small value substituted for US
equity at 10/20/30% of the sleeve, gold and duration weights held fixed.
1998-06..2026-07, annually rebalanced, net of costs.

| book | CAGR | maxDD | **Sortino** | underwtr | worst 10y |
|---|---:|---:|---:|---:|---:|
| 50/25/25 eq-gold-dur | 8.77% | −22.62% | **1.52** | 3.0y | 4.83% |
| 50/25/25 +10% SV | 8.82% | −22.31% | 1.51 | 2.7y | 5.22% |
| 50/25/25 +20% SV | 8.87% | −22.01% | 1.51 | 2.7y | 5.60% |
| 50/25/25 +30% SV | 8.91% | **−21.69%** | 1.50 | **2.2y** | **5.94%** |
| 60/20/20 eq-gold-dur | 8.93% | −24.47% | **1.41** | 3.2y | 3.52% |
| 60/20/20 +30% SV | 9.09% | −24.79% | 1.38 | 2.7y | 4.78% |
| 80/20 VTI-GLD | 9.65% | −38.29% | 1.19 | 4.2y | 0.94% |
| 80/20 VTI-GLD +7% SV | 9.72% | −38.43% | 1.18 | 4.1y | 1.44% |

Reading this honestly: **Sortino, the stated objective, does not improve.** It
declines 0.02 at every rung — a move far inside this study's noise. Drawdown,
time underwater and worst-10y all improve modestly. Nothing here is decisive in
either direction.

**Your current 7% tilt does nothing measurable.** 9.72% vs 9.65% CAGR, −38.43%
vs −38.29% drawdown, Sortino 1.18 vs 1.19. It is neither helping nor hurting.

## The number that looks best is the one we trust least

| book | dot-com | GFC | COVID | 2022 |
|---|---:|---:|---:|---:|
| 50/25/25 eq-gold-dur | −7.4% | −14.7% | −4.8% | −21.0% |
| 50/25/25 +30% SV | **+1.1%** | −15.0% | −6.8% | −19.6% |

The 8.5-point dot-com improvement is the strongest result in this report, and it
is **measured on a truncated window**. The panel's `US Small Value` sleeve starts
1998-06, so this counts the unwind and **excludes the run-up**. On the full DFSVX
series:

```
run-up     1995-01..2000-02   small value +135.1%   S&P +226.3%   LAGS 91pp
unwind     2000-03..2002-09   small value   +5.2%   S&P  -38.3%
round trip 1995-01..2002-09   small value +147.2%   S&P +101.2%   wins 46pp
```

Small value did not dodge the bubble for free. It gave up 91 points of
participation to avoid 43. The table above shows the payoff and hides the price.

**The truncation cannot be fixed.** DFSVX would extend the sleeve to 1993-03, but
it **fails the panel's seam check** — mean gap 1.154pp/yr against a 1.00 bar
(TE/vol 0.254 passes). It is a different fund, not another wrapper on the same
asset, and splicing it would shift the sleeve's level.

> **Second correction.** Two earlier messages reported DFSVX as *passing* this
> check "1.15 vs a 1.50 limit". The panel's real bar is 1.00/0.30; the validator
> had its own stale copy reading 1.50/0.35. Duplicated constants drift, and this
> copy was wrong in the permissive direction — it would have authorised a splice
> the panel is designed to refuse. `validate_dfsvx_series.py` now imports the
> constants from `build_study_panel` instead of restating them.

## What this means for the goal

The objective is Sortino subject to a drawdown ceiling. Small value:

- **does not help the ceiling** — it amplifies the tail that sets it;
- **does not improve Sortino** — 0.02 worse at every rung, i.e. flat;
- **does add return** (+0.14pp at 50/25/25, +0.16pp at 60/20/20) and improves
  worst-10y and time-underwater;
- **costs 5+ years of tracking error** when the cycle runs against it, which is
  exactly the tolerance you said you have.

So it is defensible but not compelling. The gold-and-duration pair remains the
structure doing the work; small value rides alongside it rather than adding a
third leg. If you want it, 10-30% of the equity sleeve is a reasonable range and
the choice inside that range barely matters. If you leave the books alone, you
give up almost nothing.

## Limitations

- **Investability gap.** The 33-year evidence is DFSVX, which is advisor-gated
  and which you cannot buy. Buyable equivalents (`DFSV`, `AVUV`) have 4-6 years;
  `VBR` is buyable with history to 1998 and is what the panel actually models.
- **Survivorship.** DFSVX and DFSCX both still exist in 2026. Funds that closed
  are absent, biasing measured factor returns upward by an unquantified amount.
- **One cycle.** The dot-com round trip is a single observation. The premium has
  since flipped sign: `+4.01pp` 1998-2009, `−2.52pp` 2010-2026.
- **The manager question is separate and weaker.** DFSVX beat VISVX by
  +0.81pp/yr, t=1.18 — not significant. The DFUS implementation edge (Q2,
  +0.66pp REIT-adjusted, t=2.11) rests on one 5-year post-hoc window.
- The 1998-06 start excludes the run-up, as set out above. This is the binding
  limitation on everything in the book-comparison section.

---

# Addendum: the exhaustive sweep, and the answer to the original question

Generated by `frontier_sweep.py` and `frontier_walkforward.py`.

Everything before this compared a handful of *declared* books. That was the
right response to walk-forward, but it left the original question open: we never
established what was ACHIEVABLE, so we never knew whether those books were near
the frontier or nowhere near it. This closes that.

## The sweep

Every long-only combination of the panel's 11 fully-covered exposures at 5%
granularity with up to 5 sleeves — **2,139,753 portfolios**, 1998-06..2026-07,
net of 10bps/side. ("Every combination" is infinite for continuous weights; the
grid and the sleeve cap are the stated approximation.)

| book | CAGR | maxDD | Sortino | best Sortino at same DD | percentile |
|---|---:|---:|---:|---:|---:|
| 50/25/25 eq-gold-dur | 8.74% | −22.25% | 1.49 | 1.84 | **98.9th** |
| 60/20/20 eq-gold-dur | 8.90% | −28.40% | 1.38 | 1.84 | 96.4th |
| 80/20 VTI-GLD | 9.67% | −40.56% | 1.18 | 1.84 | 84.4th |
| Current allocation | — | — | — | 1.84 | ~72nd |

Two problems with the frontier itself, both visible before any validation:

- **Maximising Sortino alone gives a useless answer.** The Sortino-optimal book
  is identical at every ceiling — 10% US / 75% aggregate bonds / 15% gold,
  Sortino 1.84, **CAGR 5.46%**. Sortino has no opinion about return level, so
  optimising it alone runs to low volatility and fails the stated requirement of
  beating All-Weather on return.
- **The max-CAGR frontier books are visibly overfit**: 45% small value + 15% PM
  equity + 40% gold at the 40% ceiling; 45% gold at the 20% ceiling.

## The validation

Same search, no hindsight. Expanding window, refit annually from 2008-06,
92,378 portfolios searched at every refit (coarser grid, which can only help the
searcher's speed and hurt its quality — so a loss here is safe to believe).

```
OUT OF SAMPLE, searched fresh at every refit
  40% / max sortino: CAGR  3.94%   DD -16.49%   Sortino 1.17
  40% / max cagr   : CAGR  5.15%   DD -51.68%   Sortino 0.53   BREACHED
  30% / max cagr   : CAGR  5.77%   DD -49.38%   Sortino 0.59   BREACHED
  25% / max cagr   : CAGR  5.76%   DD -43.96%   Sortino 0.61   BREACHED
  20% / max cagr   : CAGR  5.80%   DD -37.53%   Sortino 0.68   BREACHED

SIMPLY HOLDING A FIXED BOOK over the identical span (2008-06..2026-07)
  50/25/25 eq-gold-dur : CAGR  9.34%   DD -22.25%   Sortino 1.47
  60/20/20 eq-gold-dur : CAGR  9.86%   DD -24.56%   Sortino 1.44
  80/20 VTI-GLD        : CAGR 11.40%   DD -34.40%   Sortino 1.34
  Current allocation   : CAGR 10.11%   DD -36.65%   Sortino 1.15
  100% US Total        : CAGR 11.54%   DD -42.32%   Sortino 1.15
```

**Holding 50/25/25 beat the best searcher on every metric at once**: +5.4pp of
CAGR, a better drawdown, and +0.30 of Sortino. Every max-CAGR ceiling was
breached out of sample, one of them by 32 points. The 0.35 of Sortino and 1.1pp
of CAGR that looked available in sample is not merely unreachable — **chasing it
costs about 5.4pp of CAGR per year.**

## So: is this the answer to the original question?

Yes, and it is a negative answer to the part that motivated the search.

- **There is no allocation to find.** 2.1M candidates, and nothing beats holding
  a simple fixed book once hindsight is removed. This is now the second
  independent demonstration; the first was the drawdown ladder.
- **The books already identified are effectively optimal.** 50/25/25 at the
  98.9th percentile, and the 1.1% above it is curve fit.
- **The ladder is the real decision**, and it is a preference, not an
  optimisation:

  | | CAGR (OOS) | maxDD | Sortino |
  |---|---:|---:|---:|
  | 50/25/25 eq-gold-dur | 9.34% | −22.25% | **1.47** |
  | 60/20/20 eq-gold-dur | 9.86% | −24.56% | 1.44 |
  | 80/20 VTI-GLD | 11.40% | −34.40% | 1.34 |
  | 100% US Total | 11.54% | −42.32% | 1.15 |

  Moving from 100% US to 50/25/25 costs 2.2pp of CAGR and removes 20 points of
  drawdown. Where you sit on that line is your call; no amount of further
  computation makes it for you.
- **Your current allocation is the one book that is clearly dominated.** At
  10.11% / −36.65% / 1.15 it takes 80/20-like drawdown for less return, and sits
  around the 72nd percentile. Every other book listed beats it on Sortino.

## What is still genuinely open

Not the allocation. These:

- **Q3 — history before 1996.** Still the largest hole. No Volcker, no 1973-74,
  and 2022 remains the only observation of stocks and bonds falling together —
  the main failure mode of the very structure being recommended.
- **Q2 — the DFUS implementation edge**, +0.66pp REIT-adjusted, t=2.11 on one
  post-hoc 5-year window. Prospectively testable, not yet tested.
- **Entry timing on the $250K**, already covered in `report.md` §4-5 and
  unaffected by anything here.
