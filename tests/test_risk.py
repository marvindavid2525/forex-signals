"""Tests for risk management."""

import numpy as np

from src.models import Signal, SignalType, TradeResult
from src.risk import RiskManager, RiskParameters


def _signal(price, stop_loss, take_profit, direction=SignalType.BUY):
    return Signal(
        symbol="EURUSD",
        timestamp="2024-01-01",
        signal_type=direction,
        strength=0.8,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        strategy="test",
    )


def test_position_size_fixed_fractional():
    rm = RiskManager(RiskParameters(account_balance=10_000, risk_per_trade=0.01, max_position_size=1000))
    sig = _signal(price=1.1000, stop_loss=1.0950, take_profit=1.1150)
    size = rm.position_size(sig, 1.0950)
    expected = (10_000 * 0.01) / abs(1.1000 - 1.0950)  # 100 / 0.005 = 20000 -> capped at 1000
    assert size == min(expected, 1000.0)


def test_hold_returns_zero_size():
    rm = RiskManager()
    sig = _signal(price=1.10, stop_loss=1.09, take_profit=1.11, direction=SignalType.HOLD)
    assert rm.position_size(sig, 1.09) == 0.0


def test_validate_signal_reward_risk():
    rm = RiskManager(RiskParameters(min_risk_reward=2.0))
    sig = _signal(price=1.1000, stop_loss=1.0950, take_profit=1.1150)  # ratio 3.0 >= 2.0
    assert rm.validate_signal(sig) is True
    sig2 = _signal(price=1.1000, stop_loss=1.0950, take_profit=1.1050)  # ratio 1.0 < 2.0
    assert rm.validate_signal(sig2) is False


def test_compute_pnl_buy():
    rm = RiskManager()
    t = TradeResult(symbol="EURUSD", entry_time="2024-01-01", entry_price=1.1000, direction=SignalType.BUY, size=10.0)
    pnl = rm.compute_pnl(t, 1.1050)
    assert np.isclose(pnl, 0.05)


def test_compute_pnl_sell():
    rm = RiskManager()
    t = TradeResult(symbol="EURUSD", entry_time="2024-01-01", entry_price=1.1000, direction=SignalType.SELL, size=10.0)
    pnl = rm.compute_pnl(t, 1.0950)
    assert np.isclose(pnl, 0.05)