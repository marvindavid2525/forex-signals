"""Tests for signal generation."""

from src.models import IndicatorValues, SignalType, Timeframe
from src.signals import SignalGenerator


def _ind(**overrides):
    base = dict(
        rsi=50.0, macd=0.001, macd_signal=0.0, macd_hist=0.001,
        sma_20=1.10, ema_12=1.101, ema_26=1.100,
        bb_upper=1.11, bb_middle=1.10, bb_lower=1.09, atr=0.005,
    )
    base.update(overrides)
    return IndicatorValues(symbol="EURUSD", timestamp="2024-01-01", **base)


def test_rsi_oversold_gives_buy():
    gen = SignalGenerator()
    sig = gen.generate("EURUSD", "2024-01-01", 1.10, _ind(rsi=25.0, macd=0.001, macd_signal=0.0, macd_hist=0.001, ema_12=1.101, ema_26=1.100))
    assert sig.signal_type == SignalType.BUY
    assert sig.strength > 0


def test_rsi_overbought_gives_sell():
    gen = SignalGenerator()
    sig = gen.generate("EURUSD", "2024-01-01", 1.10, _ind(rsi=80.0, macd=-0.001, macd_signal=0.0, macd_hist=-0.001, ema_12=1.099, ema_26=1.100))
    assert sig.signal_type == SignalType.SELL
    assert sig.strength > 0


def test_hold_when_neutral():
    gen = SignalGenerator()
    sig = gen.generate(
        "EURUSD", "2024-01-01", 1.10,
        _ind(rsi=50.0, macd=0.0, macd_signal=0.0, macd_hist=0.0, ema_12=1.10, ema_26=1.10, price=None),
    )
    assert sig.signal_type == SignalType.HOLD


def test_atr_stops_for_buy():
    gen = SignalGenerator()
    sig = gen.generate("EURUSD", "2024-01-01", 1.10, _ind(rsi=25.0, atr=0.01, ema_12=1.101, ema_26=1.100))
    assert sig.signal_type == SignalType.BUY
    assert sig.stop_loss is not None and sig.stop_loss < 1.10
    assert sig.take_profit is not None and sig.take_profit > 1.10
