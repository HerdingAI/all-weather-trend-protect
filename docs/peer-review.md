# Peer Review: Risk-Parity System (`risk_parity_eval.py` et al.)

*Critical-thinking analysis of the system's claim to deliver "positive uncorrelated
returns," with a focus on where All-Weather is weak (the both-down / stagflation
regime). Research / illustration only — not investment advice.*

## Headline verdict

The system is **honest and well-engineered** as a piece of quantitative plumbing:
walk-forward selection, Ledoit-Wolf shrinkage, a per-sleeve cap, transaction costs,
Deflated Sharpe, and block-bootstrap CIs are the right guardrails and are implemented
correctly. As **evidence for the central claim** — that some investable long-only
risk-parity portfolio delivers *positive, uncorrelated* returns in the regime where
All-Weather is weak — it is **not sufficient, and the most important finding is a
refutation rather than a confirmation**.

Three line-confirmed structural issues drove this conclusion (all addressed in the
"Changes applied" section below):

1. The 20% cap was applied **post-hoc** (`cap_weights` after the optimizer), so the
   reported "ERC/MinVar winner" was *not* an ERC/MinVar solution — clipped weights
   violate equal-risk-contribution / KKT, and the cap (not the optimizer) was the
   dominant allocator.
2. The both-down **reference baskets overlapped the candidate universe**, so a
   bond-heavy candidate mechanically scored well on "low equity correlation" just by
   holding bonds — the headline metric was partly tautological.
3. The long/short managed-futures (TSMOM) direction that **actually approaches the
   goal** sat in a separate report (`all_weather_v2.py`) with no DSR / walk-forward /
   bootstrap — the most promising answer was the *least* rigorously tested one
   (inverted evidence).

## §1. What is solid

- **Selection discipline.** TRAIN (2008–2017) selects; TEST (2018–2026) evaluates;
  a rolling pass re-runs the full combo×scheme search each January from trailing data
  only. This is the correct shape for guarding against selection bias.
- **Realistic frictions.** 20% per-sleeve cap, Ledoit-Wolf covariance shrinkage,
  10 bps/side costs on monthly-rebalance turnover, non-tradable VIX excluded by
  default. Few backtest repos include all of these.
- **Multiple-comparison awareness.** Deflated Sharpe Ratio (Bailey & López de Prado
  2014) and block-bootstrap CIs are present and used to temper the headline.
- **Separation of composition and allocation.** Five weighting schemes (EW, InvVol,
  InvVar, ERC, MinVar) over the same combo set cleanly separates "which sleeves"
  from "how they are weighted."
- **Honest reporting.** The existing `report_eval.md` §3 already states the DSR is
  ≈ 0 and that the both-down loss is reduced, not eliminated. The repo does not
  oversell.

## §2. Biases and structural issues

### §2a. Post-hoc cap → the reported ERC/MinVar winner is neither
`cap_weights` (clip-and-redistribute) was called *after* `s_erc`/`s_minvar`. Clipped
weights do not satisfy equal-risk-contribution (ERC) or the MinVar KKT conditions, so
the label "ERC winner" / "MinVar winner" was a misnomer. In practice the cap bound on
US Treasuries at exactly 20.0% every year — the cap, not the optimizer, was allocating.
**Fix applied:** cap is now enforced *inside* the solver via an exact Euclidean
projection onto the capped simplex (`project_capped_simplex`, validated to 0 error vs
a 200-iteration bisection reference over 20k random cases). MinVar is now a true
box-constrained QP; capped-ERC is a projected-gradient approximation (documented as
such; MinVar is the rigorous path and the empirical winner).

### §2b. Reference/universe tautology
The both-down mask and the "correlation with equity during both-down" metric were built
from sleeve baskets that overlap the candidate universe (all 5 bond sleeves and 3 of 4
equity sleeves are themselves the reference). A bond-heavy candidate scores well on
"low equity correlation" by construction, not by hedging. **Fix applied:** `--ref-mode
external` (now the default) builds the regime and the correlation metric from external
investable indices (equity = SPY, bond = AGG), decoupling the metric from the
candidates. `--ref-mode sleeves` reproduces the legacy behavior exactly (regression
guard).

### §2c. Inverted evidence on the promising direction
`all_weather_v2.py` shows a long/short managed-futures (TSMOM) blend delivering
**positive** returns in *both* the dot-com bust and 2022 stagflation — the exact
regime the brief targets. But that result lived in a separate report with none of the
eval pipeline's rigor (no DSR, no walk-forward, no bootstrap, no cost-Adjusted
re-enumeration). The most promising answer was the least-rigorously tested one.
**Fix applied:** LS-TSMOM is now a first-class scheme in the canonical pipeline
(`--schemes` default, TRAIN selection, TEST top-N, rolling re-enumeration), measured
on the same footing as risk parity (DSR, bootstrap CI, costs, head-to-head vs the
risk-parity winner and vs All-Weather in a new §9).

### §2d. Single regime / two blocks
TRAIN 2008–17 / TEST 2018–26 is one regime split into two blocks. The rolling pass
mitigates this but inherits the same universe and the same both-down definition. The
canonical four-seasons walk-forward (`risk_parity_seasons.py --preset long1985`, 8
folds, 1985–2026) is the more regime-robust view; this eval is the anchored-split
complement. **Status:** documented, not changed (out of scope this round).

### §2e. DSR effective-N and OOS application
DSR uses N = (number of trials) assuming independent trials. The trials are highly
correlated (overlapping combo membership, correlated sleeves), so the true effective N
is far smaller and DSR is **over-conservative** — a "DSR ≈ 0" verdict may understate
significance. Separately, DSR is applied to the OOS Sharpe of the TRAIN-selected winner
(a non-canonical but accepted variant of Bailey & López de Prado). **Fix applied:** an
effective-rank diagnostic (Σλ/λ_max of the de-meaned trial-return matrix) is now
computed and reported in §3/§6, and a caveat block discloses both points. A proper OOS
multiple-comparison test (Holm/Bonferroni over effective-N, or DSR on the TRAIN max) is
flagged as future work; the headline DSR number is unchanged.

### §2f. No vol-targeting / leverage
Long-only, no cash sleeve, no leverage. "Uncorrelated positive returns" in the both-down
regime from a *long-only* book is a hard ask — the genuine crisis-alpha sleeve
(managed futures) goes *short* the falling legs. This is why LS-TSMOM is the relevant
test, not a long-only risk-parity tilt. **Status:** documented; vol-targeting +
leverage is a separate, larger effort.

### §2g. Bond-sleeve total return
Bond sleeves use Yahoo adjusted close (ETF total return incl. distributions). The only
non-TR / non-investable sleeve was VIX, now excluded. No change needed.

## §3. Strategy-space gaps (did we explore the logical alternatives?)

The brief asks for an All-Weather variant that wins where All-Weather is weak. The
logical strategy space, in rough order of how directly each targets the weak regime:

1. **Long-only risk-parity tilts (EW/InvVol/InvVar/ERC/MinVar over the sleeve combo
   space).** The original system. Result: *dampens* the both-down loss vs All-Weather,
   does not produce positive both-down returns OOS. Honest negative result.
2. **Long-only TSMOM ("exit to cash if 12m return < 0").** Great in dot-com (bonds
   still rally, equities exit), only *reduces* 2022 (both legs fall, cash saves you
   from the loss but doesn't make you positive). Half-measure for the target regime.
3. **Long/short managed-futures (LS-TSMOM).** Short the falling legs → genuinely
   positive in 2022. This is the strategy that matches the brief. Now measured in the
   canonical pipeline (§9).
4. **Regime-conditioned allocation / CVaR / carry.** Documented next steps
   (`risk_parity.md` caveats); out of scope this round.

The critical-thinking point: the system's *original* answer space (1) cannot, by
construction, deliver the brief's goal from a long-only book in a both-down regime.
(3) is the first strategy in the explored space that *can*, and folding it into the
rigorous pipeline is the substantive change.

## §4. "Uncorrelated" is measured, and it refutes the long-only claim

The repo does the right thing: "uncorrelated positive returns" is operationalized as
(diversification ratio) + (correlation with the equity reference during both-down
months, penalized in the score). It is not assumed — it is measured. And what it
measures, for the long-only risk-parity winner, is a *reduction* in equity correlation
and a *reduction* in the both-down loss, not zero correlation and not positive
both-down returns. The metric, once de-tautologized (Fix 2), says the same thing less
flatteringly. This is the central honest finding: **you can meaningfully dampen the
All-Weather weak spot with investable long-only sleeves, not eliminate it.**

## §5. Bottom line

- The long-only risk-parity search **does not** deliver positive uncorrelated returns
  in the both-down regime, and the prior in-sample numbers were the optimization
  objective reported back, not evidence. Fix 1 + Fix 2 make the measurement honest;
  the honest measurement confirms the negative.
- The long/short managed-futures direction **does** approach the goal and is now
  measured on the same footing (Fix 3). Whether it survives DSR / walk-forward /
  bootstrap is an empirical question the regenerated `report_eval.md` §9 answers —
  measured, not assumed.
- The DSR caveat (Fix 4) keeps the multiple-comparison guardrail honest about its own
  assumptions.

## Changes applied (this review → code)

| Fix | What changed | Where |
|---|---|---|
| 1 | Cap enforced **inside** the MinVar/ERC solver via exact capped-simplex projection (not post-hoc clip). MinVar = true box-constrained QP; capped-ERC = documented projected-gradient approximation. | `risk_parity_eval.py` `project_capped_simplex`, `s_minvar`, `s_erc_capped` |
| 2 | Both-down regime + equity-correlation metric built from **external investable indices** (SPY / AGG), decoupled from the candidate universe. `--ref-mode external` (default); `--ref-mode sleeves` reproduces legacy. | `risk_parity_eval.py` `--ref-mode`, `both_down_mask_from_series`, ref-series construction |
| 3 | **LS-TSMOM** managed-futures scheme folded into the canonical pipeline (TRAIN, TEST top-N, winner, rolling) on equal footing: DSR, block-bootstrap CI, costs, head-to-head vs risk-parity winner and All-Weather. New `--tsmom-lookback` (default 12). | `risk_parity_eval.py` `s_ls_tsmom`, `_backtest_ls_tsmom`, `write_report` §9 |
| 4 | DSR **effective-N** diagnostic (Σλ/λ_max of the trial-return matrix) + caveat block disclosing (a) independence assumption → over-conservative, (b) OOS-application variant. Headline DSR unchanged. | `risk_parity_eval.py` `fast_search` attrs → diag → `write_report` §3/§6 |

**Reproduction:**
```bash
.venv/bin/python risk_parity_eval.py                       # canonical (external ref, LS-TSMOM on)
.venv/bin/python risk_parity_eval.py --ref-mode sleeves    # legacy regression guard
.venv/bin/python risk_parity_eval.py --tsmom-lookback 6    # momentum-signal robustness
```

**Measured outcomes** (canonical run: `--ref-mode external`, 12 sleeves, 2817 combos
× 6 schemes = 16,902 trials, TRAIN 2008–17 / TEST 2018–26, 20% cap, 10 bps/side, Ledoit-Wolf).
The authoritative numbers are in the regenerated `output/risk_parity_eval/report_eval.md`;
the key ones:

- **Both-down regime (now external SPY/AGG, Fix 2):** 17 TRAIN / 24 TEST months (was
  53/26 under the sleeve-overlap reference — the tautology inflated the count and the
  metric; the de-tautologized metric is harsher).
- **Risk-parity winner** — MinVar on [US Equity, US Treasuries, US Municipal Bonds,
  Gold, Silver, Currency]:
  - OOS net Sharpe **1.518**; both-down ann **−11.42%**; Max DD **−5.61%**.
  - **Cap integrity (Fix 1):** winner max sleeve weight = 20.00% = cap → the solver
    output already respects the cap; the post-hoc clip is a no-op (the property the
    label "MinVar" claims is now actually true).
  - DSR **0.056** (P>0 = 0.56); block-bootstrap 95% CI on Sharpe [0.872, 2.354].
  - vs All-Weather (Sharpe 1.055, both-down −18.74%, MaxDD −12.31%): the winner
    **dampens** the both-down loss by ~7.3 pp and cuts MaxDD by more than half — but
    the both-down return is still **negative** OOS.
- **Effective N (Fix 4):** participation ratio of the TRAIN trial-return matrix =
  **1.2** vs nominal 16,902 trials. This confirms DSR's independence assumption is
  massively violated and the headline DSR is a conservative upper bound on the
  multiple-comparison penalty (the edge may be more significant than DSR suggests).
- **LS-TSMOM (Fix 3) head-to-head on TEST:**

  | Metric | All-Weather | Risk-parity winner | **LS-TSMOM** |
  |---|---:|---:|---:|
  | Net Sharpe | 1.055 | 1.518 | **0.347** |
  | Both-down ann ret | −18.74% | −11.42% | **−4.82%** |
  | Both-down hit rate | 16.7% | 20.8% | **37.5%** |
  | Corr w/ equity | 0.885 | 0.762 | **0.129** |
  | Crisis avg ret | −3.04% | −1.29% | **−2.09%** |
  | Max DD | −12.31% | −5.61% | −23.70% |

  - DSR −0.964 (P>0 = 0.00; n_trials = 2817); bootstrap 95% CI on Sharpe [−0.482,
    1.213]; on both-down [−10.45%, +3.14%].
  - **Verdict:** LS-TSMOM is the direction that **most reduces** the All-Weather weak
    spot — smallest both-down loss of the three (−4.82% vs −11.42% vs −18.74%), highest
    both-down hit rate (37.5%), and near-zero equity correlation (0.129 — the
    "uncorrelated" the brief asks for, measured not assumed). But it does **not** flip
    the both-down regime positive OOS (CI straddles 0: [−10.45%, +3.14%]), its Sharpe edge
    is **not statistically significant** (DSR < 0, Sharpe CI straddles 0), its crisis
    average is still negative (−2.09%, better than AW's −3.04% but worse than the
    risk-parity winner's −1.29%), and its full-period Sharpe (0.35) is far below the
    long-only portfolios — the whipsaw cost of crisis alpha in a single,
    mostly-non-stagflation TEST window. This is the measured, not assumed, answer:
    long/short managed futures is the right *direction* for the brief, but in this window
    it dampens rather than eliminates the All-Weather weakness, and the ranking is not
    significant.

## Out of scope / future work

- Vol-targeting + leverage + a cash/T-bill sleeve (would let risk-parity *scale*
  risk rather than just allocate it).
- A proper OOS multiple-comparison test (Holm/Bonferroni over effective-N, or DSR on
  the TRAIN max).
- Regime-conditioned allocation, CVaR, carry overlays.
- LS-TSMOM vol-scaling (currently equal-weight `base_w` for neutrality) and a real
  T-bill collateral return (currently 0% conservative; real collateral adds ~1–2%/yr).

*Research / illustration only. Not investment advice.*