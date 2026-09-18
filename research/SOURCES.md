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
