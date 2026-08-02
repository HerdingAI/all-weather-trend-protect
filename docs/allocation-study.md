# The allocation study

A framework for answering "what should I actually hold?" with measurement instead
of narrative — and for finding out when the honest answer is *we cannot tell*.

> **Not investment advice.** Nobody here is a financial adviser. This is research
> code and a research write-up. Every number is a measurement of the past on a
> specific dataset with specific, disclosed gaps. Read the limitations before the
> conclusions.

---

## 1. The value proposition

Most portfolio backtests answer the question *"what would have worked?"* That
question is nearly useless, because the answer is always available and almost
never survives contact with the future.

This repo is built around a harder question: **"what would have worked, chosen
without knowing the future, and how much of the apparent edge is real?"**

That reframing changes the machinery in four ways.

**1. Every claim gets a noise floor.** Before believing a gap, you need to know
what "no difference" looks like in this dataset. Here it is measured, not
assumed: GLD vs IAU — two funds holding the same metal in the same vault —
differ by **0.11pp/yr**. An edge of 0.6pp/yr is only ~5x that. An edge of 0.05pp
is nothing at all.

**2. Selection is validated, not just results.** The standard error is to search
a thousand portfolios, report the best one's backtest, and call it a strategy.
Here the *entire search procedure* is re-run out of sample. That is what caught
the study's biggest error (§5).

**3. External data is gated before use.** Any series pasted in from elsewhere
must reproduce its own source's published statistics before it is allowed into a
single calculation. Four series have gone through this; several defects were
caught that would otherwise have propagated silently (§6).

**4. Wrong answers stay visible.** Corrections are recorded next to the claims
they correct, in code comments and commit messages, rather than being quietly
edited away. Several are listed in §5. This matters because a research artifact
whose history has been tidied is one you cannot audit.

---

## 2. The method: enumerate, then measure

The governing rule for the whole study:

> Go through the entire space of possibilities and see what the data says back,
> instead of having an assumption and projecting it onto the data.

Concretely, that forbids a few things that feel natural:

- **No sleeve is included because it "should" help.** Gold and long Treasuries
  are in the candidate books because they were *measured* protecting on different
  crisis axes — not because of an inflation-hedge story.
- **Candidate portfolios are declared before comparison.** `candidates.py`
  contains a fixed set written down in advance, with the reasoning in the file.
  Choosing them after seeing results would reintroduce exactly the bias that
  walk-forward exists to catch.
- **Grids, not hand-picked weights.** Where a tilt is tested, it is tested at
  10/20/30% — a round grid — so nothing is tuned.
- **The decision rule is written before the test runs.** `factor_axis_test.py`
  states its pass/fail criteria in the module docstring, above the code.

---

## 3. What's in the box

### Data

| | |
|---|---|
| Universe | 342 tickers, Yahoo Finance |
| Daily | 1927 → 2026-07 |
| Monthly | 1962 → 2026-07 |
| Study panel | 20 asset-class exposures, 1972 → 2026 (per-sleeve starts vary) |
| Integrity | 0 FAIL · 27 PASS · 12 WARN — `output/integrity_findings.md` |
| Tests | 222 passing |

The study panel (`build_study_panel.py`) turns tickers into *exposures* — "US
Total Market", "Gold", "Long Treasuries" — splicing older mutual funds behind
newer ETFs to extend history. Splices are not free: each seam must pass a
tracking-error and mean-return check, and the builder **refuses to write** if any
two columns are identical or a spliced column diverges from its ETF.

### Scripts, by the question they answer

| Question | Script |
|---|---|
| Is this external data trustworthy? | `pv_series.py`, `validate_*_series.py` |
| What exposures do we have, and how far back? | `build_study_panel.py`, `audit_study_data.py` |
| How do specific portfolios compare? | `candidates.py`, `compare_candidates.py` |
| What is *achievable* across all combinations? | `frontier_sweep.py` |
| Does optimising survive not knowing the future? | `walkforward_ladder.py`, `frontier_walkforward.py` |
| Is sleeve X a genuinely independent return source? | `factor_axis_test.py` |
| What happens when yields rise? | `rate_regime_test.py` |

---

## 4. The core findings

All net of 10bps/side costs. Windows stated per result.

### Searching for the optimal allocation does not work

2,139,753 long-only portfolios enumerated at 5% granularity. Then the same search
re-run with no hindsight — expanding window, refit annually.

```
SEARCHED, out of sample     40%/max cagr   CAGR  5.15%   DD -51.68%   ceiling breached
                            20%/max cagr   CAGR  5.80%   DD -37.53%   ceiling breached
HELD, fixed, same span      50/25/25       CAGR  9.34%   DD -22.25%   Sortino 1.47
                            80/20 VTI-GLD  CAGR 11.40%   DD -34.40%   Sortino 1.34
```

**Holding a simple fixed book beat the best searcher on every metric at once** —
+5.4pp of CAGR, better drawdown, +0.30 Sortino. Every drawdown ceiling the
optimiser was given was breached out of sample, one by 32 points.

The mechanism is visible in the fold-by-fold selections: a 2006 refit put 100%
into US REIT, because REITs had high return and no large drawdown over 1996-2006.
The GFC then took REITs down 62%. A drawdown-ceiling optimiser systematically
selects whatever asset's crash has not happened yet.

### The declared books are already near-optimal

Against all 2.1M portfolios, by Sortino: **50/25/25 sits at the 98.9th
percentile**. The remaining 1.1pp of CAGR "available" is concentrated in books
like *45% gold* that no one would hold and that fail out of sample.

### Maximising Sortino alone is a broken objective

The Sortino-optimal book is identical at every drawdown ceiling — 75% aggregate
bonds — with Sortino 1.84 and **CAGR 5.46%**. Sortino has no opinion about return
*level*, so optimising it alone runs to low volatility. Return-subject-to-a-
drawdown-ceiling is the objective that actually encodes what an investor wants.

### Protection comes from leaving equity, not from diversifying within it

Dot-com, measured as points saved in the crash per point given up in the run-up:

| | gave up | saved | ratio |
|---|---:|---:|---:|
| 60/20/20 equity-gold-duration | −10.2 | +22.8 | **2.2** |
| A conventional diversified equity book | −11.3 | +13.6 | **1.2** |

Diversifying *inside* equity — international, small cap, small value — pays the
participation cost without buying the defence, because all equity falls together.
Gold and duration diversify *out* of equity.

### A factor sleeve is not a third uncorrelated axis

Small value passes an independence test at regime frequency (36-month excess
correlates 0.404 with gold's, against a 0.646 control between gold and duration
themselves) but fails where it counts: in the worst decile of market months it
returns **−8.40%/mo against the market's own −7.70%**, up in 1 month of 41. Gold
returns +0.99% and long Treasuries +1.64% in those same months.

It is a diversifying *return* sleeve, not a protective one.

### Nothing hedges "equity down AND rates up"

86 months since 1985, market averaging −3.66%/mo. Every sleeve has a negative
mean. The least-bad: gold −0.03%/mo, short Treasuries −0.09%/mo. Long Treasuries
−2.43%/mo. Duration damage is monotonic in duration, which makes shortening the
bond sleeve the one reliable lever.

**You can roughly halve this scenario's damage. You cannot eliminate it.**

---

## 5. Errors this process caught

Listed because the catches are the argument for the method.

| Error | How it was caught | Impact |
|---|---|---|
| Treasury sleeve built from **yield levels**, inverting it | Exploration | Sleeve was −0.51 correlated with a clean version of itself; understated return 289bps/yr |
| Splice ran oldest-first, so **proxies overwrote the ETFs** | Code review | Panel's "US Total Market" was VFINX for VTI's entire life |
| Two panel columns **byte-identical** | Distinctness gate | Consequence of the above |
| Drawdown ceiling enforced **gross**, reported **net** | Code review | Every published rung breached its own labelled ceiling |
| `dropna(how="any")` silently deleting whole asset classes | Code review | A 5-month window shift flipped "infeasible" to "feasible" |
| Rolling-window off-by-one skipping the **inception window** | Code review | Dropped precisely the unlucky-entrant case the study was about |
| Gold validation **blind to ordering** | Adversarial review | A permutation moved dot-com return 7.89% → 24.24% leaving every headline stat bit-identical |
| A diversification bar that **rejected its own control** | Running it | Would have failed gold and duration, the accepted pair |
| Seam constants **duplicated and stale** (1.50 vs the real 1.00) | Cross-check | Authorised a splice the panel is designed to refuse |
| A convention inferred from **one series**, falsified by the next | Second series | `-0.00%` sign was not meaningful after all |

The last three were errors in the *analysis of this study*, made while applying
its own rules. They are in the repo with their corrections attached.

---

## 6. Using this to answer your own question

### Validate a series before you trust it

Paste monthly returns plus the source's own summary statistics, then gate them:

```bash
.venv/bin/python validate_dfus_series.py
```

Four checks: the source's compounded balance path must reproduce its return
column; its published summary statistics must recompute; the series must behave
like what it claims to be (graded against an anchor by tracking error, not
correlation); and the record must be long enough to resolve the effect you care
about.

That last check is the one people skip. Detecting a 0.60pp/yr edge at a measured
0.67%/yr tracking error needs **4.8 years**. At 2.0%/yr it needs **44**. Compute
it before running the comparison, not after:

```python
from pv_series import years_for_t
years_for_t(1.96, te_pp=1.5, edge_pp=0.6)     # 25.0 years
```

### Compare portfolios you care about

Add them to `candidates.py` — **before** running anything — then:

```bash
.venv/bin/python compare_candidates.py
```

Produces CAGR, drawdown, Sortino, crisis-window behaviour, entry-timing
distributions across every possible start month, cashflow paths for a lump sum
plus monthly contributions, and a rebalancing-policy comparison.

### Map what is achievable

```bash
.venv/bin/python frontier_sweep.py          # 2.1M portfolios
.venv/bin/python frontier_walkforward.py    # then remove hindsight
```

The first tells you where your book sits in the distribution. **The second tells
you whether the gap above it is real.** Never run the first without the second —
that is the error the whole study is organised around.

### Test a sleeve as a diversifier

```bash
.venv/bin/python factor_axis_test.py
```

Three lenses — monthly tail, regime frequency, named episodes — because an asset
can diversify at one frequency and not another. Gold and duration hedge monthly;
a valuation cycle operates over years. Testing a regime claim with a monthly
statistic is a category error.

### Stress a conclusion against a regime

```bash
.venv/bin/python rate_regime_test.py
```

Episodes are identified mechanically from the 10-year yield, not chosen. This is
a conditional stress test — *what happened last time yields rose* — not a
forecast.

---

## 7. What this does NOT contain

The honest list. Several of these are load-bearing.

**No history before 1987 for bonds and equities.** The single largest gap. There
is no 1973-74, no Volcker, no 1987 crash. Consequently **2022 is the only
observation of stocks and bonds falling together** — which is the main failure
mode of the very structure the study ends up recommending. Gold alone reaches
1972.

**No forecasting.** Nothing here predicts returns, rates, or inflation. Every
regime result is conditional: *when this happened before, this followed*.

**Survivorship bias, direction known and magnitude not.** Every fund in the
universe still exists in 2026. Measured factor returns are biased upward by an
unquantified amount.

**One path.** History ran once. A 39-year record contains far fewer independent
observations than it appears to — overlapping windows are not independent
samples, and a 100% rolling win rate over 38 overlapping windows may be ~2.5
effective observations.

**Monthly resolution.** Month-end sampling cannot see intra-month troughs, so
every drawdown here is a lower bound on the real one.

**No taxes, no transaction friction beyond 10bps/side.** No bid-ask modelling, no
tax-lot accounting, no early-withdrawal penalties.

**Proxies validated on overlap, used outside it.** A splice graded on 1998-2026
agreement is then used for 1990-1998, where it cannot be checked.

**A permissive proxy bar.** 839 of 112,560 ticker pairs pass the equivalence
test. That is a real filter, but it is not a tight one.

**Not investment advice, and no adviser is involved.** No view is taken on your
tax situation, income stability, insurance, debts, or anything else that matters
more than allocation for most people.

---

## 8. How it leads to a recommendation

The chain, so it can be audited or rejected at any link:

1. **Establish a noise floor.** GLD/IAU = 0.11pp/yr. Anything smaller is invisible.
2. **Validate every input** against its own source before use.
3. **Ask whether searching works at all.** It does not — 5.4pp/yr worse than
   holding a fixed book. So the deliverable becomes a *comparison*, not an
   optimisation.
4. **Declare candidates in advance**, at round weights.
5. **Map the achievable region** to check the candidates are not far off. They
   are at the 98.9th percentile.
6. **Test each sleeve's actual job.** Gold and duration protect. Factor sleeves
   add return, not protection.
7. **Stress the survivor** against the regime that threatens it. Long duration
   fails a rising-rate regime badly (−5.48%/yr, worst sleeve of any tested), so
   aggregate bonds replace it — costing ~2 points of dot-com protection and
   gaining ~4 points in a 2022 repeat.
8. **Split by horizon,** because the constraint differs. A long horizon absorbs
   drawdown and is paid for it. A pot with an uncertain call date cannot risk
   being sold at the bottom.
9. **State what remains unhedgeable.** Equity-down-and-rates-up can be halved,
   not solved.

What the chain produces is not "the optimal portfolio" — the study's own evidence
says no such thing is findable. It produces **a small number of defensible books,
a measured price for each step down the risk ladder, and an explicit list of the
scenarios that would break them.**

The remaining decision — how much drawdown to accept for how much return — is a
preference. No amount of computation makes it for you, and any tool claiming
otherwise is fitting a curve.
