# Open research questions

Written 2026-08-01, after the allocation study's first full pass
(`output/candidates/report.md`). This is the standing list of what we still
cannot answer and what data would close each gap.

## Governing constraint

The user's instruction stands and applies to everything below:

> Let's go through the entire possibility and combinations, and let's see what
> the data says back to us instead of us having an assumption and projecting
> that towards the data.

Walk-forward already showed what happens when that discipline slips: every
drawdown ceiling breached out of sample by 25-45 points, ~5pp of return gone at
every level. So each question below is written to be *falsifiable on data we
either have or can obtain* — not as a thesis looking for support.

Two numbers set the resolution floor for every question here:

- **0.11pp/yr** — GLD vs IAU, two funds holding the same metal. This is what
  "no difference" looks like in this dataset.
- **~5pp/yr** — the out-of-sample shrinkage measured by walk-forward. Any edge
  smaller than this that was found by searching is not credible.

An effect must clear the first to be visible and the second to be actionable.

---

## What the study can already answer

Settled; listed so nobody re-opens them.

| Question | Answer | Where |
|---|---|---|
| Does optimizing to a drawdown ceiling work? | **No.** Every ceiling breached OOS by 25-45pp. Mechanism: 2006 refit chose 100% US REIT; GFC took it -62%. | `walkforward_ladder.py` |
| Do gold and long Treasuries protect on different axes? | **Yes**, measured. dot-com: gold +7.9 / duration +36.4. 2022: gold -10.9 / duration -34.1. | `candidates.py` |
| Does rebalancing policy matter? | **Second-order.** <=0.24pp CAGR across all policies tested. | report §5 |
| Do contributions reduce entry-timing risk? | **Not shortfall-vs-contributed** (marginally worse); they cut outcome *dispersion* 12-41pp. | report §5 |
| Cost of the drawdown ladder? | 0.88pp CAGR buys 15.7 points of drawdown. | report §3 |

---

## Q1 — Does small value's dot-com signature hold up? [HIGHEST VALUE]

**Why this is first.** It is the only candidate lever found so far that
addresses the user's actual stated fear — a large-cap bubble deflating — from an
*equity* sleeve that keeps participating if it doesn't.

Measured on data in hand:

```
dot-com 2000-03..2002-09    VISVX +14.9%    VFINX -38.3%    spread 53pp
GFC     2007-11..2009-02    VISVX -53.3%    VFINX -51.0%    WORSE
COVID   2020-02..2020-03    VISVX -32.6%    VFINX -19.6%    WORSE
```

So it is **not** a crisis hedge. It protects against one specific thing. And the
premium flipped sign: `+4.01pp` 1998-2009, `-2.52pp` 2010-2026.

**Open:** is the dot-com result a repeatable property of the sleeve, or one
episode? With one observation we cannot tell. `VISVX` starts 1998-06, which is
*after* the bubble began inflating and truncates any book containing it.

**Data needed:** US small value monthly total returns **1972-1998**, to cover
the 1973-74 bear, the Nifty Fifty unwind, and 1980-82. Candidates: `DFSVX`
(1993-), `DFA US Micro Cap` / `DFSCX` (1981-), or the Fama-French research
library's small-value decile. FF is a research construct, not investable — usable
as evidence, not as a candidate sleeve, and it must be labeled as such.

---

## Q2 — Can the DFA implementation edge be tested at all?

The claim is **60bps/yr** from avoiding index-rebalancing adverse selection.
Years needed for `t=2`, by tracking error:

```
TE=0.75%/yr ->  6.2 yrs      TE=1.50%/yr -> 25.0 yrs
TE=1.00%/yr -> 11.1 yrs      TE=2.00%/yr -> 44.4 yrs
```

DFUS has ~4 years of ETF history. Its `DTMEX` predecessor is not comparable
(different objective, different exclusions, +19bps expense gap).

**Provisional answer: no**, not to an actionable standard. 0.60pp sits at ~5x the
same-asset noise floor. This is recorded so it is not re-litigated; supplying
DFUS data does not change the arithmetic.

**Would reopen it:** a long series where the *mechanism* is separable — e.g. a
"lazy index" reconstruction vs a standard index over 25+ years.

---

## Q3 — Panel starts 1996-07. What lives before it? [HIGHEST STRUCTURAL VALUE]

The single largest limitation in the study. The panel misses:

- **1973-74** — the deepest post-war equity bear
- **1980-82** — Volcker; the only high-inflation regime in the record
- **1987** — the only true crash

Consequence: **2022 is the sole observation of stocks and bonds falling
together.** The whole equity+gold+duration thesis rests on one episode of its
main failure mode. The gold series alone already reaches 1972 and is validated;
everything else stops at 1996.

**Data needed** — monthly total returns back to ~1972 for, in priority order:

| Exposure | Panel starts | Long proxies to look for |
|---|---|---|
| US Total Market | 1996-07 (VFINX 1985) | `VFINX` pre-1985, FF market |
| Long Treasuries | 1996-07 (VUSTX 1986) | `VUSTX` 1986-, Ibbotson LT govt |
| US Aggregate Bonds | 1996-07 (VBMFX 1986) | `VBMFX` 1986-, BBG Agg |
| Intl Developed | 1996-07 (VTRIX 1985) | MSCI EAFE net TR (1970-) |
| US Small Value | 1998-06 | see Q1 |
| TIPS | 1997 (real start) | *cannot* extend — TIPS did not exist |

Extending **any single one** of the first four is worth more than any refinement
of the current candidate set.

---

## Q4 — How large is the survivorship bias?

Disclosed in report §7, **direction known, magnitude not**. Every fund in the
universe is one that still exists in 2026. The daily archive holds 5 dead funds
(`AUBAX`, `LOMMX`, `PADMX`, `PAGPX`, `PIGLX`) that were deliberately excluded to
keep sleeve composition stable — too few to measure with.

**Data needed:** a dead-fund set with returns up to closure, in the equity and
intl sleeves. Or a published survivorship-bias estimate for the relevant
categories, usable as a stated haircut rather than a measurement.

---

## Q5 — Four exposures have no pre-ETF history

`splice_allowed=False` in `build_study_panel.py`, so these carry ETF-only
history and are structurally disadvantaged in any long-window comparison:

| Exposure | ETF | Starts | Gap |
|---|---|---|---|
| Emerging Markets | EEM | 2003-04 | no dot-com |
| Commodities | DBC | 2006-03 | no dot-com, no 1970s |
| Interm/Short Treasuries | IEF/SHY | 2002-07 | no dot-com |
| PM Equity | FSAGX | — | proxy never graded (anchor GDX absent) |

**Data needed:** graded proxies — `VEIEX` (EM, 1994-), `GSCI`/`CRB` (commodities,
1970-), `VFITX`/`VFISX` (Treasuries, 1991-), `GDX` (to grade PM Equity).

Note commodities in the 1970s is the highest-value item on this list — it is the
one asset expected to work in the regime Q3 says we cannot see.

---

## Q6 — Is there a taxable/retirement split worth acting on?

Deferred, never measured. Gold is taxed as a collectible (up to 28%), bond
coupons as ordinary income — both worst in the taxable bucket, which is also the
bucket with the uncertain call date. Deliberately excluded from the search per
the enumerate-then-measure rule; it is a legitimate **tiebreaker** between books
that are already close on pre-tax merit.

**Data needed:** none. This is analysis on existing results, gated on the
candidate set being settled.

---

## How to supply data

Two sources per series, matching the pattern that worked for gold — one to use,
one to validate against. A single source cannot be checked.

**1. The series.** Either format:

```
# Source: <where>. Retrieved <date>. Total return, dividends reinvested.
year,jan,feb,mar,apr,may,jun,jul,aug,sep,oct,nov,dec
2026,12.31,8.75,-11.02,...
```

or long form: `date,ticker,monthly_return`. Percent or decimal — state which.

**2. An independent cross-check.** A Portfolio Visualizer backtest summary for
the same series is ideal: CAGR, stdev, max drawdown, the annual returns table,
**the drawdown table, and the rolling returns table**.

The last two are not optional. Aggregate stats are order-invariant — a permuted
series passes every one of them. That gap was real: permuting 1996-98 gold months
moved the dot-com return from 7.89% to 24.24% while leaving every headline stat
bit-identical. `validate_gold_series.py` TEST 4 exists to catch it, and it needs
dated drawdowns and rolling extremes to work.

Anything supplied gets the same treatment gold got: validated before use, and
rejected if it fails. `GC=F` was rejected as a gold proxy on exactly this basis
(184bps/yr of roll artifact).

---

## Priority

1. **Q3** — long history for US equity, long Treasuries, or aggregate bonds.
   Unlocks the regime we are blindest to and the failure mode we have seen once.
2. **Q1** — US small value pre-1998. The one lever aimed at the user's stated
   fear.
3. **Q5** — commodities pre-1996, for the same reason as Q3.
4. **Q4** — survivorship magnitude.
5. **Q6** — tax tiebreaker. No data needed; run when candidates settle.
6. **Q2** — closed unless the mechanism becomes separable.
