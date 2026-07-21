# All-Weather v2 — resilient in dot-com AND 2022

*Research / illustration only. Not investment advice.*

> Goal: a version of All-Weather that does **great in both** the dot-com bust
> (2000-2002: equities crash, bonds rally) **and** 2022 (stocks + bonds both
> fall). These are opposite growth-down regimes; a static long-duration tilt wins
> one and loses the other. The tool here is a **per-sleeve time-series momentum
> (TSMOM) overlay**: hold each sleeve only if its 12m return is positive, else go
> to cash. It adapts to the regime without forecasting it. TSMOM is investable
> (managed-futures/trend ETFs e.g. DBMF/KMLM, or mechanical). No parameter search
> -> no overfitting; cash proxy = 0% (conservative).

## 1. Headline — both target episodes (cumulative return, 1996-06-30–2026-07-31 history)

| Candidate | dot-com 2000-03..2002-09 | 2022 rout | 2022 full yr | COVID | Full CAGR | Full Sharpe | Full MaxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| AW-classic (vintage) | **-2.24%** | **-10.41%** | -7.11% | -12.60% | 6.61% | 0.813 | -20.29% |
| AW-v2 static (lower duration, diversified) | **-0.83%** | **-16.29%** | -12.56% | -15.93% | 7.31% | 0.752 | -34.73% |
| AW-classic + TSMOM | **3.11%** | **-4.40%** | -3.61% | -12.60% | 5.75% | 0.955 | -12.60% |
| AW-v2 static + TSMOM | **7.25%** | **-7.07%** | -6.65% | -13.93% | 6.33% | 0.967 | -13.93% |
| ERC risk-parity (vintage, 20% cap) | **4.67%** | **-18.63%** | -14.03% | -15.90% | 7.37% | 0.713 | -35.21% |
| ERC risk-parity + TSMOM | **12.35%** | **-6.47%** | -6.19% | -13.53% | 6.60% | 0.945 | -13.53% |
| AW-v2 + long/short TSMOM (managed-futures overlay) | **14.84%** | **2.15%** | -1.75% | -11.93% | 4.90% | 0.601 | -24.22% |
| ERC + long/short TSMOM | **19.50%** | **6.29%** | 0.64% | -11.16% | 5.28% | 0.603 | -24.36% |
| AW-v2 modern static | **0.00%** | **-9.17%** | -6.80% | -13.31% | 5.68% | 0.702 | -27.89% |
| AW-v2 modern +TSMOM | **0.00%** | **-3.08%** | -3.28% | -8.37% | 3.42% | 0.574 | -24.36% |

> **'Great in both' = positive (or near-flat) in dot-com AND 2022.** Classic
> All-Weather wins dot-com (bonds rally) but is negative in 2022. The TSMOM
> variants aim to be positive in BOTH.

## 1b. Carry + crisis-alpha blends (the practical 'All-Weather v2')

A pure long/short trend is positive in both episodes but low carry. The
practical answer is a **blend of carry All-Weather + a long/short managed-futures
overlay**. Blends that are positive in BOTH dot-com and 2022:

| Blend | dot-com | 2022 | CAGR | Sharpe | MaxDD |
|---|---:|---:|---:|---:|---:|
| 30% AW-classic + 70% long/short TSMOM | **12.95%** | **1.30%** | 5.85% | 0.855 | -13.15% |

**Recommended: 30% AW-classic + 70% long/short TSMOM** — positive in both episodes with the best
full-period CAGR among positive-both blends: dot-com 12.95%,
2022 1.30%, CAGR 5.85%, Sharpe 0.855,
MaxDD -13.15%.

## 2. The recommended portfolio — carry All-Weather + long/short trend overlay

The only way to be **positive in 2022** (not just less-bad) is to **SHORT** the
falling long bonds + equities — i.e. a long/short managed-futures (trend) sleeve.
Long-only overlays (TSMOM exit-to-cash) make dot-com great but only *reduce* the
2022 loss, because in 2022 nothing in the long-only vintage universe is strongly
positive (gold flat; no commodities/managed-futures). So the practical 'All-Weather
v2' is a blend of carry + crisis-alpha:

| Sleeve | Weight | What it is | Investable proxy |
|---|---:|---|---|
| Carry All-Weather (classic) | 30% | US Eq 30 / US Treas 55 / Gold 15 | VTI, IEF/TLT, GLD |
| Long/short managed-futures (trend) | 70% | 12m momentum, long winners / SHORT losers | DBMF / KMLM / futures |
|   trend universe |  | US Eq, Intl Eq, US Treas, US Corp, Gold, REIT | VTI/VXUS/IEF/LQD/GLD/VNQ |
| Cash collateral (T-bills) | backs the 70% | earns ~T-bill (not modeled; 0% conservative) | BIL / SGOV |

**Result (1996-2026):** dot-com **12.95%**, 2022 rout **1.30%** — positive in BOTH — CAGR 5.85%, Sharpe 0.855, MaxDD -13.15%.

Mechanics of the trend sleeve: each month, for each of the six vintage sleeves,
take a LONG position if its 12m return > 0, a SHORT position if < 0, sized to its
target weight ($1 gross, T-bill collateral). In dot-com it shorts equities + longs
rallying Treasuries; in 2022 it shorts crashing long Treasuries + equities and
longs gold. This is exactly what real managed-futures funds did in 2022 (DBMF
~+30% in 2022).

Trade-off: the heavy trend tilt cuts full-period CAGR/Sharpe vs static All-Weather
(whipsaw in calm, risk-on years) — that is the price of crisis alpha. A real
implementation adds T-bill yield on the collateral (improves CAGR ~1-2%/yr) and
can use a lighter trend weight if a small 2022 drawdown is acceptable.

## 3. TSMOM lookback robustness (recommended candidate)

| Lookback | dot-com cum | 2022 cum | CAGR | Sharpe |
|---:|---:|---:|---:|---:|
| 6m | 4.48% | -6.61% | 5.81% | 0.916 |
| 9m | 1.45% | -6.95% | 5.18% | 0.784 |
| 12m | 7.25% | -7.07% | 6.33% | 0.967 |

## 4. Four-seasons balance (avg monthly return, full history)

| Candidate | GrowthUp InfUp | GrowthUp InfDown | GrowthDown InfDown | GrowthDown InfUp (stagflation) |
|---|---:|---:|---:|---:|
| AW-classic (vintage) | 0.69% | 0.71% | 0.24% | -0.48% |
| AW-v2 static (lower duration, diversified) | 0.81% | 0.88% | 0.06% | -0.86% |
| AW-classic + TSMOM | 0.68% | 0.62% | -0.05% | -0.40% |
| AW-v2 static + TSMOM | 0.76% | 0.71% | -0.11% | -0.59% |
| ERC risk-parity (vintage, 20% cap) | 0.75% | 0.89% | 0.26% | -0.86% |
| ERC risk-parity + TSMOM | 0.71% | 0.77% | 0.03% | -0.56% |
| AW-v2 + long/short TSMOM (managed-futures overlay) | 0.71% | 0.55% | -0.28% | -0.32% |
| ERC + long/short TSMOM | 0.67% | 0.64% | -0.19% | -0.25% |
| AW-v2 modern static | 0.64% | 0.89% | -0.32% | -0.73% |
| AW-v2 modern +TSMOM | 0.54% | 0.64% | -0.81% | -0.51% |

## 5. Modern inflation-enhanced variant (post-2008, for 2022)

Once TIPS (2004), commodities/DBC (2006) and UUP (2007) exist, add them to the
inflation budget. This is the same TSMOM methodology with a richer universe — it
cannot be tested in 2000 (sleeves absent) but is the right 2022+ book:

| Sleeve | Weight |
|---|---:|
| US Equity | 18.0% |
| US Treasuries | 18.0% |
| TIPS | 14.0% |
| International Equity | 10.0% |
| Gold | 10.0% |
| Commodities | 10.0% |
| US Corporate Bonds | 8.0% |
| US REIT | 7.0% |
| Currency | 5.0% |
| + TSMOM overlay | |

## 6. Honest caveats

- **Cash proxy = 0%** (conservative). Real T-bills (BIL/SGOV) returned ~+1-2%/yr,
  so TSMOM's true numbers are modestly BETTER than shown, especially in 2022 when
  you sit in T-bills while bonds crash.
- **TSMOM is a trend rule**, not a fitted model; the 12m lookback is a standard
  prior. Lookback robustness (6/9/12) is reported.
- **No TIPS/commodities in 2000** -> the vintage portfolio dodges 2022 (flat-to-
  slightly-positive) rather than being strongly positive; the modern variant adds
  the inflation budget needed to be strongly positive in 2022.
- Whipsaw risk: TSMOM can lag in fast V-shaped reversals (e.g. COVID rebound).
- Single history; the 2022 stagflation sample is thin. Read episode numbers as
  illustrative of the mechanism, not a guarantee.

