# Regime protocol — 19 September 2026

Fixed before this renovation's evaluation, without independent preregistration. Historical
snapshots and familiar crises make the late segment retrospective, not an untouched holdout.

Primary question: does a two-state Gaussian HMM improve next-session SPY squared-return
forecasts beyond EWMA? Primary endpoint: paired mean loss difference HMM minus EWMA,
January 2025–17 September 2026; negative is favorable. Economic alternative: the states only
repackage trailing volatility or describe history. Require a below-zero interval and stable
sensitivity before proposing predictive usefulness; overlay results alone cannot rescue failure.

Inputs: pinned SPY/TLT adjusted closes, July 2018–17 September 2026. Simple returns only, no cumulative
levels or macro values with uncertain release lags. Daily information available after NY close;
current vendor adjustments are not a point-in-time archive. Reject missing/duplicate/nonfinite
prices and missing XNYS sessions. First undefined return dropped, no fills or winsorization.

At each monthly first session's close from August 2020, fit on the preceding 504 returns
INCLUDING that close. Training-only mean/std scaling for SPY/TLT, diagonal Gaussian covariance.
States fixed at two for parsimony, not selected on the evaluation set. One deterministic seed
19; HMM EM maximum 200, tolerance .01 log likelihood in standardized units, initialization covariance floor
.001 (hmmlearn min_covar is not an M-step bound); GMM 3 initializations, reg_covar .001. Report training occupancy and explicitly check finite moments and
likelihood improvement (reaching max iterations alone is not convergence). A failed model uses
EWMA for forecasts and the volatility control for overlay; record every fallback. State ordering
is ascending training SPY second moment, recomputed at each fit; no future crisis labels.

Filtering: alpha_t proportional to emission_t * (alpha_(t-1) A), normalized in log space.
At refit reconstruct only the trailing training prefix; between refits update one new emission.
Next-state probability is alpha_t A. Forecast E[r_(t+1)^2] as sum p_next (sigma_state^2+mu_state^2)
in original return units. No smoothing or full-sequence Viterbi in decisions. GMM has iid mixture
weights for next-session forecasting; posterior current-state probabilities are descriptive,
not a transition forecast. A single-state trailing second moment and 0.94 EWMA are baselines.
EWMA initializes on pre-evaluation returns and updates using only the current/past observations.

Target: next session squared simple SPY return, nonoverlapping. Loss log(v)+r^2/v, forecast
floor 1e-8. A zero target is valid. This forecasts second moments with a zero-mean risk proxy,
not unbiased latent variance. Loss differences use identical targets/dates. Full post-warmup
and late-segment results shown separately. Paired circular-block percentile intervals (21
sessions primary; 5/63 sensitivity, 2,000 resamples, seed 20260919) condition on archived fits;
no selection or refitting uncertainty. Primary family has one HMM/EWMA contrast. Other models
and sensitivities are exploratory, pointwise, dependent comparisons.

Supporting overlay: HMM risky target 1 - 0.75 * filtered highest-risk probability; static SPY
weight .625 (midpoint, fixed ex ante), and EWMA volatility target min(1,.10/sqrt(252*v)).
Decision after t close, execute t+1 close, first earn t+2 return. This conservative lag means
the forecast horizon and first executable exposure horizon differ; report the decision test
separately. Fractional SPY, residual cash at zero nominal interest; no leverage/financing.
Costs 5 bps per bought/sold dollar, self-financing post-cost targets, drift and entry charged,
no terminal liquidation. Cost sensitivities 0/10. Fallback overlay uses EWMA target.

Diagnostics: training state means/variances, transition entries, occupancy, filter entropy,
high-state persistence, refit convergence/fallback, retrospective-versus-causal label agreement.
Full-sample smoothed HMM and bounded Gaussian binary segmentation are labeled descriptive. The
segmentation is an independent simple greedy Gaussian likelihood splitter, not a full optimized
GGS replication. An online endpoint alarm on a synthetic variance break uses minimum segments
40, gain threshold 20, checks every 5 observations; record detection versus breakpoint, delay,
and false alarms across 50 fixed-seed null/change runs. Its threshold is not tuned on markets.

Bounded model sensitivities, one change at a time: 3 states, seed 41, covariance floor .01,
and SPY-only features; same dates, no winning-variant selection. Synthetic tests do not imply
known market regimes. Freeze archived daily forecasts; future data must not revise their prefix.

Recovery: `uv run python research/run_study.py`; expensive variants checkpoint only with matching
source/code/protocol fingerprints. Outputs `research/results/`, figures `research/figures/`;
full timestamped paths are ignored under `research/results/paths/`. `study.ipynb` is replaced
only after successful fresh-kernel execution.

## Data amendment before evaluation

The user authorized refreshing inputs during implementation, before primary results were computed. On 19 September 2026 KST, download through the last completed US close (17 September; exclusive end 18 September). September is partial. Original protocol is retained in `protocol_versions/initial_20260919.md`; initial manifest and raw snapshots remain available. This expands the late segment by 12 sessions and may revise overlapping adjusted prices. Source revision diagnostics are saved; no initial performance result is claimed.

## Final implementation clarification

19 September: corrected the diagnostic description to smoothed HMM (the actual retrospective plot) and clarified that occupancy is reported, not an additional fit rejection threshold. These are documentation corrections; no model, endpoint or decision changed.
