# Design — Forecast-Free Sortino Maximization & Entry-Timing Risk

*Date: 2026-07-31 · Status: approved design, pending implementation plans*
*Research / illustration only. Not investment advice.*

## Research statement

> Among **forecast-free** portfolios — static weights with rebalancing, and
> trailing-covariance risk-parity weightings (InvVol / ERC / MinVar) — over the repo's
> asset-class universe, which construction **maximizes the out-of-sample Sortino ratio**,
> and **how sensitive is each candidate to entry date**? Entry-date sensitivity is measured
> as the distribution — especially the worst case — of rolling 5- and 10-year outcomes
> across all possible start months.

"Forecast-free" is the operative constraint. The repo's existing TrendProtect playbook is
explicitly regime-conditional: it tells you which tool to deploy *given a view on the coming
regime*. Holding a view is market timing. This study asks the complementary question — how
much downside-adjusted return is reachable while refusing to predict anything — and treats
the playbook as the contrast case, not the baseline.

Benchmarks (all recomputed on repo data so the numbers are comparable): the three Portfolio
Visualizer portfolios that motivated the question (the 6-asset sample; 80/20 US-stock/gold;
60/20/20 US/ex-US/gold), 100% US equity, the repo's All-Weather, and the risk-parity winner's
time-averaged weights.

The hypothesis under test comes from the PV data: 80/20 US-stock/gold posted the best Sortino
(0.90) of its set **without any bond allocation**, on the strength of gold's ~0.00 correlation
to US equities. Whether that survives out-of-sample discipline — and whether duration and munis
(which dominate the repo's risk-parity winner) supply downside protection gold alone cannot — is
the substantive question.

## Findings that reshaped the design

Three discoveries during exploration changed the scope. They are recorded here because they are
load-bearing, not incidental.

### Finding 1 — The published asset-class file has a return-contamination bug

`pull_returns.py:426-437` builds equal-weighted asset-class aggregates while excluding only
`Sector-*` classes and single stocks. It does **not** exclude tickers of `kind == "YIELD"`,
even though `docs/methodology.md:55` states that yield series "are excluded from
asset-class/sector return aggregations." The documentation describes an exclusion the code
never implements.

Consequently `^FVX`, `^TNX`, and `^TYX` — Treasury **yield levels** — have their percent
changes averaged into the `US Treasuries` sleeve as though they were returns. Because yields
move opposite to bond prices, the result is inversion rather than noise:

| `US Treasuries` sleeve | Ann. return | Ann. vol | Worst month | Series start |
|---|---:|---:|---:|---|
| As published | 2.24% | 5.43% | −9.73% | 1985-02 |
| Fund-only (clean) | 5.13% | 6.70% | −6.07% | 1986-06 |

The two versions correlate **−0.51** over their common span, with a mean absolute monthly
difference of 2.03%. The published sleeve understates Treasury return by 289 bps/yr and
inverts its month-to-month behaviour. Worse, 1985-02 through 1986-05 is composed *entirely*
of yield changes — no total-return Treasury fund exists in the dataset before VUSTX
(1986-06 monthly / 1986-05 daily), so sixteen months of the sleeve are pure artifact.

The same flaw affects `US Equity` via the price-only indices `^GSPC`, `^DJI`, `^IXIC`, `^RUT`,
but immaterially: correlation 0.9996 and ~5 bps/yr, because four price series are diluted
among 71 total-return funds and only dividends separate them.

A third case is structural rather than dilutive: the `Volatility` sleeve is **100% `^VIX`**,
and VIX percent-changes are no more a return than yield changes are. The sleeve is not
investable as constructed.

This affects published work. The risk-parity winner allocates 20% to Treasuries, and every
TrendProtect flavor's bond leg rests on this series.

### Finding 2 — Ticker-level data extends the sleeves ~5 years further back

The monthly asset-class file begins 1985-02, but not because of a configured cutoff — the
monthly puller already requests `period="max"` (`pull_returns.py:374-380`). The wall is
Yahoo's: monthly-interval history for these instruments generally starts ~1985
(`pull_returns.py:579`). The **daily** archive is not so limited, so compounding daily
returns to monthly recovers earlier history from data already downloaded — no new pulls.

Earliest clean (fund-only, total-return) start per sleeve:

| Sleeve | Clean start | Via |
|---|---|---|
| US Equity | 1973-05 | MIGFX / MITTX / PIODX |
| World Equity | 1973-05 | OPPAX |
| Gold / Precious Metals | 1978-01 | ASA |
| US Corporate Bonds | 1980-01 | FBNDX |
| US Municipal Bonds | 1980-01 | VWITX |
| International Equity | 1983-05 | VTRIX |
| **US Treasuries** | **1986-05** | VUSTX — the binding constraint |
| Gold (bullion) | 2004-11 | GLD |

A prototype confirmed the mechanism: compounding the existing daily series yields a clean
five-sleeve monthly panel spanning **1980-01 → 2026-07, 559 months**. The gain matters
disproportionately because 1980–82 contains the Volcker shock and the accompanying bond
bear — the only high-inflation stress in the record, and the regime most likely to separate
portfolios on downside risk.

### Finding 3 — Bullion cannot be extended; the long "gold" history is miners

`GLD`/`IAU` begin 2004-11 and no earlier bullion instrument exists in the dataset. The
1978-onward `Gold/Precious Metals` sleeve is `ASA`, `INIVX`, `FSAGX` — precious-metals
**miner funds**. Miners are equities: materially higher volatility and materially positive
equity correlation. They are not a proxy for bullion, and PV's result depends specifically
on bullion's near-zero equity correlation. Extending history does not resolve this; it is a
genuine either/or, handled below by running both and reporting the disagreement as a finding.

## Scope decomposition

The decision to correct the bug at source makes data remediation a prerequisite. The work is
therefore two projects in sequence, each receiving its own implementation plan.

- **Phase A — Clean sleeve construction, then re-derive.** Fix the aggregation, extend
  history, regenerate, re-run the risk-parity pipeline, republish.
- **Phase B — `sortino_search.py`.** The study proper, on clean data.

Phase B depends on Phase A's outputs and does not begin until Phase A's reports are
regenerated.

---

## Phase A — Clean sleeve construction and re-derivation

### A1. Fix the aggregation

In `pull_returns.py`, exclude from asset-class aggregates any ticker whose `kind` marks it as
not-a-total-return series:

- `kind == "YIELD"` (`^TNX`, `^FVX`, `^TYX`) — percent changes of a yield level are not returns.
- The price-only equity indices `^GSPC`, `^DJI`, `^IXIC`, `^RUT` — numerically immaterial, but
  they are price-only where every other constituent is total-return.
- `^VIX` — a level, not a holdable return stream. This removes the `Volatility` sleeve from
  the aggregates entirely. It is already off by default (`default_sleeves` drops it absent
  `--include-volatility`), so the practical cost is nil and the alternative is preserving a
  sleeve nobody can hold. A consequence to handle rather than discover: `--include-volatility`
  becomes inoperative once the sleeve is absent from the aggregates. It must fail with a clear
  message instead of silently producing a portfolio without the sleeve the flag requested.

**Ticker-level data is untouched.** Only aggregation changes. This is essential:
`risk_parity_seasons.py:26` uses the 12-month change in `^TNX` as its inflation-regime
signal, which is a correct use of a yield level. Removing `^TNX` from *return aggregates*
does not disturb it, and `^TNX` daily history reaches 1962, so the signal covers the extended
sample.

`docs/methodology.md` and `docs/nuances_and_caveats.md` are updated so the documented
behaviour and the implemented behaviour agree, including the measured impact table above.

### A2. Extend history via daily compounding

Add a daily→monthly aggregation path producing
`output/monthly_returns_by_asset_class_extended.csv`: per ticker, compound daily returns
within each calendar month (`prod(1+r)-1`); then equal-weight across the asset class's
constituent tickers, applying the same exclusions as A1.

Emitted as a **new file** alongside the corrected original so no existing consumer silently
changes shape. A companion coverage table records each sleeve's start date and constituent
count over time, because the panel's composition varies with sleeve availability.

Partial-month handling is explicit: a ticker's first and last months are included only if the
month is complete in the daily data, so a stub month cannot masquerade as a full-month return.

### A3. Re-run and republish

Per the approved scope: **all ten evaluation rounds plus the seasons walk-forward**, on the
**extended** panel.

One consequence should be understood before reading the results. The eval pipeline's windows
are TRAIN 2008-17 / TEST 2018-26, so the extended history does **not** reach them — the ten
eval rounds change because of the *bug fix alone*. Only `risk_parity_seasons.py` (a 1985–2026
walk-forward) gains sample, running from ~1981 once the 12-month regime lookback is satisfied.
Attribution is therefore cleaner than the "both changes at once" concern suggested: eval
deltas are attributable to the fix; seasons deltas are attributable to fix plus extension
jointly, and the spec requires seasons to be run **twice** — fixed-only and fixed-plus-extended
— so its two effects separate too.

**The published playbook numbers are expected to move materially, and conclusions may change.**
The clean Treasuries sleeve earns 289 bps/yr more and is negatively correlated with the
contaminated one. This is a re-derivation, not a refresh. Every regenerated report carries a
header noting it supersedes a version computed on contaminated bond data, and the README and
`docs/portfolio-flavors.md` tables are updated to the new numbers.

Runtime for ten rounds is unmeasured and is the principal schedule risk; the implementation
plan measures a single round first and re-scopes if the total proves impractical.

---

## Phase B — `sortino_search.py`

A new standalone script. It imports shared helpers from `risk_parity_eval.py`
(`ledoit_wolf_cov`, `project_capped_simplex`, the `s_*` weighting solvers,
`precompute_refits`, `fixed_weight_backtest_costs`, `block_bootstrap_ci`, `_max_dd`) and
**modifies no existing script**.

### B1. Samples

Three tracks, each reported separately; no track's result is presented as the single answer.

| Track | Span | Sleeves |
|---|---|---|
| **1 — Long** | 1980-01 → 2026-07 (~46.6y) | US Equity, World Equity, Gold/PM, US Corporates, US Munis |
| **2 — Full universe** | 1986-05 → 2026-07 (~40.2y) | Track 1 + US Treasuries, International Equity |
| **3 — Bullion** | 2004-12 → 2026-07 (~21.6y) | Track 2 with GLD/IAU replacing Gold/PM |

Track 3 is the only one that genuinely tests the PV hypothesis. The miners sleeve is labelled
**"Precious-Metals Equity"** in every table and never "Gold." Where Tracks 1/2 and Track 3
disagree, the disagreement is reported as a substantive finding about whether the
diversification benefit is a property of bullion specifically.

### B2. The Sortino objective

Annualized Sortino at **MAR = 0** throughout — matching PV's convention (so the pasted PV
figures are directly comparable) and the repo's existing rf = 0 Sharpe convention
(`risk_parity_eval.py:1476`).

No full-history risk-free series exists in the dataset: the `Money Market` sleeve begins
2023-05 (35 months) and the earliest short-Treasury proxy, `SHY`, begins 2002-08. A MAR > 0
robustness column is therefore computed on the 2002-08+ subsample only, using SHY, and is
reported there and nowhere else rather than being extrapolated.

Downside deviation uses the full-length convention (deviations below MAR summed over **all**
periods, not only losing ones), stated explicitly in the report since the alternative
convention yields systematically different numbers and PV's exact choice is not documented.

Every headline Sortino is accompanied by a **block-bootstrap confidence interval**
(reusing `block_bootstrap_ci`). No candidate is declared a winner on a point estimate.

### B3. Candidates

**Benchmarks, replicated on repo data.** PV-1 (6-asset sample), PV-2 (80/20 stock/gold),
PV-3 (60/20/20), 100% US equity, All-Weather, and the RP winner's time-averaged weights.
The PV replication is a **validation gate**: if PV-2's Sortino on Track 3 does not land near
the published 0.90, the discrepancy is diagnosed and explained before any search result is
reported. A search built on a panel that cannot reproduce a known answer is not trustworthy.

**Static-weight search.** Dirichlet sampling plus local refinement, maximizing TRAIN Sortino,
evaluated untouched on TEST. Two splits, because a single split can flatter one regime and
Sortino estimates are noisy:

- Split 1: TRAIN 2008-01–2017-12 / TEST 2018-01–2026-07 (the repo's existing discipline).
- Split 2: TRAIN track-start–2005-12 / TEST 2006-01–2026-07 (long-sample robustness).
  **Tracks 1 and 2 only.** Track 3 begins 2004-12, which would leave 13 months of training,
  so Track 3 is evaluated on Split 1 alone and its single-split status is stated in the report.

Rebalancing sensitivity across monthly / quarterly / annual, at 10 bps costs. Long-only,
weights summing to 1, with the repo's 20% per-sleeve cap applied via the exact capped-simplex
projection as a reported variant alongside the uncapped search.

**Risk-parity weightings.** EW, InvVol, ERC, MinVar — walk-forward via the imported solvers,
scored on Sortino. This tests whether reactive covariance weighting beats any fixed vector
without forecasting.

The **trial count is recorded and reported** with a deflated-Sharpe-style multiplicity caveat.
A grid search over thousands of weight vectors will find a flattering TRAIN Sortino by
construction; the report states how many candidates were examined so TEST results are read
with appropriate scepticism.

### B4. Entry-date sensitivity

For every candidate and benchmark, all rolling 5-year and 10-year windows at monthly start
offsets (~500 and ~440 windows on Track 1). Reported per portfolio: worst, 5th percentile,
median, 95th percentile rolling CAGR; the spread (p95 − p5) as the timing-risk measure; the
worst window's start and end dates; and the longest time spent underwater.

The headline of this section is one table answering the question directly: **if you had picked
the worst possible month to invest, what happened?** Low spread and a high worst-case are what
"protected from timing the market" means operationally, and a portfolio that maximizes Sortino
while widening that spread has not solved the stated problem — the report says so where it occurs.

### B5. Deliverables

- `sortino_search.py` — the script.
- `output/sortino_search/report.md` — narrative report, all three tracks.
- `output/sortino_search/*.csv` — candidate metrics, rolling-window distributions, PV
  replication check.

Missing sleeves or coverage gaps raise an explicit error rather than being silently dropped
to NaN, consistent with the repo's preference for explicit failure.

### B6. Testing

Written before implementation, per the repo's TDD practice:

- Sortino and downside deviation against hand-computed synthetic series, including the
  zero-downside edge case and both downside-deviation conventions.
- Rolling-window extraction — count, boundaries, and off-by-one at series ends.
- Daily→monthly compounding against a hand-computed month, plus the partial-month rule.
- Cross-check that the static backtest reproduces `fixed_weight_backtest_costs` on a known input.
- A regression asserting the corrected aggregation excludes every non-total-return ticker.

## Out of scope

- New TrendProtect flavors, regime gates, or any forecast-conditional signal — that is the
  concluded investigation, and reintroducing it would violate the forecast-free constraint.
- Vol-targeting and DCA / contribution scheduling — considered and deliberately excluded.
- Sourcing a long bullion series from outside the audited dataset.
- Any change to `risk_parity_eval.py`, `risk_parity_seasons.py`, or
  `risk_parity_backtest.py` logic. Phase A re-runs them; it does not alter their methods.
