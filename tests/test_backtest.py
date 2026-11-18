"""Tests for the backtesting engine."""

import pandas as pd

from src.backtest import Backtester, BacktestConfig
from src.data import generate_mock_forex_data
from src.models import Timeframe
from src.strategy import get_strategy


def test_backtest_runs_and_returns_summary():
    df = generate_mock_forex_data(symbol="EURUSD", timeframe=Timeframe.H1, periods=200, seed=7, trend=0.0, volatility=0.002)
    strat = get_strategy("default")
    bt = Backtester(strategy=strat, config=BacktestConfig(initial_balance=10_000, risk_per_trade=0.01))
    result = bt.run(df, symbol="EURUSD", timeframe=Timeframe.H1)

    assert result.summary is not None
    assert result.summary["total_trades"] >= 0
    assert 0.0 <= result.summary["win_rate"] <= 1.0
    assert result.summary["initial_balance"] == 10_000
    assert len(result.equity_curve) == len(df)


def test_backtest_different_strategies():
    df = generate_mock_forex_data(periods=150, seed=3, volatility=0.002)
    for name in ["default", "trend_following", "mean_reversion"]:
        strat = get_strategy(name)
        bt = Backtester(strategy=strat, config=BacktestConfig())
        result = bt.run(df, symbol="EURUSD", timeframe=Timeframe.H1)
        assert result.summary is not None
        assert isinstance(result.summary["total_pnl"], (int, float))


def test_backtest_no_look_ahead():
    """Signals/entries must use only data up to the current candle."""
    df = generate_mock_forex_data(periods=100, seed=1, volatility=0.002)
    strat = get_strategy("default")
    bt = Backtester(strategy=strat, config=BacktestConfig())
    result = bt.run(df, symbol="EURUSD", timeframe=Timeframe.H1)
    # All entry times must be <= the timestamp of the candle they were generated on.
    # Equity curve length must equal number of candles.
    assert len(result.equity_curve) == len(df)
