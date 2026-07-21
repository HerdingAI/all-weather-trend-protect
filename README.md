# all-weather-trend-protect

A data pipeline and a piece of portfolio research. We pulled clean daily and monthly
returns for **342 tickers** back to 1927, built a walk-forward risk-parity search on top of
them, and then spent nine rounds trying to build a flavor of All-Weather that beats it on
return while staying less correlated to equities on the way down. This repo is the artifact
of that work — the data, the code, the measured results, and an honest write-up of what we
found. *Research / illustration only. Not investment advice.*

## What's actually in here

- **A returns dataset.** 342 tickers from Yahoo Finance, daily to 1927, monthly to 1962,
  through 2026-07. Integrity-audited: **0 FAIL · 27 PASS · 12 WARN (all benign)** — see
  [`output/integrity_findings.md`](output/integrity_findings.md).
- **A risk-parity portfolio search.** Four scripts on
  `output/monthly_returns_by_asset_class.csv`. Canonical is the four-seasons walk-forward
  (`risk_parity_seasons.py --preset long1985`), backtested to 1985 (~41 years).
- **A nine-round investigation.** 47 "TrendProtect" flavors built to answer one question
  (below), fully documented in [`docs/portfolio-flavors.md`](docs/portfolio-flavors.md).

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

Out-of-sample (1995–2026, 30.9y): **6.27% CAGR**, Sharpe 0.79, max drawdown −25.1%.
All-Weather on the same window does 6.53% / 0.957, so the search does **not** beat the
benchmark on the long horizon — and that is the point of writing it down. The interesting
view is per-regime, where the portfolio's shape shows:

| Season | All-Weather | Winner |
|---|---:|---:|
| Growth up, inflation up | 0.72% | 0.61% |
| Growth up, inflation down | 0.73% | 0.80% |
| Growth down, inflation down | −0.05% | 0.08% |
| Growth down, inflation up *(stagflation)* | −0.81% | −0.90% |

Stagflation is the weak spot — for All-Weather and for everything we built after. Inflation
as priced by gold eats the nominal return: real (gold-deflated) CAGR is about −0.3%. Full
report: [`output/risk_parity_seasons/report_seasons.md`](output/risk_parity_seasons/report_seasons.md).

## The TrendProtect investigation

One question: can we find a flavor of All-Weather with **higher expected return** while
keeping equity correlation **asymmetric** — correlated on the way up, low or negative on
the way down? Long-term shorting a ticker was allowed; leverage was allowed at a 5.8% APR
funding cost.

We built **47 flavors** over **nine rounds**, each round isolating one construction idea and
measuring it out-of-sample (train 2008–17, test 2018–26, block-bootstrap CIs, Deflated
Sharpe). The rounds, in one line each:

1. **Cash-gate / overlay / structural short.** Gate equity to cash on a downside signal;
   add an LS-TSMOM overlay; structurally short a duration sleeve.
2. **Flip equity net-short** on the downside signal — the direct lever for negative Dnβ.
3. **Leading signals** (MA crossover, vol-regime, dual-MA) to fix round 2's lagging momentum.
4. **Hysteretic asymmetric gates** — fast downside exit, slow upside re-entry. First to
   drive Dnβ negative; Upβ went negative too.
4b. A wider sweep of that hysteretic gate — the asymmetry is structural, not a tunable band.
5. **Decoupled overlay** — a long-only base that never flips (Upβ stays positive) plus a
   separate additive short on the equity sleeves.
6. **Short duration in the overlay too** (hedge the both-down / stagflation months) plus a
   fast drawdown trigger.
7. **Leading macro gate** — fire the overlays off an ex-ante inflation regime (trailing 12m
   commodities). First time Upβ > Dnβ — at ~0 return.
8. **Narrow the gate** with a coincident equity-rolling confirmation. Restored the return
   (first inflation-gate flavor to beat 7.37%) — lost the asymmetry.
9. **Scale gross** instead of timing a short — a long-only base × a per-month scalar. Beat
   7.37% on return; the lagging scalar reversed the asymmetry.

### What we found

The two halves of the goal — **(a) beat All-Weather's 7.37% net OOS return** and **(b) have
Upβ > Dnβ** — were each achieved, by three different primitives, but **never in one flavor**.
Every flavor with Upβ > Dnβ gives the return back (Sharpe ≈ 0); every flavor that beats
7.37% has Upβ < Dnβ. Six structural findings, named in
[`docs/portfolio-flavors.md §0`](docs/portfolio-flavors.md), characterize the tension from
each direction. We closed the investigation after round 9 rather than run the one remaining
untried cell; the closure is documented honestly, with the untried cell named.

### Flavors at a glance

Out-of-sample 2018–2026 (the anchored eval split). All-Weather on this split is 7.37% /
Sharpe 1.055. None of the "wins" below is statistically significant — every flavor's
Deflated Sharpe is negative, the sleeves are shared, and it is one TRAIN/TEST split.

| Objective | Flavor | Ann ret | Sharpe | Upβ | Dnβ | Both-down |
|---|---|---:|---:|---:|---:|---:|
| Benchmark (nothing beat its Sharpe) | **All-Weather** | 7.37% | **1.055** | 0.327 | 0.475 | −18.74% |
| Asymmetry achieved, first time (r7) | **EW-Infl-Both** | −0.16% | −0.01 | **0.436** | **0.316** | **−2.69%** |
| Widest Upβ−Dnβ gap (r7) | **EW-Infl-BothL** | 0.22% | 0.02 | **0.522** | **0.422** | −7.26% |
| Beats AW on return, infl-gate (r8) | **EW-InflC-Both6** | **8.38%** | 0.65 | 0.466 | 0.655 | −29.64% |
| Beats AW on return, scaled gross (r9) | **EW-Scale-Mom6** | **8.50%** | 0.61 | 0.427 | 0.651 | −46.50% |
| Best downside protection ex-Both (r6) | **EW-Hedge-Dur-MA** | 2.28% | 0.30 | −0.025 | 0.243 | −12.10% |
| Best balance, positive Upβ + return (r3) | **EW-MA-Short** | 4.25% | 0.61 | 0.013 | 0.123 | −12.97% |

### What we'd actually use

Read calmly and in this order:

- **All-Weather** is still the benchmark on risk-adjusted return. Nothing beat its Sharpe.
- **EW-MA-Short** (round 3) is the closest any flavor came to the brief *with positive
  return* — positive Upβ and a both-down better than All-Weather — but Dnβ still exceeds
  Upβ and the return is well below 7.37%. Rounds 5–9 did not dethrone it on the combined
  return-plus-property view.
- **EW-Infl-Both** (round 7) is the downside hedge — the best both-down of the entire
  investigation (−2.69% vs AW −18.74%), and one of only two flavors with Upβ > Dnβ. Net
  return ≈ 0, so it is a protection sleeve, not a return strategy.
- **EW-InflC-Both6** (round 8) and **EW-Scale-Mom6** (round 9) beat 7.37% on return — the
  first via a narrower inflation gate, the second by scaling gross — but both give back the
  asymmetry (Upβ < Dnβ) and have worse both-down than All-Weather.

Full per-round construction, composition, and measured menus:
[`docs/portfolio-flavors.md`](docs/portfolio-flavors.md) (§3a–§3j build each flavor;
§5a–§5i give each round's comparison menu).

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

## Caveats

- One TRAIN (2008–17) / TEST (2018–26) split = one regime. The Sharpe CIs almost all span
  zero; every flavor's Deflated Sharpe is negative. This is an honest exploration of what
  the constructions *can* do, not a proven edge.
- The four-seasons inflation signal is the 10y yield 12m change (a rates proxy), not literal
  CPI. Real returns use CPI only if `--cpi-csv` is supplied; otherwise a harsh gold-deflated
  stress. Add a CPI series for true real-return accounting.
- The long1985 preset uses asset-class series that exist back to 1985; sleeves that only
  start in the ETF era (TIPS, GLD, DBC, UUP) are in `--preset modern`.

*Research / illustration only. Not investment advice.*