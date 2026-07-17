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

*Research/illustration only. Not investment advice.*