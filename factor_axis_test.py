"""
factor_axis_test.py -- is a small-value sleeve a THIRD uncorrelated return
source, in the way gold and long Treasuries are?

THE QUESTION, PRECISELY
-----------------------
Not "is DFA a good manager" and not "how much small value should we hold".
Gold and long Treasuries earned their place in the candidate books by a
measured property: they protect on different crisis axes, so each covers the
other's failure. This asks whether small value clears the SAME bar.

WHY TWO FREQUENCIES
-------------------
The monthly answer is already clear and negative: in the worst decile of US
months small value falls harder than the market. But gold and duration hedge
at MONTHLY frequency, whereas small value's dot-com behaviour was a 30-month
regime divergence. Testing a regime claim with a monthly-tail statistic is a
category error, and Q2 was already closed once on a single lens and was wrong.

So three lenses, and the regime lens is the genuine test:

  monthly  -- tail correlation, conditional mean, up-rate in bad months
  regime   -- overlapping 36/60m excess-vs-market, and whether small value's
              excess is UNCORRELATED with the gold and duration excesses
  episode  -- named crises plus the dot-com run-up, so the participation cost
              appears next to the payoff rather than after it

DECISION RULE, WRITTEN BEFORE RUNNING
-------------------------------------
Small value earns a place as a third axis only if BOTH:
  (a) its regime-frequency excess is materially uncorrelated with the gold and
      duration excesses, AND
  (b) it does not worsen the drawdown that the ladder constrains.
Higher raw return alone is NOT sufficient. That would make it a return sleeve,
not a diversifier, and the ladder already prices return against drawdown.

CALIBRATION -- an absolute threshold on (a) is WRONG
----------------------------------------------------
The rule above was first written with an absolute bar of |corr| < 0.30 on the
excess series. Running it exposed the flaw: gold and duration, the two sleeves
already ACCEPTED as separate axes, correlate 0.646 with each other on that
metric. The bar would reject the very pair it is meant to describe.

The cause is mechanical. Every excess series shares a `-market` term, so when
the market falls, everything-not-market looks good simultaneously. Raw gold and
duration correlate 0.192; their excesses correlate 0.646. The inflation is an
artifact of the measure, not a property of the assets.

So (a) is judged AGAINST THE GOLD/DURATION PAIR as a calibrated control -- the
same device as GLD/IAU for "what same-asset agreement looks like". Small value
qualifies on (a) only if it is no more correlated with the protective sleeves
than they already are with each other.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

import pv_series as PV

HERE = os.path.dirname(os.path.abspath(__file__))
PANEL_CSV = os.path.join(HERE, "output", "study_panel.csv")
OUT_DIR = os.path.join(HERE, "output", "factor_axis")

# Threshold for "materially uncorrelated" in the decision rule above.
AXIS_CORR_MAX = 0.30

# Episodes. The run-up is included on purpose: measuring only from 2000-03
# counts small value's payoff and hides the premium paid for it.
EPISODES = {
    "dot-com run-up":   ("1995-01", "2000-02"),
    "dot-com unwind":   ("2000-03", "2002-09"),
    "dot-com round trip": ("1995-01", "2002-09"),
    "GFC":              ("2007-11", "2009-02"),
    "COVID":            ("2020-02", "2020-03"),
    "2022":             ("2022-01", "2022-09"),
}


# ---------------------------------------------------------------- primitives

def maxdd(r: pd.Series) -> float:
    c = (1 + r).cumprod()
    return float(((c / c.cummax()) - 1).min() * 100)


def cagr(r: pd.Series) -> float:
    return float(((1 + r).prod() ** (12 / len(r)) - 1) * 100)


def cum(r: pd.Series) -> float:
    return float(((1 + r).prod() - 1) * 100)


def sortino(r: pd.Series, mar: float = 0.0) -> float:
    """MAR=0 Sortino: downside deviation measured about 0, not about the
    clipped series' own mean. Matches profile_study_panel.stats."""
    dsd = float(np.sqrt((np.minimum(r - mar, 0.0) ** 2).mean()) * np.sqrt(12))
    if dsd == 0:
        return float("inf")
    return float((r.mean() - mar) * 12 / dsd)


def tail_stats(x: pd.Series, market: pd.Series, q: float) -> dict:
    """Behaviour of `x` in the worst `q` quantile of `market` months."""
    cut = market.quantile(q)
    m = market[market <= cut]
    t = x.loc[m.index]
    return dict(n=len(m), mkt_mean=float(m.mean() * 100),
                corr=float(t.corr(m)), mean=float(t.mean() * 100),
                up_rate=float((t > 0).mean() * 100))


def rolling_excess(x: pd.Series, market: pd.Series, months: int) -> pd.Series:
    """Annualised excess of `x` over `market` on overlapping windows.

    Includes the window that STARTS at inception -- the same off-by-one that
    was fixed in drawdown_ladder.worst_rolling. Implemented by compounding
    with a leading unit wealth rather than by slicing.
    """
    wx = np.r_[1.0, (1 + x).cumprod().values]
    wm = np.r_[1.0, (1 + market).cumprod().values]
    if len(wx) <= months:
        return pd.Series(dtype=float)
    gx = wx[months:] / wx[:-months]
    gm = wm[months:] / wm[:-months]
    ann = (gx ** (12 / months) - gm ** (12 / months)) * 100
    return pd.Series(ann, index=x.index[months - 1:])


# ------------------------------------------------------------------- loading

def load_inputs() -> pd.DataFrame:
    """Panel sleeves plus the evidence-only DFA series, on a common window."""
    p = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)
    dfsvx = PV.load_pv_csv(
        os.path.join(HERE, "data", "dfsvx_monthly_returns.csv")
    )["monthly_return"] / 100.0
    dfscx = PV.load_pv_csv(
        os.path.join(HERE, "data", "dfscx_monthly_returns.csv")
    )["monthly_return"] / 100.0
    df = pd.concat([
        p["US Total Market"].rename("market"),
        p["Gold"].rename("gold"),
        p["Long Treasuries"].rename("duration"),
        p["Intl Developed"].rename("intl"),
        dfsvx.rename("smallval"),
        dfscx.rename("microcap"),
    ], axis=1, sort=True).dropna()
    return df


# --------------------------------------------------------------------- lenses

def lens_monthly(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in ("gold", "duration", "smallval", "microcap", "intl"):
        r = dict(sleeve=name, corr_full=float(d[name].corr(d["market"])))
        for q, lab in ((0.10, "d10"), (0.20, "q20")):
            t = tail_stats(d[name], d["market"], q)
            r[f"{lab}_corr"] = t["corr"]
            r[f"{lab}_mean"] = t["mean"]
            r[f"{lab}_up"] = t["up_rate"]
        rows.append(r)
    return pd.DataFrame(rows).set_index("sleeve")


def lens_regime(d: pd.DataFrame, months: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Excess-vs-market on overlapping windows, and how those excesses relate.

    The diversification question is NOT whether each sleeve beats the market.
    It is whether they beat it at DIFFERENT TIMES. That is exactly the
    correlation between their excess series.
    """
    ex = pd.DataFrame({
        s: rolling_excess(d[s], d["market"], months)
        for s in ("gold", "duration", "smallval", "microcap", "intl")
    }).dropna()
    summary = pd.DataFrame({
        "mean_excess": ex.mean(),
        "win_rate": (ex > 0).mean() * 100,
        "worst": ex.min(),
        "best": ex.max(),
    })
    return summary, ex.corr()


def lens_episode(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, (lo, hi) in EPISODES.items():
        w = d.loc[lo:hi]
        if w.empty:
            continue
        row = {"episode": name, "n": len(w)}
        for s in ("market", "gold", "duration", "smallval", "microcap"):
            row[s] = cum(w[s])
        rows.append(row)
    return pd.DataFrame(rows).set_index("episode")


def verdict(regime_corr: pd.DataFrame, monthly: pd.DataFrame,
            sleeve: str = "smallval") -> dict:
    """Apply the decision rule, calibrated against the gold/duration control.

    See the CALIBRATION note at the top: an absolute correlation bar rejects
    gold and duration themselves, so the accepted pair sets the reference.
    """
    control = abs(float(regime_corr.loc["gold", "duration"]))
    c_gold = abs(float(regime_corr.loc[sleeve, "gold"]))
    c_dur = abs(float(regime_corr.loc[sleeve, "duration"]))
    # No more correlated with the protective sleeves than they are with each
    # other. Compared to the control, not to an invented constant.
    uncorrelated = max(c_gold, c_dur) <= control

    # (b) does it worsen the tail the ladder actually constrains? The market
    # row must be present; failing loudly beats silently testing against 0.
    if "market" not in monthly.index:
        raise ValueError("monthly stats need a 'market' row to judge the tail")
    amplifies = bool(monthly.loc[sleeve, "d10_mean"]
                     < monthly.loc["market", "d10_mean"])

    return dict(sleeve=sleeve, control_gold_duration=control,
                corr_vs_gold=c_gold, corr_vs_duration=c_dur,
                uncorrelated=bool(uncorrelated), amplifies_tail=amplifies,
                is_third_axis=bool(uncorrelated and not amplifies))


# ----------------------------------------------------------------------- main

def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    d = load_inputs()
    print(f"window {d.index.min():%Y-%m} .. {d.index.max():%Y-%m}  n={len(d)}\n")

    print("=" * 72)
    print("LENS 1  MONTHLY -- behaviour in the tail that sets the drawdown")
    print("=" * 72)
    m = lens_monthly(d)
    mkt = tail_stats(d["market"], d["market"], 0.10)
    print(f"  worst decile of market months: n={mkt['n']}, "
          f"market {mkt['mean']:+.2f}%/mo\n")
    print(f"  {'sleeve':10s} {'corr':>7s} {'d10corr':>8s} {'d10mean':>9s} "
          f"{'d10up%':>7s}")
    for s in m.index:
        r = m.loc[s]
        print(f"  {s:10s} {r['corr_full']:+7.3f} {r['d10_corr']:+8.3f} "
              f"{r['d10_mean']:+8.2f}% {r['d10_up']:6.0f}%")
    m.to_csv(os.path.join(OUT_DIR, "lens_monthly.csv"))

    print("\n" + "=" * 72)
    print("LENS 2  REGIME -- do they beat the market at DIFFERENT TIMES?")
    print("=" * 72)
    regime_corrs = {}
    for months in (36, 60):
        summary, corr = lens_regime(d, months)
        regime_corrs[months] = corr
        print(f"\n  {months}-month overlapping windows "
              f"(n={len(d) - months + 1}), annualised excess vs market:")
        print(f"  {'sleeve':10s} {'mean':>8s} {'win%':>7s} {'worst':>8s} "
              f"{'best':>8s}")
        for s in summary.index:
            r = summary.loc[s]
            print(f"  {s:10s} {r['mean_excess']:+7.2f}pp {r['win_rate']:6.0f}% "
                  f"{r['worst']:+7.2f} {r['best']:+7.2f}")
        print(f"\n  correlation BETWEEN the excess series ({months}m) --"
              f" this is the diversification question:")
        print("   " + corr.round(3).to_string().replace("\n", "\n   "))
        summary.to_csv(os.path.join(OUT_DIR, f"lens_regime_{months}m.csv"))
        corr.to_csv(os.path.join(OUT_DIR, f"lens_regime_{months}m_corr.csv"))

    print("\n" + "=" * 72)
    print("LENS 3  EPISODE -- payoff and the price paid for it")
    print("=" * 72)
    e = lens_episode(d)
    print("  " + e.round(1).to_string().replace("\n", "\n  "))
    e.to_csv(os.path.join(OUT_DIR, "lens_episode.csv"))

    print("\n" + "=" * 72)
    print("VERDICT  against the rule written before running")
    print("=" * 72)
    mm = m.copy()
    mm.loc["market"] = {"corr_full": 1.0, "d10_corr": 1.0,
                        "d10_mean": mkt["mean"], "d10_up": mkt["up_rate"],
                        "q20_corr": np.nan, "q20_mean": np.nan,
                        "q20_up": np.nan}
    rows = []
    for sleeve in ("smallval", "microcap", "intl"):
        v = verdict(regime_corrs[36], mm, sleeve)
        rows.append(v)
        print(f"\n  {sleeve}")
        print(f"    (a) regime excess no more correlated with the protective")
        print(f"        sleeves than they are with each other?")
        print(f"          control |corr(gold, duration)| = "
              f"{v['control_gold_duration']:.3f}")
        print(f"          |corr vs gold|     {v['corr_vs_gold']:.3f}")
        print(f"          |corr vs duration| {v['corr_vs_duration']:.3f}")
        print(f"        -> {'PASS' if v['uncorrelated'] else 'FAIL'}")
        print(f"    (b) leaves the constrained tail no worse?")
        print(f"          worst decile {m.loc[sleeve, 'd10_mean']:+.2f}%/mo "
              f"vs market {mkt['mean']:+.2f}%/mo")
        print(f"        -> {'FAIL (amplifies)' if v['amplifies_tail'] else 'PASS'}")
        print(f"    THIRD UNCORRELATED AXIS: "
              f"{'YES' if v['is_third_axis'] else 'NO'}")

    # Sanity control: gold and duration must pass their own test against each
    # other, or the metric is broken rather than the sleeve.
    print("\n  CONTROL -- do the accepted axes pass their own rule?")
    for a, b in (("gold", "duration"), ("duration", "gold")):
        c = abs(float(regime_corrs[36].loc[a, b]))
        tail_ok = mm.loc[a, "d10_mean"] >= mm.loc["market", "d10_mean"]
        print(f"    {a:9s} vs {b:9s}: corr {c:.3f} (== control, passes by "
              f"construction), tail {'PASS' if tail_ok else 'FAIL'}")

    pd.DataFrame(rows).set_index("sleeve").to_csv(
        os.path.join(OUT_DIR, "verdict.csv"))


if __name__ == "__main__":
    main()
