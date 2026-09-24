"""Generate numerical narrative from the reviewed practical-study outputs."""

import json
import pandas as pd
from research.common import table
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
    readme = f"""# Market regimes for faster research decisions

**Recognize a changing market, understand what changed, and decide what to recalibrate.**
A regime model can help a researcher shorten a calibration window, revisit correlations,
separate stress episodes, or test whether a model still describes its inputs. Predicting
a profitable trade is only one possible use.

This project combines immediate recognition, delayed confirmation and retrospective
interpretation using a feature-based HMM across **US and international equities, Treasuries, corporate credit,
gold and commodities**. The historical study spans **March 2006–21 September 2026**.
Charts use asset names so the economic picture comes before the tickers.

![Eight-asset market atlas](research/figures/practical/market_atlas.png)

## Explore the research

| Research question | Read and inspect |
| --- | --- |
| What kind of regime has changed: risk, direction, or dependence? | [Three complementary lenses](docs/01-methods.md) |
| How did the signals behave in 2008–09, 2020, 2022 and 2025? | [Historical replay lab](docs/03-historical-replays.md) |
| Does a prompt alert improve the next calibration? | [Backtest, benchmarks and results](docs/02-results.md) |
| What should I actually do after an alert? | [Researcher's calibration playbook](docs/04-calibration-playbook.md) |
| How much does waiting five or twenty sessions change the description? | [Delayed labels and revisions](docs/02-results.md#allowing-a-short-delay-changes-the-label) |
| Where are the calculations and all figures? | [Executed research notebook](study.ipynb) |

## What a researcher gains

- A persistent map: labels change on **{representations.iloc[1].label_switch_fraction:.1%}** of sessions,
  versus **{representations.iloc[0].label_switch_fraction:.1%}** for the daily-return HMM.
- A dated review process: **{int(burden.loc["HMM reset", "alarms"])} confirmed HMM alerts**, with event replays
  showing what had already happened when each alert became available.
- A deliberate hindsight option: five- and twenty-session revised labels for event
  studies and calibration samples, alongside their original real-time descriptions.
- An actual calibration backtest: keep continuous risk updating in view, because a
  more stable regime map has not established better risk forecasts.

## The concrete experiment

Each confirmed alert resets a risk estimator to the latest 20 sessions and makes it
adapt faster for one month. Compare this with continuously slow and fast updating.
Score the following five sessions across eight assets, alongside review frequency,
missed reference episodes and the effect of delayed labels.

Across **{diag["sessions_scored"]:,} matched forecast dates**, the feature-HMM reset's mean
loss difference versus slow EWMA is **{estimate("HMM reset")}**. Its advantage is
negligible and uncertain. The [results chapter](docs/02-results.md) shows the full
comparisons with fast updating, the raw-return model and direct state forecasts.

![Calibration evidence](research/figures/practical/calibration_comparison.png)

The HMM rule produces **{burden.loc["HMM reset", "alarms_per_year"]:.2f} review alerts per year**;
the conservative observable rule produces **{burden.loc["Observable reset", "alarms_per_year"]:.2f}**.
The feature-based HMM describes smoothed risk levels and stock–bond dependence;
the raw-return HMM is retained as a benchmark. Five-session delayed labels revise **{revision.loc["lag5", "changed_from_original"]:.1%}** of
original classifications. The result should be read alongside its interval, subperiods and state-count sensitivity. The observable threshold is too
conservative for a general early-warning role: it produces just one historical alert.

## Read the evidence in the right time frame

A label available at today's close can prompt a review. A label confirmed five sessions
later can improve an event study or a calibration sample. A full-history map can organize
past markets. All three are useful; the notebook shows the waiting time rather than
silently treating every label as an immediate forecast.

This is a retrospective calibration backtest on revised adjusted prices and a fixed
surviving ETF universe. It does not claim pristine out-of-sample validation, executable
strategy returns or known true regime dates. The previous narrow SPY forecast comparison
remains [preserved at its original revision](https://github.com/QuhiQuhihi/regime_model/tree/4c0164ea5a114d865b45bd4b48f40ce72954a7c4);
its inconclusive result is not erased by this broader research question.

[Reproduction and input access](docs/05-reproduction.md) · [Sources](research/SOURCES.md) ·
[Protocol](research/PROTOCOL.md) · [Publication boundaries](PUBLICATION.md).
"""
    (ROOT / "README.md").write_text(readme)
