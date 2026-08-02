"""
candidates.py -- the fixed set of allocations this study compares.

FIXED IN ADVANCE, ON PURPOSE
----------------------------
Walk-forward showed that searching for an optimum does not survive contact with
not knowing the future: every drawdown ceiling was breached out of sample by
25-45 points, ~5pp of return evaporated at every level, and the mechanism was a
2006 refit that put 100% into US REIT because REITs had high return and no large
drawdown over 1996-2006. The GFC then took REITs down 62%.

So the deliverable is no longer "which book won a search" but "how do a few
simple, defensible allocations compare". Choosing that set AFTER seeing results
would reintroduce exactly the bias walk-forward exposed, so the set is declared
here, once, before any comparison runs.

WHY THESE, SPECIFICALLY
-----------------------
References are the user's own books plus the market, so every number has a
familiar anchor.

The variants exist because of ONE measured fact, not a story: gold and long
Treasuries protect on different axes.

    crisis        gold      long treasuries
    dot-com      + 7.9%          +36.4%
    GFC          +15.5%          +24.9%
    COVID        + 3.7%          +22.1%
    2022         -10.9%          -34.1%
    Volcker      -10.8%            n/a

Each covers the other's failure: 2022 destroyed duration while gold was merely
soft; dot-com was duration's best moment while gold did little. Holding both is
therefore the one structural idea the data supports without a search, and the
variants are simply that idea at a few sensible weights.

Nothing here is tuned. The weights are round numbers.
"""
from __future__ import annotations

# Reference books: the user's current holdings, the candidate they were
# considering, and the market -- so every comparison has a familiar anchor.
REFERENCES = {
    "Current allocation": {
        "US Total Market": 0.50, "US Large Cap": 0.05, "US Small Value": 0.07,
        "US Small Cap": 0.02, "Intl Developed": 0.18, "Gold": 0.18},
    "80/20 VTI-GLD": {"US Total Market": 0.80, "Gold": 0.20},
    "60/20/20 US-intl-gold": {
        "US Total Market": 0.60, "Intl Developed": 0.20, "Gold": 0.20},
    "100% US Total": {"US Total Market": 1.00},
    "S&P 500": {"US Large Cap": 1.00},
    "Classic 60/40": {"US Total Market": 0.60, "US Aggregate Bonds": 0.40},
}

# Variants: equity plus BOTH protective assets, at round weights.
VARIANTS = {
    "70/15/15 eq-gold-dur": {
        "US Total Market": 0.70, "Gold": 0.15, "Long Treasuries": 0.15},
    "60/20/20 eq-gold-dur": {
        "US Total Market": 0.60, "Gold": 0.20, "Long Treasuries": 0.20},
    "50/25/25 eq-gold-dur": {
        "US Total Market": 0.50, "Gold": 0.25, "Long Treasuries": 0.25},
    # Same idea with aggregate bonds instead of long Treasuries: less duration
    # risk, which matters because long Treasuries lost 34% in 2022.
    "60/20/20 eq-gold-agg": {
        "US Total Market": 0.60, "Gold": 0.20, "US Aggregate Bonds": 0.20},
    # Adds international equity to the three-way mix, since the user's own books
    # carry it and it behaves differently enough to be worth isolating.
    "45/15/20/20 +intl": {
        "US Total Market": 0.45, "Intl Developed": 0.15,
        "Gold": 0.20, "Long Treasuries": 0.20},
}

CANDIDATES = {**REFERENCES, **VARIANTS}

# The user's incumbent and the book they were considering, named so reports can
# always show the comparison that actually matters to them.
INCUMBENT = "Current allocation"
CONSIDERING = "80/20 VTI-GLD"


def assets_used() -> set[str]:
    return {a for w in CANDIDATES.values() for a in w}


def check_weights() -> None:
    """Every book must be long-only and fully invested."""
    for name, w in CANDIDATES.items():
        total = sum(w.values())
        if abs(total - 1.0) > 1e-9:
            raise SystemExit(f"{name}: weights sum to {total:.4f}, not 1.0")
        for a, x in w.items():
            if x < 0:
                raise SystemExit(f"{name}: {a} has negative weight {x}")


check_weights()
