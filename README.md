# all-weather-trend-protect

A toolkit of portfolio flavors for different market circumstances, built on a clean returns
dataset, with the measured conditions under which each one is the right tool. The point is
knowing what to deploy when — not finding one flavor that does everything. Each flavor here
is a tool built for one regime, and the out-of-sample numbers tell you when to reach for it.
*Research / illustration only. Not investment advice.*

## What's here

- **A returns dataset.** 342 tickers from Yahoo Finance, daily to 1927, monthly to 1962,
  through 2026-07. Integrity-audited: **0 FAIL · 27 PASS · 12 WARN (all benign)** —
  [`output/integrity_findings.md`](output/integrity_findings.md).
- **A walk-forward risk-parity search** — the canonical long-only portfolio.
- **A set of TrendProtect flavors**, each a tool for one circumstance, and a measured map
  of when to use each (below).

## The playbook — which tool for which circumstance

Out-of-sample 2018–2026 (train 2008–17, test 2018–26, net of 10 bps costs and 5.8% leverage
cost where gross > 1). Pick the row that matches the regime you expect.

| Circumstance | Tool | Ann ret | Sharpe | Upβ | Dnβ | Both-down | Dn-corr |
|---|---|---:|---:|---:|---:|---:|---:|
| **Stagflation** — stocks+bonds both fall (2022) | **EW-Infl-Both** | −0.16% | −0.01 | 0.44 | 0.32 | **−2.69%** | 0.29 |
| **Disinflation + growth down** (2008/2020) | **EW-Infl-Dur** | 6.79% | 0.59 | 0.54 | 0.71 | −30.11% | 0.68 |
| **Normal / growth up**, smooth ride | **All-Weather** | 7.37% | **1.06** | 0.33 | 0.48 | −18.74% | 0.79 |
| **Growth up**, want return, accept correlated downside | **RP winner (MinVar)** | 8.43% | 0.61 | 0.63 | 0.94 | −43.12% | 0.76 |
| **Trending up** (momentum leads) | **EW-Scale-Mom6** | 8.50% | 0.61 | 0.43 | 0.65 | −46.50% | 0.59 |
| **Structural short-duration**, no signal | **StructShort** | 9.35% | 0.77 | 0.53 | 0.72 | −33.96% | 0.74 |
| **Balanced** — upside + downside dampening | **EW-MA-Short** | 4.25% | 0.61 | 0.01 | 0.12 | −12.97% | 0.22 |
| **Fast mechanical drawdown hedge** (short duration) | **EW-Hedge-Dur-MA** | 2.28% | 0.30 | −0.03 | 0.24 | −12.10% | 0.33 |
| **Crisis-alpha / uncorrelated sleeve** | **LS-TSMOM** | 2.60% | 0.25 | −0.28 | 0.35 | −11.31% | 0.32 |

How to read it:

- **EW-Infl-Both** is a defensive hedge — the best both-down of the set (−2.69% vs
  All-Weather's −18.74%) and the only flavor with Upβ > Dnβ. Return ≈ 0, so it's a
  protection sleeve, not a return strategy.
- **EW-Infl-Dur** adds long duration when inflation is *falling* — bonds hedge equity for
  free in disinflation (2008/2020) and it keeps return near All-Weather.
- **All-Weather** is the smoothest ride; nothing beat its Sharpe. Reach for the others when
  you have a view on the regime.
- **EW-Scale-Mom6** scales gross with momentum — owns ~1.27× in up-months, de-risks in
  down-months. It's the trending-market tool; it fails when momentum lags the turn (the 2022
  both-down shows the failure mode).
- **StructShort** is a permanent net-short-duration tilt — no signal, no lag, gross 1.0 so
  no leverage cost. It pays a carry drag in every non-stagflation year.
- **EW-MA-Short** is the balanced pick — positive upside beta, a both-down better than
  All-Weather, and the lowest downside correlation of any flavor with positive return.
- **LS-TSMOM** is long/short trend — positive in 2022 because it shorts the falling legs, but
  its upside beta is negative, so it diversifies rather than captures.

Full per-flavor construction, composition, and the per-round menus:
[`docs/portfolio-flavors.md`](docs/portfolio-flavors.md). Full comparison table (all 47):
[`output/risk_parity_eval_asym9/report_eval.md`](output/risk_parity_eval_asym9/report_eval.md) §10.

## The canonical risk-parity portfolio

Four-seasons walk-forward, 1985–2026, ~41 years, every month out-of-sample (selected on
prior data only). Long-only, 20% per-sleeve cap, Ledoit-Wolf shrinkage, 10 bps costs. The
winner is re-selected each fold, so the time-averaged allocation is the honest picture:

| Sleeve | Avg weight | Investable proxy |
|---|---:|---|
| US Corporate Bonds | 20.0% | LQD |
| US Municipal Bonds | 20.0% | MUB |
| US Treasuries | 20.0% | IEF / TLT blend |
| US Equity | 17.8% | VTI |
| World Equity | 15.5% | ACWI |
| International Equity | 14.8% | VXUS |
| Gold / Precious Metals | 13.6% | VGPMX / gold-futures TR |

Out-of-sample (1995–2026, 30.9y): 6.27% CAGR, Sharpe 0.79, max drawdown −25.1%. The per-regime
view is the useful part — it tells you when this long-only book is enough and when to reach
for a hedge:

| Season | All-Weather | Winner |
|---|---:|---:|
| Growth up, inflation up | 0.72% | 0.61% |
| Growth up, inflation down | 0.73% | 0.80% |
| Growth down, inflation down | −0.05% | 0.08% |
| Growth down, inflation up *(stagflation)* | −0.81% | −0.90% |

Stagflation is where the long-only book and All-Weather both struggle — that's the
circumstance the TrendProtect hedges above are for. Full report:
[`output/risk_parity_seasons/report_seasons.md`](output/risk_parity_seasons/report_seasons.md).

## The flavors, by round

Each round added a tool for a specific circumstance. One line each:

1. **Cash-gate / LS overlay / structural short** — gate equity to cash on a downside
   signal; add an LS-TSMOM momentum overlay; structurally short a duration sleeve.
2. **Flip equity net-short** on the downside signal — the tool for an outright negative
   downside beta.
3. **Leading signals** (MA crossover, vol-regime, dual-MA) — tools that act *before* the
   drop, for regimes where lagging momentum is too slow.
4. **Hysteretic asymmetric gates** (fast downside exit, slow upside re-entry) — tools that
   flee drawdowns fast and re-enter cautiously; the only ones that drive Dnβ negative.
5. **Decoupled overlay** — a never-flipping long base plus a separate additive short; the
   tool for keeping upside beta positive while adding a downside short.
6. **Short duration in the overlay + fast drawdown trigger** — the tool for stagflation
   (both-down) hedging.
7. **Leading macro gate** (ex-ante inflation regime, trailing 12m commodities) — the tool
   for inflation-driven regimes; first to give Upβ > Dnβ.
8. **Narrow the gate** with coincident equity-rolling confirmation — the tool for the
   specific case "inflation rising *and* equity rolling over."
9. **Scale gross** — the trending-market tool; a long-only base × a per-month scalar, owns
   more in up-months, de-risks in down-months.

## Repo layout

```
pull_returns.py        monthly returns puller
pull_daily.py          daily returns puller (parquet output)
audit_integrity.py    data integrity audit
risk_parity_seasons.py  canonical four-seasons walk-forward (v3)
risk_parity_eval.py    anchored train/test eval + the 47 TrendProtect flavors (v2)
risk_parity_backtest.py  in-sample composition search (v1, appendix)
all_weather_v2.py      All-Weather baseline
docs/                  data dictionary, methodology, peer review, full flavor catalog
output/                reports + summary CSVs (giant per-combo dumps gitignored)
```

## Running it

```bash
pip install -r requirements.txt
.venv/bin/python pull_returns.py     # monthly returns
.venv/bin/python pull_daily.py       # daily returns (cached to output/daily_prices.parquet)
.venv/bin/python audit_integrity.py  # integrity report

.venv/bin/python risk_parity_seasons.py        # canonical four-seasons walk-forward
.venv/bin/python risk_parity_eval.py --score-mode asymmetric2   # the TrendProtect flavors
```

The per-combo `train_results.csv` / `combinations_results.csv` tables are regenerable and
gitignored; the small summary CSVs and every `report_eval.md` / `report_seasons.md` are
tracked so the links from the docs resolve.

## Read the numbers with care

- One TRAIN (2008–17) / TEST (2018–26) split = one regime. The Sharpe 95% CIs almost all
  span zero and every flavor's Deflated Sharpe is negative. This is an exploration of what
  the constructions *can* do, not a proven edge.
- The flavors share sleeves (effective N is well below the nominal count) and the
  selection is one split, so treat the ranking as directional, not significant.
- The four-seasons inflation signal is the 10y yield 12m change (a rates proxy), not literal
  CPI. Real returns use CPI only with `--cpi-csv`; otherwise a harsh gold-deflated stress.
- The long1985 preset uses asset-class series that exist back to 1985; sleeves that only
  start in the ETF era (TIPS, GLD, DBC, UUP) are in `--preset modern`.

*Research / illustration only. Not investment advice.*