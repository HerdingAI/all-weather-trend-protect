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
