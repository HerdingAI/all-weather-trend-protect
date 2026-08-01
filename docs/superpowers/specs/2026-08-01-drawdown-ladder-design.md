# Design — Drawdown-Laddered Allocation Menu

*Date: 2026-08-01 · Supersedes the Phase B section of
`2026-07-31-sortino-and-timing-risk-design.md`*
*Research / illustration only. Not investment advice.*

## Research statement

> Across **liquid, long-only ETFs at gross 1.0**, find the **maximum-expected-return
> allocation at each maximum-drawdown ceiling** from 40% down to 20%, on history that
> includes 1973–74, Volcker, 1987, dot-com, the GFC, 2020 and 2022. For each candidate
> report **entry-timing robustness** — the distribution of rolling 5- and 10-year
> outcomes across every possible start month, the worst loss relative to an investor's
> own cost basis, and time to recovery — under a cashflow schedule of **$250K deployed
> now plus $5K/month**.

The deliverable is the **ladder**: the measured price, in forgone return, of each step
down in drawdown tolerance. Not a single recommended portfolio.

## Method discipline — the governing constraint

**Enumerate, then measure. Do not hypothesize a structure and go looking for support.**

An earlier draft of this design reasoned its way to municipal bonds and a tax-driven
asset-location split *before* running anything. That is backwards, and this spec exists
partly to prevent it. Specific instruments, sleeve pairings, and any "X belongs in
account Y" conclusion must **emerge from the search output**, not be supplied to it.

Concretely:

- No sleeve is pre-selected, pre-excluded, or pre-weighted on a story about what it is
  "for". Gold is not assumed to be a diversifier; duration is not assumed to hedge
  equity; commodities are not assumed to hedge inflation. Each is a column the search
  may or may not choose.
- No structure (60/40, risk parity, All-Weather, barbell) is seeded as a starting point.
  They enter only as **benchmarks to be beaten**, alongside the user's own portfolios.
- Tax treatment and account location are applied as a **post-hoc lens on the results**,
  after the frontier exists, and only where the data supports a distinction. They do not
  shape the search space.
- Where the search cannot be literally exhaustive (see §5), the coverage actually
  achieved is stated numerically, and convergence evidence is reported. "We searched
  everything" is a claim requiring proof, not a figure of speech.

## 1. Constraints (fixed by the user)

| Constraint | Value |
|---|---|
| Instruments | Liquid ETFs, buyable today |
| Direction | Long-only |
| Leverage | **None.** Gross 1.0. Financing at 5.8% APR is too expensive to carry |
| Regime view | Forecast-free allocations; regimes enter only as stress tests |
| Drawdown ladder | 40% (absolute worst tolerable) → 20% (stated risk profile), in steps |
| Capital | $250K being rebalanced now |
| Contributions | $5K/month, ~$2K to retirement (near the annual limit), ~$3K to taxable |
| Retirement bucket | ~$125K, 20–30 year horizon, no call on the money |
| Taxable bucket | ~$125K, ≤10 years, **uncertain call date** (house, startup) |
| Taxable friction | Significant embedded gains — selling realizes tax |

## 2. Benchmarks

Every candidate is reported against all four, recomputed on the same panel so the
comparison is like-for-like:

| Benchmark | Composition | PV-reported (1986–2026) |
|---|---|---|
| **Current allocation** | 50% US total, 5% US large, 7% US small value, 2% US mid, 18% ex-US, 18% gold | 10.22% CAGR, Sortino 0.85, MaxDD −42.61% |
| **Candidate under consideration** | 80% VTI / 20% GLD | 10.61% CAGR, Sortino 0.90, MaxDD −39.62% |
| 60/20/20 | 60% US, 20% ex-US, 20% gold | 9.98% CAGR, Sortino 0.84, MaxDD −41.41% |
| **S&P 500** | Vanguard 500 | 11.42% CAGR, Sortino 0.86, MaxDD −50.97% |

**All four violate the 20–25% end of the ladder**, and three of four violate 30%. The
binding crisis is 2008, not dot-com — every one of them handled dot-com better. This is
the finding that motivates the study: the incumbent and the candidate both sit far
outside the stated tolerance, so the question is not "tweak 80/20" but "what does the
frontier actually offer at each ceiling".

## 3. Objective and the ladder

For each ceiling `D ∈ {40%, 35%, 30%, 25%, 20%}`:

> maximize annualized return, subject to maximum drawdown ≤ D, long-only, weights
> summing to 1.

Reported per rung: the allocation, CAGR, realized max drawdown, Sortino and Sharpe,
crisis-by-crisis behavior, and entry-timing statistics. The **shape** of the ladder is
itself a finding — if the curve is flat between two rungs, a large reduction in pain
costs almost nothing, and that is more actionable than any single allocation.

Drawdown is evaluated **both** ways, and a rung must satisfy the ceiling on the worse:

- **Strategy peak-to-trough** — the conventional number, comparable to published
  backtests.
- **Entry-relative loss** — the deepest fall below an investor's own cost basis, taken
  over every possible start month. This is the "losing your own money rather than the
  house's" risk, and the conventional metric hides it.

## 4. Universe

Every asset class in the repo panel that maps to a liquid ETF. The mapping is recorded
explicitly, including the pre-ETF proxy used to extend history and the date the real ETF
takes over:

- US equity (broad, and the size/value/growth splits present in the data)
- International developed, emerging, world
- US Treasuries across the curve (short/intermediate/long)
- US corporate credit, high yield, municipal bonds, TIPS, international bonds
- Gold (bullion), silver, precious-metals equity, broad commodities
- REITs, preferred stock, currency, cash/T-bills

Two gold tracks, unchanged from the prior design and for the same reason: bullion
(GLD/IAU) begins **2004-12**, while the long-history precious-metals sleeve is *miner
equity*, which is a different asset. Long-history results use the miners proxy and say
so; a 2005+ track uses actual bullion. Where the two disagree, the disagreement is the
finding.

## 5. Search method and honest coverage

Three passes, because a literal grid over the full simplex is combinatorially
impossible and pretending otherwise would be the same sin as pre-supposing structure:

1. **Exhaustive coarse grid** over all subsets up to 5 assets at 5% weight increments.
   This genuinely enumerates the space most real portfolios live in.
2. **Large-sample random search** over the full universe simplex (Dirichlet draws),
   followed by local refinement of the best candidates, to cover higher-cardinality
   allocations the grid cannot reach.
3. **Convergence check** — re-run pass 2 with an independent seed and a larger budget;
   if the reported frontier moves materially, the search was not converged and the
   result is reported as provisional.

The report states the number of allocations evaluated, the subset sizes exhaustively
covered, and the convergence evidence. A frontier is only as trustworthy as the search
behind it, and the reader is entitled to see that.

**Multiplicity is a real risk here.** Searching millions of allocations against a fixed
history will find a flattering one by construction. Every headline rung therefore
carries a block-bootstrap confidence interval and a deflated-Sharpe-style penalty for
the number of trials, and is re-tested out-of-sample under §6.

## 6. Out-of-sample discipline

A frontier fitted to the whole history is a description of the past, not a
recommendation. Each rung is therefore re-derived under walk-forward selection —
allocation chosen on data strictly prior, then held and measured on data it never saw —
and the report leads with the walk-forward numbers. Full-sample numbers appear only as
the optimistic bound.

## 7. Entry timing and cashflow

The distinctive part of this study, and the risk the user identified directly.

- **Rolling-start distribution.** For every candidate, all rolling 5- and 10-year
  windows at monthly start offsets: worst, 5th percentile, median, 95th percentile
  CAGR; the spread as the timing-risk measure; the worst window's dates; and the
  longest underwater period.
- **The unlucky entrant.** Explicitly model the 1999-style case — deploy at the worst
  historical moment and measure time to recover cost basis.
- **Contributions as the counterweight.** $5K/month against $250K means contributions
  exceed the initial stake within roughly four years. Model the actual schedule per
  bucket and report how much the contribution stream relaxes the drawdown constraint —
  for a steady contributor an early crash is partly an opportunity, and the size of that
  effect should be measured rather than asserted.

## 8. Rebalancing and contribution steering

Treated as a first-class mechanism, not a footnote — the user's framing.

- **Rebalancing policy** is itself searched: calendar (monthly / quarterly / annual)
  versus threshold bands (±5%, ±10% absolute or relative drift), at 10 bps costs. The
  ladder is reported under the best-performing policy and under annual rebalancing as a
  simple baseline.
- **Reaching the target without selling.** With ~$3K/month against ~$125K of appreciated
  taxable holdings, new contributions alone reach a large share of that bucket within a
  few years. The report quantifies the achievable path — what fraction of the target
  allocation is reachable by directing new money only, at 1/3/5/10 years — so the
  embedded-gains constraint bounds *speed* rather than *destination*.
- **Timing of the rebalance itself.** Because the user is moving $250K at a single
  moment, report the sensitivity of the outcome to *when* that move happens, using the
  same rolling-start machinery.

## 9. Two bucket profiles

The buckets face different risks and are reported separately. Which rung suits which
bucket is a **conclusion to be drawn from the ladder**, not an input:

- **Retirement** (~$125K + ~$2K/month, 20–30y, no call): long horizon and a large
  contribution stream relative to the base.
- **Taxable** (~$125K + ~$3K/month, ≤10y, uncertain call date): the constraint is not a
  horizon but a **call option at an unknown strike date** — a forced sale during a
  drawdown is the actual risk. The relevant statistic is the worst plausible value at an
  arbitrary moment, not the terminal CAGR.

Tax treatment (including the collectibles rate on gold and ordinary-income treatment of
bond distributions) is applied **after** the frontier exists, as a lens for deciding
which of two otherwise-comparable allocations belongs in which account. It does not
constrain the search.

## 10. Deliverables

- `drawdown_ladder.py` — the search, walk-forward evaluation, and cashflow modeling.
- `output/drawdown_ladder/report.md` — the ladder, crisis table, entry-timing
  distributions, rebalancing comparison, and the two bucket profiles.
- CSVs for the frontier, the rolling-window distributions, and the ETF mapping with
  proxy provenance.

## 11. Out of scope

- Leverage of any kind, and any short position.
- Forecast-conditional allocation (the concluded TrendProtect work; also excluded by the
  forecast-free constraint).
- Individual security selection.
- Personalized tax or investment advice. The tax lens in §9 is a mechanical
  consequence-of-the-rules comparison, not a recommendation.
