"""Replay the documented SPY exposure rule with the eight-ETF model's filtered states."""

import json

import numpy as np
import pandas as pd

from research.common import performance, sha, trading_cost
from research.practical_config import MANIFEST, PATHS, RESULTS, ROOT
from research.practical_data import validate_prices


def daily_net_returns(prices, stressed, bps=5):
    """Both inputs start at the first signal close. All strategies start in cash."""
    if (
        len(prices) < 3
        or not prices.index.equals(stressed.index)
        or prices.index.has_duplicates
        or not prices.index.is_monotonic_increasing
    ):
        raise ValueError("Prices and filtered states must have the same ordered sessions")
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Invalid SPY adjusted price")
    if not stressed.between(0, 1).all():
        raise ValueError("Invalid filtered stress probability")

    # On date t earn the return on yesterday's holdings before trading on yesterday's signal.
    asset_returns = prices.pct_change(fill_method=None).iloc[1:]
    targets = pd.DataFrame(
        {"regime": 1 - 0.75 * stressed.shift(1), "spy": 1.0, "static": 0.625},
        index=prices.index,
    ).iloc[1:]
    net_returns = {}
    for name, targets_at_close in targets.items():
        weight = 0.0
        net = []
        for asset_return, target in zip(asset_returns, targets_at_close, strict=True):
            gross_value = 1 + weight * asset_return
            drifted_weight = weight * (1 + asset_return) / gross_value
            fee, _ = trading_cost([drifted_weight], [target], bps)
            net.append(gross_value * (1 - fee) - 1)
            weight = target
        net_returns[name] = net
    return pd.DataFrame(net_returns, index=asset_returns.index)


def write_landing_backtest(prices, stressed):
    """Publish month-end wealth and daily-based statistics from a common $100 start."""
    sample = prices.loc[stressed.index[0] :]
    daily = daily_net_returns(sample, stressed)
    wealth = 100 * (1 + daily).cumprod()
    initial = pd.DataFrame(100.0, columns=wealth.columns, index=sample.index[:1])
    month_ends = wealth.groupby(wealth.index.to_period("M")).tail(1)
    monthly = pd.concat([initial, month_ends]).rename_axis("date")

    summary = pd.DataFrame({name: performance(net) for name, net in daily.items()}).T
    summary = summary[["terminal_wealth", "cagr", "max_drawdown"]].rename_axis("strategy")
    summary["terminal_wealth"] *= 100
    output = ROOT / "docs/figures"
    output.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(output / "spy-wealth.csv", float_format="%.8f")
    summary.to_csv(output / "spy-performance.csv", float_format="%.8f")


def load_archived_states():
    state_path = PATHS / "primary_states.csv"
    metadata = json.loads((RESULTS / "run_metadata.json").read_text())
    expected_state = metadata["private_outputs"][state_path.relative_to(ROOT).as_posix()]
    if sha(state_path) != expected_state:
        raise ValueError("Filtered states differ from the recorded study inputs")
    states = pd.read_csv(state_path, index_col="date", parse_dates=True)
    diagnostics = json.loads((RESULTS / "diagnostics.json").read_text())
    if (states.index[0], states.index[-1]) != (
        pd.Timestamp(diagnostics["first_decision"]),
        pd.Timestamp(diagnostics["last_decision"]),
    ):
        raise ValueError("Filtered states differ from the published decision window")
    return states


def replay_archived_backtest():
    manifest = json.loads(MANIFEST.read_text())
    entry = next(s for s in manifest["snapshots"] if s["ticker"] == "SPY")
    price_path = ROOT / "research/data/raw" / entry["filename"]
    if sha(price_path) != entry["sha256"]:
        raise ValueError("SPY prices differ from the recorded study inputs")
    prices = pd.read_csv(price_path, index_col="Date", parse_dates=True)
    validate_prices(prices)
    states = load_archived_states()
    write_landing_backtest(prices.SPY, states.p_high)


if __name__ == "__main__":
    replay_archived_backtest()
