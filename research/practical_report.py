"""Generate numerical narrative from the reviewed practical-study outputs."""

import json
import pandas as pd
from research.common import table
from research.landing_figure import write_stress_history
from research.practical_config import ROOT, RESULTS


def write_report():
    comp = pd.read_csv(RESULTS / "calibration_comparison.csv")
    main = comp.query('endpoint=="Eight-asset mean" and block==63').set_index("contrast")
    burden = pd.read_csv(RESULTS / "review_burden.csv").set_index("method")
    revision = pd.read_csv(RESULTS / "label_revisions.csv").set_index("lens")
    diag = json.loads((RESULTS / "diagnostics.json").read_text())
    monitor = json.loads((RESULTS / "latest_monitor.json").read_text())

    representations = pd.read_csv(RESULTS / "representation_comparison.csv")

    def estimate(method):
        s = main.loc[method]
        return f"{s.estimate:+.4f} (95% interval [{s.lower95:+.4f}, {s.upper95:+.4f}])"

    rows = []
    for method in [
        "Fast EWMA",
        "Observable reset",
        "HMM reset",
        "HMM state forecast",
        "Raw-return HMM reset",
    ]:
        s = main.loc[method]
        rows.append(
            {
                "Calibration rule": method,
                "Loss difference vs slow EWMA": f"{s.estimate:+.4f}",
                "Pointwise 95% interval": f"[{s.lower95:+.4f}, {s.upper95:+.4f}]",
            }
        )
    evidence = table(pd.DataFrame(rows))
    representation_table = table(
        pd.DataFrame(
            [
                {
                    "Model inputs": row.representation,
                    "Sessions with a label change": f"{row.label_switch_fraction:.1%}",
                    "Review alerts": int(row.alarms),
                    "Reviews per year": f"{row.alarms_per_year:.2f}",
                }
                for row in representations.itertuples()
            ]
        )
    )
    burden_table = table(
        pd.DataFrame(
            [
                {
                    "Alert": m,
                    "Alerts": int(s.alarms),
                    "Per year": f"{s.alarms_per_year:.2f}",
                    "Time in reset/fast mode": f"{s.fast_mode_fraction:.1%}",
                    "Reference episodes matched": f"{int(s.matched_episodes)}/{int(s.reference_episodes)}",
                }
                for m, s in burden.iterrows()
            ]
        )
    )
    summary = f"Across eight asset exposures and {diag['sessions_scored']:,} matched forecast dates, the HMM-triggered reset has mean risk-loss difference **{estimate('HMM reset')}** versus slow EWMA. The observable reset gives **{estimate('Observable reset')}**; continuously fast EWMA gives **{estimate('Fast EWMA')}**. Negative favors the alternative. These are calibration losses, not investment returns."
    results = f"""# What changes when regimes become a research tool?

{summary}

## Calibration is the practical test

An alert changes the input to a research decision: replace the slow risk estimate with
one based on the latest 20 sessions, then update it faster for the next 21 sessions.
The test scores the following five sessions, so an attractive retrospective label
cannot improve a forecast that was already frozen.

{evidence}

![Calibration comparison](../research/figures/practical/calibration_comparison.png)

The primary targets are eight individual asset second moments, weighted equally in the
loss. This does not give equities more importance because their raw volatility is larger.
The supporting basket uses quarter weights in US equities, long Treasuries, gold and
commodities; its risk includes their correlations. Loss is log(v) + realized r² / v,
with the five-session mean squared return as the target.

Intervals use paired 63-session circular blocks and 2,000 draws. Overlapping five-day
targets, cross-asset dependence and each day's common outcomes are preserved by the
paired sampling. The intervals condition on fitted paths; they do not remove model
selection, revised-data or familiar-history uncertainty. Two primary alert contrasts
have pointwise intervals, without familywise coverage.

## Which representation gives a useful research picture?

{representation_table}

![Representation comparison](../research/figures/practical/representation_comparison.png)

The original daily-return HMM and the feature-based HMM are both retained. The
feature version describes recent risk levels and equity–bond dependence; it was
introduced after inspecting the first model's rapid label changes. This is an
explicit exploratory amendment, not an independent validation sample. Smoother labels
are useful for interpretation but do not, by themselves, establish better forecasts.
The raw-return reset is re-scored over the same dates as the feature-based policy.

The result supports a specific workflow: use the more persistent map to organize
research and review scenarios, while maintaining continuous risk updates. The
feature-based reset changes the average calibration loss by very little, with an
interval spanning zero. Its direct state-moment forecast is worse than the slow
baseline under this specification. A useful descriptive state is not automatically
the best forecasting model.

## A fast response has an operating burden

{burden_table}

![Alert timing](../research/figures/practical/alert_timing.png)

The conservative observable threshold generates only **one alert in the entire replay**.
Its quietness is not evidence of reliable detection: the synthetic primary check
misses even the stipulated volatility doubling. The predeclared 1.3 sensitivity gives
six historical alerts; the 1.7 sensitivity gives none. These outcomes are shown rather
than silently replacing the weak primary threshold with a more favorable one.

In a prolonged stressed state, no new alert may be issued because the rule has not
re-armed. For example, the feature HMM is already stressed from its first June 2008
review through the September escalation. The event table records high-state status
separately, so the new-alert match rate is not presented as true-regime detection accuracy.

The reference is an observable escalation in recent volatility, not a known true
regime boundary. A negative lag means earlier than that reference; unmatched alerts
can reflect another sort of change and are not automatically false alarms. The
[complete event table](../research/results/practical/episode_timing.csv) retains misses.

## Allowing a short delay changes the label

On common available dates, **{revision.loc["lag5", "changed_from_original"]:.1%}** of
labels differ after five sessions and **{revision.loc["lag20", "changed_from_original"]:.1%}**
after twenty. The full-history map differs on **{revision.loc["full", "changed_from_original"]:.1%}**.
These revisions can help research interpretation. They also show why the date a label
becomes available belongs beside the date it describes.

![Delayed confirmation](../research/figures/practical/revision_tradeoff.png)

## Inspect the contrasts, not just an average

The [subperiod table](../research/results/practical/subperiods.csv) covers 2008–2014,
2015–2019, 2020–2023 and 2024–latest. [Sensitivity results](../research/results/practical/sensitivity.csv)
retain two-state/three-state fits, a second seed and both tighter and looser alert
thresholds. None replaces the original specification. Per-asset intervals are in
[asset_comparison.csv](../research/results/practical/asset_comparison.csv).

![Risk estimate replay](../research/figures/practical/calibration_replay.png)

## Latest historical research snapshot

As of **{monitor["as_of"]}**, the broad HMM label is **{monitor["state"]}**, stressed-state
probability **{monitor["p_stressed"]:.1%}**, and normalized uncertainty **{monitor["normalized_entropy"]:.2f}**.
The fast/slow risk ratio is **{monitor["fast_slow_risk_ratio"]:.2f}**, while the trailing
63-session US-equity/long-Treasury correlation is **{monitor["equity_bond_correlation_63"]:+.2f}**.
This is the endpoint of the recorded historical replay, not a live signal service.
[The snapshot](../research/results/practical/latest_monitor.json) contains the full
probability vector, asset-direction context and last review dates.

[Methods](01-methods.md) · [Historical event lab](03-historical-replays.md) ·
[Researcher's playbook](04-calibration-playbook.md) · [Exact protocol](../research/PROTOCOL.md).
"""
    (ROOT / "docs/02-results.md").write_text(results)
    write_stress_history()
    portfolio = pd.read_csv(ROOT / "docs/figures/spy-performance.csv", index_col="strategy")
    regime, spy = portfolio.loc["regime"], portfolio.loc["spy"]
    switch_rate = representations.set_index("representation").label_switch_fraction
    reset = main.loc["HMM reset"]
    readme = rf"""# Market regimes and the S&P 500

What happened to a stock portfolio that cut its exposure when markets looked stressed? This 18-year
backtest uses a three-state hidden Markov model (HMM) across eight ETFs to size a
position in **SPY**, the ETF tracking the S&P 500.

![Growth of $100 in three SPY portfolios, June 2008–September 2026, with blue, gold, and rose bands for quiet, active, and stressed markets](docs/figures/spy-backtest.png)

Blue, gold, and rose bands mark the model’s **quiet**, **active**, and **stressed**
classifications at each daily close. For example,
the HMM switched from active to stressed on 28 February 2020 and back to active
on 1 July.

**The regime allocation gave up some growth for a shallower drawdown.**
An initial \$100 grew to **\${regime.terminal_wealth:,.0f}** with the model and
**\${spy.terminal_wealth:,.0f}** with buy-and-hold SPY. The largest peak-to-trough
loss, measured at daily closes, was **{-regime.max_drawdown:.1%}** for the model
and **{-spy.max_drawdown:.1%}** for buy-and-hold.

**What was traded.** Each close's filtered stress probability $p_t$ sets a target
SPY weight of $1-0.75p_t$, ranging from 25% to 100%. Trade at the following close
and earn the new position's return from then on. All three portfolios start in cash,
use adjusted SPY prices, earn 0% on cash, and pay 5 basis points per dollar traded,
including entry. The fixed mix rebalances to 62.5% SPY daily. Curves show month-end
wealth plus the final session. [Monthly wealth](docs/figures/spy-wealth.csv) · [Daily-based performance summary](docs/figures/spy-performance.csv)

This historical simulation applies the earlier allocation rule to a model developed
on the same history. Its portfolio results are exploratory. [Allocation rule](research/protocol_versions/forecast_20260919.md) · [Backtest code](research/landing_backtest.py)

## How the model assigns a regime

**1. Measure risk and dependence.** Let $r_t$ be the vector of daily returns for
SPY, EFA, EEM, IEF, TLT, LQD, GLD, and DBC. Update the matrix of return second
moments with an exponentially weighted moving average (EWMA).

$$
M_t(\lambda)=\lambda M_{{t-1}}(\lambda)+(1-\lambda)r_t r_t^\top
$$

With $\lambda=0.90$, take half the log of the mean diagonal entry within each
group to get four risk features (equities, Treasuries, credit, and real assets).
With $\lambda=0.97$, divide the SPY–TLT cross-moment by the product of their
root-mean-square returns, clip to $\pm 0.95$, and apply the Fisher transform. That gives the fifth feature.

**2. Fit three states and update them at each close.** Each month, fit a
diagonal-Gaussian HMM on the latest 504 feature observations. Standardize inputs
using that window and rank the states by their mean standardized level across the
four risk features. For today's standardized vector $x_t$, the filtered probability is

$$
\alpha_t(j) \propto \mathcal{{N}}(x_t\mid\mu_j,D_j)\sum_{{i=1}}^3 \alpha_{{t-1}}(i) A_{{ij}}
$$

$A_{{ij}}$ is the fitted probability of moving from state $i$ to state $j$.
The Gaussian density measures how well today's features fit state $j$.
Normalize across the three states and use the most probable one as the day's label.
[Feature construction and replay code](research/feature_regimes.py)

Across the full replay, the feature model switched labels on
**{switch_rate["Risk and dependence features"]:.1%}** of sessions versus **{switch_rate["Daily returns"]:.1%}**
for the daily-return HMM. [Stress probability over time](docs/figures/stress-history.png) · [Daily replay examples](docs/03-historical-replays.md)

**3. Test a separate risk-calibration rule.** Two consecutive closes above 70% stressed
probability trigger a reset to the mean of the latest 20 daily return outer products.
For the next 21 updates, use fast EWMA (0.90), then resume slow EWMA (0.97).
Another alert requires the signal to first fall to 70% or below and at least 21
sessions to pass since the previous alert. [Alert and calibration code](research/practical_models.py)

## Did the reset improve the next five sessions' risk estimate?

The model triggered **{int(burden.loc["HMM reset", "alarms"])} resets**. Across **{diag["sessions_scored"]:,} matched forecast dates**, the reset changed mean loss by
**{reset.estimate:+.4f}** versus continuous slow EWMA. Its 95% interval
**[{reset.lower95:+.4f}, {reset.upper95:+.4f}]** spans zero. The data are consistent
with either a modest improvement or a modest deterioration in calibration.

![Loss differences versus slow EWMA for three calibration rules, with 95% intervals and a breakdown by asset](research/figures/practical/calibration_comparison.png)

For each asset, score the second-moment forecast $v$ against the next five sessions'
mean squared return $y$ using $L(v,y)=\log(v)+y/v$. Average the loss equally across
assets. Negative differences favor the alternative rule. Intervals use 2,000 paired
block-bootstrap draws with 63-session blocks. [Result table](research/results/practical/calibration_comparison.csv)

The retrospective sample uses revised adjusted prices for eight surviving ETFs from
March 2006 through 21 September 2026. The feature design followed inspection of
the daily-return model on this same history. [Study protocol](research/PROTOCOL.md) · [Data sources](research/SOURCES.md) · [Publication notes](PUBLICATION.md)

[Executed notebook](study.ipynb) · [Methods](docs/01-methods.md) · [Full results](docs/02-results.md) · [Calibration playbook](docs/04-calibration-playbook.md) · [Reproduce the study](docs/05-reproduction.md)
"""
    (ROOT / "README.md").write_text(readme)
