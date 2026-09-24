# When should a researcher recalibrate? — 24 September 2026

## Decision and scope

This user-directed amendment changes the question before the new evaluation. The
previous SPY forecast result remains at commit `4c0164e` and in existing baseline
artifacts; the [earlier protocol](protocol_versions/forecast_20260919.md) is retained.

Primary question: can a fast regime alert improve subsequent risk calibration relative
to a continuously updated slow estimator? Competing explanation: continuous fast
adaptation supplies the benefit with fewer model choices. Regime labels also support
historical interpretation and calibration-window selection; these uses do not require
profitable trading or an economic causal claim.

This is retrospective replay with revised vendor prices, familiar episodes and
investigator-selected settings. No pristine holdout or external preregistration.
Chronology matters for measuring alert delay and post-alert usefulness. Retrospective
and delayed labels are useful research tools; show their actual availability dates.

## Inputs

Eight USD-listed adjusted-close proxies: SPY, EFA, EEM, IEF, TLT, LQD, GLD, DBC.
Charts use exposure names. Common start 1 March 2006, exclusive end 22 September 2026
(last complete common session 21 September). Check exact XNYS sessions, positive finite
prices, duplicates, extreme returns and unchanged prices. No fills or backfills.
Foreign-underlying ETFs include currency/asynchronous-market effects; credit means
investment grade; the commodity fund holds futures, not spot commodities. Fixed
surviving funds, revised adjustments and unverified cash-flow reconciliation limit inference.
Raw prices and daily paths stay ignored. Separate manifest from the old SPY/TLT study;
retain timestamped snapshots and hashes. Changed vendor vintages fail closed.

## Three lenses

- **Immediate recognition:** three-state diagonal Gaussian HMM on eight simple daily
  returns. Monthly refits on trailing 504 sessions including the current close;
  training-only standardization; seed 19; max 300 EM iterations; tolerance .01.
  Check finite positive variances and final likelihood gain in [−.01,.01). Failed
  fit retains previous parameters and filters the new observation; first failure
  uses uniform probabilities with no HMM risk forecast. Count failures. States rank
  by mean standardized second moment across assets: quiet, active, stressed.
  These are relative risk states, not objectively known macro regimes.
- **Delayed confirmation:** at t close, use the then-fitted model and data through t
  to revise labels for t−5 and t−20. Save label date and availability date. Changes
  can reflect refits as well as extra observations. Never backdate a revised label
  into a decision. Compare revisions on common valid dates.
- **Historical interpretation:** full-sample HMM smoothing and state fingerprints
  describe completed history and never enter alerts or risk forecasts. A 63-session
  equity/bond return quadrant and rolling stock/bond correlations supply directional
  and hedging context missing from volatility-state labels.

## Alerts and calibration

Observable alert: median across assets of sqrt(EWMA(.90) squared-return estimate /
EWMA(.97) estimate) above 1.5 on two consecutive sessions. HMM alert: stressed-state
filtered probability above .70 twice. Re-arm after a below-threshold observation;
minimum 21 sessions between alarms. A persistently high state is not a new alarm.
Thresholds are fixed practical review rules, not optimized statistical significance.

Compare slow EWMA(.97), fast EWMA(.90), observable-alert reset and HMM-alert reset.
All start from the same warmup second-moment matrix. Each reset estimator switches
at its alarm to the last 20 outer products (zero-mean risk proxy), then uses .90 for
21 subsequent updates and .97 afterwards. Shrink forecast matrices 10% to diagonal.
This is an explicit model-recalibration use case, not a universal optimal alpha-model
window. HMM next-state weighted diagonal forecasts are a supporting comparison.

Primary endpoint: average across eight assets of log(v)+mean(next-five-session r²)/v,
paired against slow EWMA over the common post-504-session history. Freeze at close t;
first target t+1. Exclude the last five dates from scoring; keep them for monitoring.
This is a calibration backtest, not executed trading P&L. Five-session targets overlap.
Also report fixed equal-notional US-equity/long-Treasury/gold/commodity basket risk,
per-asset losses, realized/predicted second-moment ratios, alarms/year, fast-mode share,
and changes in risk estimates.

Paired circular-block percentile intervals: 63 sessions, 2,000 draws, seed 20260924;
21/126 blocks for primary HMM-reset contrast. Two alert-versus-slow primary contrasts;
intervals are pointwise, not familywise. Show continuous fast EWMA; do not select a
winner by significance. Subperiods: 2008–2014, 2015–2019, 2020–2023, 2024–latest.
No refitting or specification-selection uncertainty is included in these intervals.

## Speed, revisions and review burden

Preselected panels: Aug 2008–Jun 2009, Jan–Jun 2020, calendar 2022, Mar–Jun 2025.
These are familiar illustrations, not known regime-change dates. Empirical escalation
reference: median trailing-20-session volatility / preceding-126-session volatility
above 1.5 twice, at least 63 sessions between references. First alert within [−20,+40]
sessions per reference; show unmatched references and alarms. Negative lag means lead
versus a lagging observable reference, not prediction of an unobserved true break.
Shared inputs favor the observable detector; calibration results remain the main test.

Synthetic check, separately labeled: 100 independent 500-session paths for stationary,
abrupt 2x volatility, gradual volatility rise, and correlation-only shift, true change
at 250. Report pre-change/null alarms, hit rate through +60 and conditional delay for
the observable detector. This illustrates what a volatility detector misses; no claims
about historical true-break accuracy. Thresholds are not tuned on synthetic results.

Bounded sensitivities: HMM 2 states, seed 41; observable thresholds 1.3/1.7; HMM
thresholds .60/.80. Same data/dates/calibration policy. Exploratory, dependent contrasts;
no replacement of the primary result. Independently test fixed-lag smoothing, date
alignment, matrix/target accounting, alarm re-arming, and future-perturbation invariance.

## Recovery

`uv run python research/practical_data.py --download`; `uv run python research/run_study.py`;
`uv run python research/build_notebook.py`. Download checkpoints per asset; HMM checkpoints
per configuration with input/code/settings fingerprints. Public outputs:
`research/results/practical/`, `research/figures/practical/`. Daily paths ignored under
`research/results/paths/practical/`. Replace notebook only after fresh-kernel execution.

## Source-feasibility amendment before numerical evaluation

24 September: EFA lacks the 22 September session in both its full-history request
and a separate short-window request. End the common study at 21 September instead
of filling the gap or interpreting a two-session price change as a one-day return.
The initially retrieved SPY-through-23-September snapshot remains in the ignored cache.
No multi-asset evaluation or model comparison had run when this cutoff changed.
HMM supporting forecasts average the next five transition-projected state moments,
matching the five-session realized-risk target.

## Diagnostic clarification after the primary run

The conservative 1.5 observable threshold produced one historical alarm and detected
none of the stipulated synthetic changes. Retain that result. Apply the already
declared 1.3/1.7 threshold sensitivities to the same synthetic paths as a diagnostic
of this blind spot; no threshold is promoted to a replacement primary specification.

## Feature representation amendment after the initial replay

The raw-return HMM changes its most likely label on 55.5% of adjacent sessions.
Retain its results in `initial_raw_return_*.csv`, and its reset policy as an aligned
benchmark in the new evaluation. The [feature design](feature_design_20260924.md)
specifies four smoothed log-risk features plus stock–bond dependence, chosen for
research interpretability before evaluating this follow-up. It supersedes the raw
return representation as the maintained research monitor, not as a retrospectively
selected forecast winner. All policies now share 567 returns of warmup (63 feature
initialization plus 504 training observations). The experiment remains exploratory.

Event-reporting clarification: record whether the feature HMM was already in its
high-stress state at each empirical reference, and time since the last alert. The
new-alert match count alone is not detection accuracy: an ongoing state can predate
the matching window. This adds diagnostics without changing signals or policies.
