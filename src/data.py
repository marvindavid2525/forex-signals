"""Data loading utilities: CSV loader and synthetic mock forex data generator."""

from datetime import datetime, timedelta
from typing import List, Optional

import numpy as np
import pandas as pd

from src.models import Candle, Timeframe


def _timeframe_delta(tf: Timeframe) -> timedelta:
    mapping = {
        Timeframe.M1: timedelta(minutes=1),
        Timeframe.M5: timedelta(minutes=5),
        Timeframe.M15: timedelta(minutes=15),
        Timeframe.H1: timedelta(hours=1),
        Timeframe.H4: timedelta(hours=4),
        Timeframe.D1: timedelta(days=1),
    }
    return mapping[tf]


def generate_mock_forex_data(
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    start: Optional[datetime] = None,
    periods: int = 500,
    seed: int = 42,
    trend: float = 0.0,
    volatility: float = 0.001,
) -> pd.DataFrame:
    """Generate a synthetic OHLCV dataset for backtesting/demos.

    Uses a geometric random walk with an optional drift (trend) so that
    strategies produce a mix of BUY, SELL and HOLD signals.
    """
    rng = np.random.default_rng(seed)
    if start is None:
        start = datetime(2024, 1, 1)

    delta = _timeframe_delta(timeframe)
    timestamps = [start + i * delta for i in range(periods)]

    # Log-returns with drift
    dt = 1.0
    log_returns = rng.normal(loc=trend * dt, scale=volatility, size=periods)
    prices = 1.08 * np.exp(np.cumsum(log_returns))  # start near EURUSD ~1.08

    data = []
    for i, (ts, close) in enumerate(zip(timestamps, prices)):
        noise = rng.normal(0, volatility * 0.5, size=3)
        o = close if i == 0 else prices[i - 1]
        h = max(o, close) * (1 + abs(noise[0]) * 0.5)
        l = min(o, close) * (1 - abs(noise[1]) * 0.5)
        # ensure high >= max(o,c) and low <= min(o,c)
        h = max(h, o, close)
        l = min(l, o, close)
        volume = float(rng.integers(50, 500))
        data.append(
            {
                "symbol": symbol,
                "timestamp": ts,
                "open": round(float(o), 5),
                "high": round(float(h), 5),
                "low": round(float(l), 5),
                "close": round(float(close), 5),
                "volume": volume,
            }
        )

    df = pd.DataFrame(data)
    return df


def load_csv(path: str) -> pd.DataFrame:
    """Load candle data from a CSV file.

    Expected columns: timestamp, open, high, low, close, volume (symbol optional).
    """
    df = pd.read_csv(path, parse_dates=["timestamp"])
    required = {"timestamp", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")
    if "symbol" not in df.columns:
        df["symbol"] = "UNKNOWN"
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def candles_to_dataframe(candles: List[Candle]) -> pd.DataFrame:
    rows = [
        {
            "symbol": c.symbol,
            "timestamp": c.timestamp,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    return pd.DataFrame(rows)