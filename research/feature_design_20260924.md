# Feature-based regime amendment — 24 September 2026

The first multi-asset replay revealed that the daily-return HMM changes its most
likely state on 55.5% of adjacent sessions. It is retained as the raw-return baseline.
This follow-up changes representation before evaluating the new model; it is explicitly
exploratory and does not convert the familiar historical sample into fresh validation.

Use four log-risk features from EWMA(.90) squared returns: equities (SPY/EFA/EEM),
Treasuries (IEF/TLT), credit (LQD), and real assets (GLD/DBC). Within each group use
the mean second moment, then half its logarithm. Add the zero-mean stock–bond
correlation proxy from an EWMA(.97) second-moment matrix, clipped to ±.95 and Fisher
transformed. Initialize on 63 returns, then update forward. The first feature belongs
to return index 63; fit on trailing 504 feature observations. Training-only scaling.
Three states, seed 19 and all original alert/reset settings remain unchanged. State
order uses the mean standardized fitted level of the four log-risk features.

Training-smoothed state weights estimate each asset's conditional raw-return second
moment. Next-five-session state forecasts average transition-projected moments;
these remain separate from the review/reset use case. Overlapping EWMA features
make the HMM emission-independence assumption approximate; posterior probabilities
are model-implied scores, not calibrated probabilities of an objectively true regime.

All calibration policies, including raw-return-HMM-triggered resets, use the same
567-return warmup and scored dates. Retain raw-return and feature-based outputs,
report hard-label switch rates, alert burden, mean loss and uncertainty. Full-history
and delayed maps use the feature-based representation. Two-state and seed-41
sensitivities apply to that representation. No representation is selected by its
backtest profit or forecast-loss ranking.
