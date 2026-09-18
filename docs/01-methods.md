# Description, detection, and forecasting are different tasks

A historical color map can organize market behavior even when it cannot improve a decision.
The study therefore asks the forecast question first. SPY represents equity risk; TLT adds a
rate-sensitive asset that may distinguish equity stress from joint stock/bond shocks.

## What each model knows

A Gaussian mixture treats observations as iid draws from several Gaussian components. Its
posterior classifies the current observation; its next-observation distribution still uses
mixture weights. A hidden Markov model adds transition probabilities A_ij. It can carry a
persistent state belief from one date into the next.

At a monthly refit, 504 trailing observations determine scaling, component parameters and
state order. High risk means a higher fitted SPY second moment, not recession status. Models
learn from earlier evaluation observations as time advances, but never from future ones.
Between refits, the HMM uses one forward update:

alpha_t(j) proportional to f_j(x_t) sum_i alpha_(t-1)(i) A_ij.

Normalize in log space, then next-state probabilities are alpha_t A. The forecast is the
probability-weighted sum of state variance plus squared state mean, mapped back to decimal
SPY return units. The known-parameter test enumerates every short hidden-state path and
compares the exact posterior with the recursion. Future perturbations must leave saved
forecast prefixes unchanged.

Full-sequence library posterior/decoding methods can use future observations. Here they are
confined to retrospective diagnostics. Comparing those descriptions with archived filters
shows how appealing historical labels can revise. No state is independently labeled a recession.

## The forecast contest

The target is next-session squared SPY return. EWMA uses decay .94; a single-state trailing
second moment is another baseline. Loss is log(v)+r_next^2/v, with positive forecast floor
1e-8. Pairwise differences matter; the log term means negative loss levels are normal.
Daily squared returns are noisy risk proxies, not measured latent conditional volatility.
The primary HMM/EWMA contrast uses 428 late-segment forecasts through 17 September 2026.

HMM's `min_covar` is an initialization floor in the installed implementation, while GMM's
`reg_covar` adds diagonal regularization. The floor sensitivity records these exact API
settings; it is not a promise that every fitted HMM variance is bounded by that number.
Reaching an EM iteration limit alone does not pass convergence; the last likelihood gain
and finite positive covariances are checked. Failed fits explicitly use EWMA.

## A decision requires another timing assumption

The overlay maps high-risk probability p to SPY weight 1-.75p. It trades one session after
observation and first earns the next return, so its executable horizon differs from the
one-step forecast score. A static .625 control and capped 10%-volatility EWMA rule make
exposure reductions visible. All use exact self-financing costs and zero assumed cash interest.

## Change points with known truth

The independent greedy Gaussian splitter optimizes one mean/variance likelihood break at a
time; it omits the original GGS breakpoint refinement and multivariate optimization. Market
splits are retrospective. An expanding-prefix synthetic alarm records detection date separately
from estimated breakpoint; 50 null and 50 variance-break paths quantify false alarms and delay.
The artificial 3x volatility jump is an algorithm check, not market ground truth.

[Forecast and decision results](02-results.md) · [Frozen settings and caveats](../research/PROTOCOL.md).
