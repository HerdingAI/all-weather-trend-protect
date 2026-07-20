# Stock_Price

Daily + monthly prices and returns for **342 tickers** from Yahoo Finance, as far back
as Yahoo provides (daily to **1927**, monthly to **1962**, through **2026-07**).

→ **Full documentation: [`docs/README.md`](docs/README.md)**

Quick links:
- [Data dictionary](docs/data_dictionary.md) — every output file, field-by-field
- [Coverage](docs/coverage.md) — date ranges, per-ticker / per-asset-class / per-sector
- [Methodology](docs/methodology.md) — how values are derived
- [Nuances & caveats](docs/nuances_and_caveats.md) — data quirks + integrity-audit triage
- [Scripts reference](docs/scripts_reference.md) — the 3 scripts, config, reproducibility

## Quick start
```bash
pip install -r requirements.txt
.venv/bin/python pull_returns.py     # monthly
.venv/bin/python pull_daily.py       # daily (cached in output/daily_prices.parquet)
.venv/bin/python audit_integrity.py  # integrity report
```

Integrity status: **0 FAIL · 27 PASS · 12 WARN (all benign)** — see
[`output/integrity_findings.md`](output/integrity_findings.md).

## Risk-parity portfolio search
Four scripts, built on `output/monthly_returns_by_asset_class.csv`. **Canonical = v3
`risk_parity_seasons.py --preset long1985`** — backtests to **1985 (~41 years)** using the
investable-as-of-1985 sleeves (equities, treasuries, corporates, munis, gold), four-seasons
walk-forward CV across ~8 regimes, stagflation weighted 2x, real returns. `--preset modern`
uses the richer 2008+ ETF universe (TIPS, gold, silver, commodities, UUP). `risk_parity_eval.py` (v2, anchored train/test + 5 weighting
schemes) and `risk_parity_backtest.py` (v1, in-sample composition search) are secondary /
appendix. All: long-only, 20% per-sleeve cap, Ledoit-Wolf shrinkage, 10 bps costs,
Deflated Sharpe, block-bootstrap CIs; Volatility (^VIX, non-tradable) excluded.
Full docs: [`docs/risk_parity.md`](docs/risk_parity.md). Canonical report:
[`output/risk_parity_seasons/report_seasons.md`](output/risk_parity_seasons/report_seasons.md)
(long1985); modern preset in `output/risk_parity_seasons_modern/`.

### Peer review of the eval pipeline
[`docs/peer-review.md`](docs/peer-review.md) is a critical review of `risk_parity_eval.py`
(v2). It found the eval honest but not sufficient as evidence for "positive uncorrelated
returns" in the both-down/stagflation regime, and drove four methodology fixes now in the
code: cap enforced **inside** the MinVar/ERC solver (not post-hoc), both-down reference
decoupled to external SPY/AGG, **LS-TSMOM** managed-futures folded into the canonical
pipeline, and a DSR effective-N disclosure. The peer-reviewed anchored-split report is
[`output/risk_parity_eval/report_eval.md`](output/risk_parity_eval/report_eval.md).

```bash
.venv/bin/python risk_parity_seasons.py        # canonical (four-seasons walk-forward)
.venv/bin/python risk_parity_seasons.py --cpi-csv cpi.csv   # true CPI real returns
.venv/bin/python risk_parity_eval.py           # v2 anchored split
.venv/bin/python risk_parity_backtest.py       # v1 in-sample (appendix)
```

*Research/illustration only. Not investment advice.*