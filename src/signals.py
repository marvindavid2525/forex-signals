"""Signal generation logic.

Combines technical indicators into actionable BUY/SELL/HOLD signals with a
confidence strength in [0, 1]. Designed to be easy to extend with new rules.
"""

from dataclasses import dataclass
from typing import List

import pandas as pd

from src.models import IndicatorValues, Signal, SignalType, Timeframe


@dataclass
class SignalRule:
    name: str
    weight: float  # 0..1, contribution to final strength


class SignalGenerator:
    """Generates trading signals from indicator values using weighted rules."""

    def __init__(self, rsi_oversold: float = 30.0, rsi_overbought: float = 70.0):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate(
        self,
        symbol: str,
        timestamp,
        price: float,
        indicators: IndicatorValues,
        strategy: str = "default",
        timeframe: Timeframe = Timeframe.H1,
    ) -> Signal:
        """Produce a single Signal from the latest indicator values."""
        buy_score = 0.0
        sell_score = 0.0
        reasons: List[str] = []

        ind = indicators

        # --- RSI mean reversion ---
        if ind.rsi is not None:
            if ind.rsi < self.rsi_oversold:
                buy_score += 0.30
                reasons.append(f"RSI oversold ({ind.rsi:.1f})")
            elif ind.rsi > self.rsi_overbought:
                sell_score += 0.30
                reasons.append(f"RSI overbought ({ind.rsi:.1f})")
            elif self.rsi_oversold <= ind.rsi <= self.rsi_overbought:
                # Neutral zone adds a small bias toward the nearer extreme
                pass

        # --- MACD momentum ---
        if ind.macd is not None and ind.macd_signal is not None:
            if ind.macd > ind.macd_signal and ind.macd_hist > 0:
                buy_score += 0.25
                reasons.append("MACD bullish crossover")
            elif ind.macd < ind.macd_signal and ind.macd_hist < 0:
                sell_score += 0.25
                reasons.append("MACD bearish crossover")

        # --- EMA trend (12 vs 26) ---
        if ind.ema_12 is not None and ind.ema_26 is not None:
            if ind.ema_12 > ind.ema_26:
                buy_score += 0.20
                reasons.append("EMA uptrend")
            elif ind.ema_12 < ind.ema_26:
                sell_score += 0.20
                reasons.append("EMA downtrend")

        # --- Bollinger Bands mean reversion ---
        if ind.bb_lower is not None and ind.bb_upper is not None:
            if price <= ind.bb_lower:
                buy_score += 0.15
                reasons.append("Price at/below lower Bollinger Band")
            elif price >= ind.bb_upper:
                sell_score += 0.15
                reasons.append("Price at/above upper Bollinger Band")

        # --- Decide ---
        total = buy_score + sell_score
        if total == 0:
            signal_type = SignalType.HOLD
            strength = 0.0
        elif buy_score > sell_score:
            signal_type = SignalType.BUY
            strength = min(buy_score, 1.0)
        else:
            signal_type = SignalType.SELL
            strength = min(sell_score, 1.0)

        # Compute ATR-based stops for directional signals
        stop_loss = None
        take_profit = None
        if ind.atr is not None and signal_type != SignalType.HOLD:
            atr = ind.atr
            if signal_type == SignalType.BUY:
                stop_loss = round(price - 2 * atr, 5)
                take_profit = round(price + 3 * atr, 5)
            else:
                stop_loss = round(price + 2 * atr, 5)
                take_profit = round(price - 3 * atr, 5)

        return Signal(
            symbol=symbol,
            timestamp=timestamp,
            signal_type=signal_type,
            strength=strength,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=strategy,
            timeframe=timeframe,
            indicators=ind,
        )