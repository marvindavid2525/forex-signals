"""Trading strategies that turn candle data + indicators into signals."""

from typing import List, Optional

import pandas as pd

from src.indicators import compute_all_indicators
from src.models import Candle, IndicatorValues, Signal, SignalType, Timeframe
from src.signals import SignalGenerator


class BaseStrategy:
    name: str = "base"

    def __init__(self, generator: Optional[SignalGenerator] = None):
        self.generator = generator or SignalGenerator()

    def generate_signal(
        self,
        symbol: str,
        timestamp,
        price: float,
        indicators: IndicatorValues,
        timeframe: Timeframe = Timeframe.H1,
    ) -> Signal:
        return self.generator.generate(
            symbol=symbol,
            timestamp=timestamp,
            price=price,
            indicators=indicators,
            strategy=self.name,
            timeframe=timeframe,
        )

    def generate_from_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: Timeframe = Timeframe.H1,
    ) -> List[Signal]:
        """Generate a signal for every row of an indicator-enriched DataFrame."""
        signals: List[Signal] = []
        enriched = compute_all_indicators(df) if "rsi" not in df.columns else df

        for _, row in enriched.iterrows():
            indicators = IndicatorValues(
                symbol=symbol,
                timestamp=row["timestamp"],
                rsi=row.get("rsi"),
                macd=row.get("macd"),
                macd_signal=row.get("macd_signal"),
                macd_hist=row.get("macd_hist"),
                sma_20=row.get("sma_20"),
                ema_12=row.get("ema_12"),
                ema_26=row.get("ema_26"),
                bb_upper=row.get("bb_upper"),
                bb_middle=row.get("bb_middle"),
                bb_lower=row.get("bb_lower"),
                atr=row.get("atr"),
            )
            sig = self.generate_signal(
                symbol=symbol,
                timestamp=row["timestamp"],
                price=float(row["close"]),
                indicators=indicators,
                timeframe=timeframe,
            )
            signals.append(sig)
        return signals


class TrendFollowingStrategy(BaseStrategy):
    name = "trend_following"

    def __init__(self, generator: Optional[SignalGenerator] = None):
        # Trend following leans on MACD/EMA, less on mean-reversion RSI
        super().__init__(generator or SignalGenerator(rsi_oversold=25, rsi_overbought=75))


class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion"

    def __init__(self, generator: Optional[SignalGenerator] = None):
        # Mean reversal leans on RSI + Bollinger Bands
        super().__init__(generator or SignalGenerator(rsi_oversold=35, rsi_overbought=65))


def get_strategy(name: str) -> BaseStrategy:
    strategies = {
        "default": BaseStrategy(),
        "trend_following": TrendFollowingStrategy(),
        "mean_reversion": MeanReversionStrategy(),
    }
    if name not in strategies:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(strategies)}")
    return strategies[name]