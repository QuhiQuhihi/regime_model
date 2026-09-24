# Sources and input provenance

Reviewed 19 September 2026. External source statements, modeling assumptions and computed
results are kept separate. No paper's reported performance is presented as reproduced here.
The corporate-bond quality reference was inspected locally at commit
`1f565f6d7010274ff8feb333b9c05be11ba1dcfa` (README, protocol, sources, evaluation, agenda, publication).

## Observed inputs

[Yahoo Finance historical prices](https://finance.yahoo.com/quote/SPY/history/) via
[yfinance's official API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html).
The exact per-ticker URLs, retrieval timestamps, library version, units, row counts and SHA-256
hashes are in [input_manifest.json](data/input_manifest.json). These are USD adjusted closes;
simple returns are decimal changes. Distributions and splits are represented through provider
adjustments and are not independently reconciled with issuer cash-flow ledgers.

Fresh snapshots span 2 July 2018–17 September 2026 (2,064 close observations). Acquisition on
18 September UTC / 19 September KST excluded the still-open 18 September US session. The
[NYSE schedule](https://www.nyse.com/trade/hours-calendars) identifies the core close at 4 p.m.
Eastern. An access timestamp does not establish historical information availability.
No internal missing dates, duplicate sessions or forward fills are accepted. Raw data remain
ignored. Vendor/provider terms still apply; no unrestricted redistribution or commercial-use
permission is asserted. Users need permitted access to restore the same snapshots.

The original August-end snapshot and initial manifest are retained locally. The refresh adds
12 sessions; small overlapping adjusted-price changes are quantified in
[source_refresh.csv](results/source_refresh.csv). No old-vintage primary performance was
computed before this refresh. This is not an independent before/after strategy experiment.

## Methods and attribution

- [hmmlearn 0.3.3 API](https://hmmlearn.readthedocs.io/en/stable/api.html): transition/emission structures, forward-backward smoothing, decoding and convergence monitor behavior. Actual forward-filter code here is explicit and checked by exact state-path enumeration.
- [Hallac, Nystrup and Boyd, GGS](https://web.stanford.edu/~boyd/papers/ggs.html): upstream attribution and the distinction between segmentation and forecasting. The maintained pedagogical binary splitter is not a complete reproduction of their optimized implementation.
- [Botte and Bao, Two Sigma regime modeling](https://www.twosigma.com/articles/a-machine-learning-approach-to-regime-modeling/): original project inspiration for descriptive multi-asset states. This project tests a different small ETF risk-forecast design and does not claim to replicate Two Sigma's results.

Contribution: timestamped causal forecasts and decision paths, matched EWMA comparison,
future-perturbation tests, convergence/fallback accounting and explicit retrospective revisions.
No unsupervised state is treated as a verified economic recession label.

## Practical multi-asset extension — 24 September 2026

The new [practical manifest](data/practical_manifest.json) records eight separate
Yahoo adjusted-close snapshots retrieved on 24 September UTC: 5,172 prices per fund,
1 March 2006–21 September 2026. All use the same observed XNYS sessions, with zero
missing values and zero fills. A longer EFA request and a targeted retry both lacked
22 September; the common cutoff was shortened before model evaluation. Earlier
SPY/TLT vintages are retained separately. The new
[data audit](results/practical/data_audit.json) records extreme returns and unchanged
prices. Retrieval timestamps are not point-in-time release evidence.

Current sources reviewed for this extension:

- [Official yfinance history API](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html): acquisition interface. The locked local version is recorded per snapshot.
- [hmmlearn API](https://hmmlearn.readthedocs.io/en/stable/api.html): Gaussian emissions, transition probabilities, convergence and the difference between posterior smoothing and a forward update. Fixed-lag smoothing is implemented explicitly and checked against enumeration.
- [Two Sigma: A Machine Learning Approach to Regime Modeling](https://www.twosigma.com/articles/a-machine-learning-approach-to-regime-modeling/): motivation for using multi-asset regimes in research. This project's ETF sample, review rule and calibration results are its own experiment, not a replication of that article.
- [Hallac, Nystrup and Boyd: Greedy Gaussian Segmentation](https://web.stanford.edu/~boyd/papers/ggs.html): attribution for the original segmentation topic. The original simplified splitter remains in the baseline; it is not represented as the new monitoring detector.

New contributions are the eight-asset historical replay, dated immediate/delayed labels,
explicit reset policy, matched continuous-update controls, review-burden accounting and
original visualizations. Synthetic paths are separately identified, never substituted
for market data. The assets remain surviving fund proxies; adjusted prices, distributions,
underlying-market timing and provider revisions limit interpretation. Raw prices, daily
signals and forecast panels are excluded from publication; aggregate evidence and original
figures do not establish unrestricted rights to redistribute the source datasets.

The maintained feature representation is described in
[the dated design amendment](feature_design_20260924.md). It was introduced after the
raw-return replay showed frequent state changes. That observation motivates a
research-oriented description; it does not provide independent validation of the new
representation. Four smoothed risk features and one dependence feature remain derived
from the same observed market data. The original raw-return calibration policy is kept
as a matched-period control, and the initial evaluation tables are preserved separately.

The final September 2026 monthly summary is partial through 21 September. A month-end
index in `monthly_monitor.csv` denotes the aggregation period, not an observation or
availability date after the source cutoff.
