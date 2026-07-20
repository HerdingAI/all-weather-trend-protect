# Risk-Parity Asset-Class Combination Search

Two scripts, built on `output/monthly_returns_by_asset_class.csv` (the 19 asset-class
buckets from `pull_returns.py`).

## `risk_parity_backtest.py` — IN-SAMPLE composition search (method appendix)
Enumerates every asset-class combination (≥1 equity + ≥1 bond sleeve) and backtests
each under long-only Equal-Risk-Contribution (ERC) risk parity, scoring by resilience
to "both-down" months (broad equity AND broad bond references both negative) + named
crisis windows, vs All-Weather. **This is in-sample** (ranked on the same window it is
backtested on) → it OVERSTATES performance. Its `report.md` carries a banner demoting it
to a method appendix. **Volatility (^VIX, non-tradable) is excluded by default**
(`--include-volatility` opts back in, illustration only).

## `risk_parity_seasons.py` — CANONICAL (v3): four-seasons walk-forward, real returns
This is the report to cite (after the regime/inflation critiques). It replaces the
single 10y/8y train-test split with **walk-forward cross-validation** across the full
2008-2026 multi-regime history (GFC, ZIRP, taper, hiking, COVID, 2022 stagflation,
2023 bank stress): 4 expanding-window folds, OOS equity curve = concatenation of every
fold's held-out test. Scoring uses **Bridgewater's four economic seasons** (growth x
inflation) with **stagflation weighted 2x** (the All-Weather weak spot). A dedicated
**TIPS** sleeve + gold/silver/commodities are in the universe so the optimizer CAN
defend inflation, and **real returns** are reported (CPI via `--cpi-csv`, else a harsh
gold-deflated purchasing-power stress). All v2 rigor retained (20% cap, Ledoit-Wolf,
10 bps costs, 5 schemes, Deflated Sharpe, bootstrap CIs, diversification + correlations,
Volatility excluded).

Presets: `--preset long1985` (CANONICAL — backtests to **1985 (~41y)** using the investable-as-of-1985 sleeves: equities + treasuries + corporates + munis + gold via the VGPMX/gold-futures TR proxy; 8 walk-forward folds, OOS 1995–2026) and `--preset modern` (2008+, 13 sleeves incl TIPS; richer search, shorter history).

Run: `.venv/bin/python risk_parity_seasons.py --preset long1985`  (options: `--cpi-csv PATH`,
`--schemes ...`, `--cap`, `--cost-bps`, `--min-train-years`, `--test-years`).
Outputs in `output/risk_parity_seasons/`: `report_seasons.md` (canonical),
`oos_walkforward_returns.csv`, `per_fold.csv`, `diagnostics.csv`,
`train_results_all_folds.csv` (gitignored). Modern-preset outputs in `output/risk_parity_seasons_modern/`.

## `risk_parity_eval.py` — secondary out-of-sample, anti-overfit, allocation-aware eval
It adds (superseded by v3 for regime robustness, but still useful for the anchored-split view):

- **Composition vs allocation:** every combination is backtested under FIVE weighting /
  risk-profile schemes (EW, InvVol, InvVar, ERC, MinVar) so *which sleeves* is separated
  from *how they are weighted*.
- **No overfitting:** selection on TRAIN (2008–2017) only; evaluation on held-out TEST
  (2018–2026); **rolling walk-forward selection that re-runs the FULL combo×scheme search
  each January from trailing data only** (not a TRAIN shortlist); overfit diagnostics
  (score dispersion, winner z, top-10 train→test stability, Spearman rank persistence,
  train/test degradation).
- **Investable & realistic:** Volatility (^VIX) excluded by default; **20% per-sleeve cap**
  (no 47% single-ETF macro bets); **Ledoit-Wolf covariance shrinkage**; **transaction
  costs net of 10 bps/side** with monthly-rebalance turnover.
- **Objective encoded:** the score includes **diversification ratio** and a penalty for
  **correlation with the equity reference during both-down months** ("uncorrelated
  positive returns" is measured, not assumed). Both are reported in the headline.
- **Multiple-comparison adjusted:** **Deflated Sharpe Ratio** (Bailey & López de Prado
  2014) given the number of trials, plus block-bootstrap 95% CIs on OOS Sharpe and
  both-down return.

Run:
```bash
.venv/bin/python risk_parity_eval.py                 # canonical (default)
.venv/bin/python risk_parity_eval.py --include-volatility   # add ^VIX (illustrative)
.venv/bin/python risk_parity_eval.py --cap 0.25 --cost-bps 15   # tune constraints
.venv/bin/python risk_parity_eval.py --no-rolling     # skip the expensive rolling pass
.venv/bin/python risk_parity_eval.py --help
```

Outputs in `output/risk_parity_eval/`:
`report_eval.md` (canonical), `overfit_diagnostics.csv`, `scheme_comparison_test.csv`,
`test_eval_topN.csv`, `rolling_selection_log.csv`, `oos_rolling_returns.csv`,
`train_results.csv` (gitignored — large, regenerable).

## Headline takeaway (read `report_eval.md` §3 before trusting any number)
With the non-tradable VIX sleeve removed, a 20% concentration cap, costs, and shrinkage,
the best **investable** long-only risk-parity portfolio **reduces** the both-down loss vs
All-Weather out-of-sample (winner both-down ≈ −8% vs All-Weather ≈ −19%; lower drawdown,
lower equity correlation) but does **not** deliver positive both-down returns OOS, and
the **Deflated Sharpe is ≈ 0** (the Sharpe edge is not statistically significant after
accounting for the ~16,500 trials). Honest conclusion: you can meaningfully dampen the
All-Weather weak spot, not eliminate it, with these investable sleeves.

## Caveats / not yet implemented
- One regime / two blocks (TRAIN 2008–17, TEST 2018–26); DSR + bootstrap are guardrails.
- No vol target (infeasible without leverage + a cash/T-bill sleeve).
- Regime-conditioned / CVaR / momentum overlays (review item 10) are documented next steps.
- Bond sleeves use Yahoo adjusted close (ETF total return incl. distributions); the only
  non-TR / non-investable sleeve was Volatility, now excluded.

*Research / illustration only. Not investment advice.*

## `all_weather_v2.py` — the "great in dot-com AND 2022" portfolio
The focused answer to the final ask: an All-Weather variant that does GREAT in
BOTH the dot-com bust (2000-2002, deflationary equity crash, bonds rally) AND
2022 (stocks + bonds both fall = stagflation) — two *opposite* growth-down
regimes. A static long-duration tilt wins one and loses the other. The tool is a
**per-sleeve time-series-momentum (TSMOM) overlay**: long-only "exit to cash if
12m return < 0" makes dot-com great but only *reduces* 2022; to be **positive in
2022** you must **short** the falling bonds+equities, i.e. a **long/short
managed-futures (trend) sleeve** (investable via DBMF/KMLM or futures).
**Recommended: 30% carry All-Weather + 70% long/short trend** → dot-com
**+13.0%**, 2022 **+1.3%** (positive in BOTH), CAGR ~5.9%, Sharpe ~0.86 (1996-2026,
cash proxy 0% conservative). Trade-off: lower CAGR/Sharpe than static (whipsaw in
calm markets) — the price of crisis alpha.

Run: `.venv/bin/python all_weather_v2.py`  → `output/all_weather_v2/report_awv2.md`
(headline both-episode table, blends, TSMOM lookback robustness, four seasons).
