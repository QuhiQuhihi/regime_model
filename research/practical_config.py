"""Choices fixed before the multi-asset evaluation on 24 September 2026."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "research/results/practical"
FIGURES = ROOT / "research/figures/practical"
PATHS = ROOT / "research/results/paths/practical"
MANIFEST = ROOT / "research/data/practical_manifest.json"
ASSETS = {
    "SPY": "US equities",
    "EFA": "Developed ex-US equities",
    "EEM": "Emerging-market equities",
    "IEF": "Intermediate Treasuries",
    "TLT": "Long Treasuries",
    "LQD": "Investment-grade credit",
    "GLD": "Gold",
    "DBC": "Broad commodities",
}
START = "2006-03-01"
END = "2026-09-22"
SETTINGS = {
    "states": 3,
    "lookback": 504,
    "feature_warmup": 63,
    "seed": 19,
    "fixed_lags": [5, 20],
    "horizon": 5,
    "slow_decay": 0.97,
    "fast_decay": 0.90,
    "alarm_ratio": 1.5,
    "hmm_alarm_probability": 0.70,
    "confirmation": 2,
    "cooldown": 21,
    "reset_window": 20,
    "fast_sessions": 21,
    "diagonal_shrinkage": 0.10,
    "bootstrap_block": 63,
    "bootstrap_draws": 2000,
}
EPISODES = {
    "2008–09": ("2008-08-01", "2009-06-30"),
    "2020": ("2020-01-02", "2020-06-30"),
    "2022": ("2022-01-03", "2022-12-30"),
    "2025": ("2025-03-03", "2025-06-30"),
}
