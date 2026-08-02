# Allocation study — what the data supports

*Generated 2026-08-01. Research / illustration only. Not investment advice.*

Panel: 1998-06 → 2026-07 (338 months, 28.2 years), covering dot-com, the GFC,
COVID and 2022. Every book annually rebalanced, net of 10 bps/side on traded
turnover.

---

## 1. The headline: searching for the best portfolio does not work

This study began as a search — find the maximum-return allocation at each
drawdown ceiling. That search produced a clean-looking ladder. **It does not
survive out of sample, and the ladder is withdrawn as a recommendation.**

Walk-forward test: choose the allocation using only data strictly before each
test period, hold it 12 months, score it on months it has never seen. 21 refits,
first after 10 years of history.

| Ceiling | In-sample CAGR | Out-of-sample CAGR | Shrink | IS maxDD | OOS maxDD | Ceiling held? |
|---|---:|---:|---:|---:|---:|:--|
| 40% | 10.36% | 5.33% | −5.03pp | −40.00% | −62.66% | **no** |
| 35% | 10.25% | 4.95% | −5.30pp | −34.94% | −62.66% | **no** |
| 30% | 10.15% | 4.77% | −5.38pp | −29.96% | −63.27% | **no** |
| 25% | 9.73% | 4.14% | −5.59pp | −24.98% | −65.37% | **no** |
| 20% | 9.01% | 3.65% | −5.35pp | −19.99% | −64.21% | **no** |

Every ceiling breached by 25–45 points. Roughly 5pp of return evaporates at
every level.

**The mechanism, verified by reading the selections rather than inferring them:**
the 2006 and 2007 refits both chose **US REIT at 100%**. Over 1996–2006 REITs had
high return *and* no large drawdown, so under a drawdown-ceiling objective they
looked optimal. The GFC then took REITs down 62% with the book entirely in them —
worst month −32.2%, trough −65.4% in February 2009.

That is not bad luck. It is what the objective asks for: *maximise return subject
to a historical drawdown ceiling* selects the asset whose drawdown has not
happened yet. **The constraint causes the concentration it is meant to prevent.**

Over the identical out-of-sample span, fixed books — which need no selection and
therefore carry no shrinkage — beat every optimised one on **every dimension at
once**: 80/20 VTI-GLD returned 11.29% at −40.56% with a +7.42% worst decade.

So the rest of this report compares **fixed allocations, declared in advance**.

---

## 2. The candidates

Eleven books, fixed in `candidates.py` before any comparison ran. The references
are the user's own holdings plus the market. The variants rest on one measured
fact rather than a story — **gold and long Treasuries protect on different axes**:

| Crisis | Gold | Long Treasuries |
|---|---:|---:|
| Dot-com | +7.9% | **+36.4%** |
| GFC | +15.5% | +24.9% |
| COVID | +3.7% | +22.1% |
| 2022 | **−10.9%** | −34.1% |

Each covers the other's failure. Holding both is the one structural idea the data
supports without a search, so the variants are that idea at round weights. Nothing
is tuned.

---

## 3. Results

| Candidate | CAGR | Vol | Max DD | Sortino | Underwater | Worst 10y |
|---|---:|---:|---:|---:|---:|---:|
| 80/20 VTI-GLD | **9.65%** | 13.08% | −38.29% | 1.19 | 4.2y | +0.94% |
| 100% US Total | 9.15% | 15.73% | −50.84% | 0.96 | 5.5y | −2.80% |
| Current allocation | 9.08% | 13.32% | −40.99% | 1.09 | 3.4y | +1.70% |
| 70/15/15 eq-gold-dur | 9.05% | 11.23% | −31.31% | 1.29 | 4.1y | +2.07% |
| 60/20/20 US-intl-gold | 9.02% | 13.01% | −39.70% | 1.11 | 4.2y | +1.57% |
| **60/20/20 eq-gold-dur** | 8.93% | 10.21% | **−24.47%** | 1.41 | 3.2y | +3.52% |
| S&P 500 | 8.92% | 15.37% | −50.78% | 0.96 | 6.2y | −3.45% |
| **50/25/25 eq-gold-dur** | 8.77% | 9.51% | **−22.62%** | **1.52** | 3.0y | **+4.83%** |
| 60/20/20 eq-gold-agg | 8.71% | 10.29% | −26.99% | 1.36 | 3.2y | +2.84% |
| 45/15/20/20 +intl | 8.47% | 10.20% | −25.57% | 1.33 | 3.2y | +4.04% |
| Classic 60/40 | 7.38% | 9.63% | −29.04% | 1.21 | 3.4y | +1.26% |

**The exchange rate.** Against the 80/20 under consideration, **50/25/25 gives up
0.88pp of CAGR** and in return:

- cuts maximum drawdown **−38.3% → −22.6%** (15.7 points)
- raises Sortino **1.19 → 1.52**
- turns the worst ten-year outcome **+0.94% → +4.83%**
- more than halves entry-timing spread (below)

**60/20/20 eq-gold-dur** lands inside the stated 20–25% tolerance for 0.72pp.

### Crises

| Candidate | Dot-com | GFC | COVID | 2022 |
|---|---:|---:|---:|---:|
| 80/20 VTI-GLD | −24.8% | −35.4% | −16.0% | −17.3% |
| S&P 500 | −33.4% | −46.7% | −19.4% | −17.7% |
| 60/20/20 eq-gold-dur | −12.8% | −21.4% | −8.1% | −20.6% |
| 50/25/25 eq-gold-dur | **−7.4%** | **−14.7%** | **−4.8%** | −21.0% |
| 60/20/20 eq-gold-agg | −14.2% | −24.7% | −11.7% | **−16.7%** |

The duration books dominate in every equity crisis and pay for it in 2022 — the
one regime where stocks and bonds fell together. Substituting aggregate bonds for
long Treasuries trades some of that protection for a softer 2022.

---

## 4. Entry timing

Every possible start month, not just the full-period average.

| Candidate | Worst 10y | 10y p5 | Worst 5y | 10y spread | Worst recovery |
|---|---:|---:|---:|---:|---:|
| S&P 500 | −3.45% | −1.01% | −6.67% | 20.0pp | 6.2y |
| 100% US Total | −2.80% | −0.24% | −6.14% | 19.7pp | 5.5y |
| 80/20 VTI-GLD | +0.94% | +2.95% | −0.30% | 14.5pp | 4.2y |
| Current allocation | +1.70% | +3.76% | −0.40% | 12.6pp | 3.4y |
| 60/20/20 eq-gold-dur | +3.52% | +4.96% | +2.24% | 8.9pp | 3.2y |
| **50/25/25 eq-gold-dur** | **+4.83%** | **+6.04%** | **+2.99%** | **6.9pp** | **3.0y** |

This is the 1999-entrant problem quantified. The S&P's worst decade was −3.45%
annualised; the diversified books have **no negative 5- or 10-year window at any
start month**. The spread — how much your outcome depends on when you happened to
start — falls from 20.0pp to 6.9pp.

---

## 5. Cashflow: $250K now, $5K/month

**Two of my own expectations were wrong here, and both are recorded rather than
dropped.**

**Contributions do NOT reduce the worst shortfall against money paid in.** They
make it marginally worse (80/20: −21.2% → −22.1%), because money added during a
decline has not had time to earn.

**What contributions DO** is cut how much the final outcome depends on the entry
month. Relative dispersion of the 10-year terminal multiple, across all start
months:

| Candidate | Lump only | With $5K/mo | Spread cut |
|---|---|---|---:|
| 100% US Total | 0.75x..4.75x | 0.72x..3.00x | 40.6pp |
| 80/20 VTI-GLD | 1.10x..4.21x | 1.00x..2.88x | 26.2pp |
| 60/20/20 eq-gold-dur | 1.41x..3.21x | 1.23x..2.34x | 15.1pp |
| 50/25/25 eq-gold-dur | 1.60x..3.03x | 1.38x..2.26x | 12.5pp |

The effect is **largest for the most volatile books** — contributions substitute
for diversification, partially. With contributions, the diversified books never
fell below **1.23x–1.38x** over any ten-year window even entering at the worst
month; the S&P bottoms at 0.69x.

### Rebalancing is second-order

Monthly, quarterly, annual and 10%/20% threshold bands differ by **at most
0.24pp of CAGR** on any candidate. I had called this "one of the few levers
left"; the measurement does not support that. Annual is fine.

### Contribution steering (taxable bucket)

$125K appreciated, $3K/month new money, both grown at a neutral 7%:

| After | New money | Share of bucket |
|---|---:|---:|
| 1 year | $37K | 21.8% |
| 3 years | $120K | 44.0% |
| 5 years | $215K | 55.1% |
| 10 years | $516K | 67.7% |

**Embedded gains bound the speed of reaching a target, not the destination.** The
taxable bucket can be steered by directing new contributions, reaching ~44% of
target composition in three years without realising a single gain.

---

## 6. The two buckets

Which rung suits which bucket follows from the ladder, and was not assumed.

**Retirement (~$125K + ~$2K/month, 20–30 years, no call on the money).** Long
horizon and a large contribution stream relative to the base. Crashes here are
buying opportunities and the dispersion-cutting effect of contributions is
strongest. This bucket can carry the higher-equity books — 70/15/15 or the 80/20.

**Taxable (~$125K + ~$3K/month, ≤10 years, uncertain call date).** The binding
constraint is not a horizon but a **call option at an unknown strike**: a forced
sale during a drawdown is the actual risk. The relevant statistic is the worst
plausible value at an arbitrary moment, which is exactly the worst-10y and
recovery-time columns. This bucket belongs at the 50/25/25 or 60/20/20 end.

**Tax note, applied last as a tiebreaker and not used to shape the search:** gold
is taxed as a collectible in the US at up to 28%, and Treasury coupons are
ordinary income. Between two otherwise comparable books, the gold and duration
sleeves are more efficiently held in the retirement bucket — which is also the
bucket that can carry more risk.

---

## 7. Limitations — what this study cannot tell you

**Survivorship.** Every proxy is a fund that still existed in 2026, and dead
funds were explicitly excluded from an earlier panel. Returns from a
survivors-only universe are biased **upward**. The direction is known; the
magnitude here is not bounded, and published estimates for surviving-fund bias in
US equity categories run roughly 0.5–1.5pp/yr. Treat every CAGR as an optimistic
edge, and note this affects candidates **roughly equally**, so the *comparison*
between them is far more robust than any absolute level.

**Proxies are validated where they are not used.** Each pre-ETF proxy was graded
against its ETF over their *overlap*, then used only *outside* that overlap. The
test certifies a period the study never uses. That is unavoidable without a third
source, but it is an extrapolation and not a verification.

**The proxy bar is permissive.** The pass criterion (tracking error ≤30% of the
pair's own volatility, ≤1.00pp/yr return difference) admits 839 of 112,560 ticker
pairs, including world-ex-US against Europe-only. It was also set after seeing
results. Nothing in the candidate set depends on a marginal pass, but the bar
would not stop a determined substitution.

**Gold before 2004.** No bullion history exists in the audited Yahoo data; the
series is externally supplied and validated against GLD (3.7 bps/month), 53 of 54
annual returns from a second source, 8 of 8 worst drawdowns by depth and date,
and 5 of 5 rolling-return extremes. Gold futures were tested as an alternative
and **rejected** — they inject ~184 bps/yr of phantom return from roll artifacts.

**One path.** 28 years is a single realisation. The dot-com and GFC results are
each one observation, and 2022 is the only stocks-and-bonds-together episode in
the sample. The consistency across four crises is what carries the argument, not
any single one.

**Not advice.** This is a historical comparison of mechanical rules. It contains
no forecast, and past behaviour is not a guarantee of anything.

---

## Provenance

| Artifact | Produced by |
|---|---|
| `study_panel.csv` | `build_study_panel.py` (splice gates: ETF wins overlap, columns distinct) |
| `study_data_readiness.csv` | `audit_study_data.py` (proxy grading vs GLD/IAU control) |
| `candidates.csv`, `crises.csv`, `entry_timing.csv`, `cashflow.csv`, `rebalancing.csv` | `compare_candidates.py` |
| `walkforward.csv` | `walkforward_ladder.py` |
| `ladder.csv` | `drawdown_ladder.py` — **in-sample only; see §1** |

163 tests. Gold series, panel construction, ladder metrics, and the
no-look-ahead property of the walk-forward are all pinned.
