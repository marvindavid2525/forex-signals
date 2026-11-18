"""Tests for technical indicators."""

import numpy as np
import pandas as pd
import pytest

from src.indicators import atr, bollinger_bands, compute_all_indicators, ema, macd, rsi, sma


@pytest.fixture
def close_series():
    return pd.Series(
        [1.1000, 1.1020, 1.1010, 1.1030, 1.1050, 1.1040, 1.1060, 1.1080, 1.1070, 1.1090,
         1.1100, 1.1085, 1.1075, 1.1090, 1.1110, 1.1120, 1.1115, 1.1130, 1.1140, 1.1135],
    )


def test_sma(close_series):
    result = sma(close_series, 5)
    assert len(result) == len(close_series)
    assert pd.isna(result.iloc[:4]).all()
    assert np.isclose(result.iloc[4], close_series.iloc[:5].mean())


def test_ema(close_series):
    result = ema(close_series, 5)
    assert len(result) == len(close_series)
    assert not pd.isna(result.iloc[4])


def test_rsi_range(close_series):
    result = rsi(close_series, 14)
    assert (result >= 0).all() and (result <= 100).all()


def test_macd_shapes(close_series):
    macd_line, signal_line, hist = macd(close_series, 12, 26, 9)
    assert len(macd_line) == len(close_series)
    assert len(hist) == len(close_series)
    # histogram = macd - signal
    assert np.allclose(hist.dropna(), (macd_line - signal_line).dropna())


def test_bollinger_bands(close_series):
    upper, middle, lower = bollinger_bands(close_series, 20, 2.0)
    assert len(upper) == len(close_series)
    # middle == SMA(20)
    assert np.allclose(middle.dropna(), sma(close_series, 20).dropna())


def test_atr_positive():
    high = pd.Series([1.1, 1.12, 1.11, 1.13, 1.12])
    low = pd.Series([1.08, 1.09, 1.07, 1.10, 1.09])
    close = pd.Series([1.09, 1.11, 1.10, 1.12, 1.11])
    result = atr(high, low, close, 14)
    assert (result.dropna() >= 0).all()


def test_compute_all_indicators_columns():
    df = pd.DataFrame(
        {
            "symbol": ["EURUSD"] * 60,
            "timestamp": pd.date_range("2024-01-01", periods=60, freq="H"),
            "open": np.random.uniform(1.08, 1.12, 60),
            "high": np.random.uniform(1.10, 1.13, 60),
            "low": np.random.uniform(1.06, 1.09, 60),
            "close": np.random.uniform(1.08, 1.12, 60),
            "volume": np.random.randint(50, 500, 60),
        }
    )
    out = compute_all_indicators(df)
    expected_cols = {"rsi", "macd", "macd_signal", "macd_hist", "sma_20", "ema_12", "ema_26", "bb_upper", "bb_middle", "bb_lower", "atr"}
    assert expected_cols.issubset(set(out.columns)), f"missing: {expected_cols - set(out.columns)}"


def test_compute_all_indicators_missing_column():
    df = pd.DataFrame({"open": [1.0], "high": [1.0], "low": [1.0]})
    with pytest.raises(ValueError):
        compute_all_indicators(df)