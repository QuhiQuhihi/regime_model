import numpy as np
import pandas as pd
import pytest

from research.landing_backtest import daily_net_returns


def test_close_signal_trades_next_close_and_earns_following_return():
    dates = pd.bdate_range("2024-01-02", periods=5)
    prices = pd.Series([100.0, 200.0, 100.0, 200.0, 100.0], index=dates)
    stressed = pd.Series([1.0, 0.0, 1.0, 0.0, 0.0], index=dates)
    net = daily_net_returns(prices, stressed, bps=0)
    np.testing.assert_allclose(net.regime, [0.0, -0.125, 1.0, -0.125])
    np.testing.assert_allclose(net.spy, [0.0, -0.5, 1.0, -0.5])
    np.testing.assert_allclose(net.static, [0.0, -0.3125, 0.625, -0.3125])
    with pytest.raises(ValueError, match="same ordered sessions"):
        daily_net_returns(prices, stressed.drop(index=dates[2]))


def test_entry_cost_drift_rebalance_and_no_exit_fee():
    dates = pd.bdate_range("2024-01-02", periods=4)
    prices = pd.Series([100.0, 100.0, 200.0, 200.0], index=dates)
    stressed = pd.Series(0.0, index=dates)
    net = daily_net_returns(prices, stressed)
    rate = 5 / 10_000
    np.testing.assert_allclose(net.spy, [1 / (1 + rate) - 1, 1.0, 0.0])
    np.testing.assert_allclose(net.regime, net.spy)
    target = 0.625
    entry_value = 1 / (1 + rate * target)
    pretrade = 2 * target / (1 + target)
    sale_fee = rate * (pretrade - target) / (1 - rate * target)
    np.testing.assert_allclose(
        net.static,
        [entry_value - 1, (1 + target) * (1 - sale_fee) - 1, 0.0],
    )
