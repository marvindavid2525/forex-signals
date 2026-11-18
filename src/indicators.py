"""Technical indicator calculations using pure pandas/numpy.

All functions operate on pandas Series/DataFrames and return aligned Series so
they can be merged back into candle dataframes without look-ahead bias.
"""

from typing import Tuple

import numpy as np
import pandas as pd


def _validate_close(close: pd.Series, name: str = "close") -> pd.Series:
    if not isinstance(close, pd.Series):
        raise TypeError(f"{name} must be a pandas Series")
    return close.astype("float64")


def sma(close: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    close = _validate_close(close)
    if window < 1:
        raise ValueError("window must be >= 1")
    return close.rolling(window=window, min_periods=window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    """Exponential Moving Average."""
    close = _validate_close(close)
    if window < 1:
        raise ValueError("window must be >= 1")
    return close.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    close = _validate_close(close)
    if window < 2:
        raise ValueError("window must be >= 2")
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))
    return rsi_values.fillna(50.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, and histogram."""
    close = _validate_close(close)
    if slow <= fast:
        raise ValueError("slow must be > fast")
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    macd_signal = ema(macd_line, signal)
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: upper, middle (SMA), lower."""
    close = _validate_close(close)
    if window < 1:
        raise ValueError("window must be >= 1")
    middle = sma(close, window)
    std = close.rolling(window=window, min_periods=window).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range (Wilder's smoothing)."""
    high = high.astype("float64")
    low = low.astype("float64")
    close = _validate_close(close)
    if window < 2:
        raise ValueError("window must be >= 2")

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_values = true_range.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return atr_values


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the full indicator suite on a candle DataFrame.

    Expected columns: symbol, timestamp, open, high, low, close, volume.
    Returns a new DataFrame with indicator columns appended.
    """
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")

    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]

    out["rsi"] = rsi(close, 14)
    macd_line, macd_signal, macd_hist = macd(close, 12, 26, 9)
    out["macd"] = macd_line
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_hist
    out["sma_20"] = sma(close, 20)
    out["ema_12"] = ema(close, 12)
    out["ema_26"] = ema(close, 26)
    bb_upper, bb_middle, bb_lower = bollinger_bands(close, 20, 2.0)
    out["bb_upper"] = bb_upper
    out["bb_middle"] = bb_middle
    out["bb_lower"] = bb_lower
    out["atr"] = atr(high, low, close, 14)
    return out