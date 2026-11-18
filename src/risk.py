"""Risk management: position sizing, stop-loss/take-profit, exposure limits."""

from dataclasses import dataclass
from typing import Optional

from src.models import Signal, SignalType, TradeResult


@dataclass
class RiskParameters:
    account_balance: float = 10_000.0
    risk_per_trade: float = 0.01  # 1% of account per trade
    max_position_size: float = 100.0  # max units
    max_daily_loss: float = 0.05  # 5% daily loss limit
    min_risk_reward: float = 1.5  # minimum reward:risk ratio


class RiskManager:
    def __init__(self, params: Optional[RiskParameters] = None):
        self.params = params or RiskParameters()
        self.daily_pnl = 0.0
        self.daily_trades = 0

    def position_size(self, signal: Signal, stop_loss: float) -> float:
        """Lot/unit size based on fixed-fractional risk.

        risk_amount = account_balance * risk_per_trade
        size = risk_amount / |entry_price - stop_loss|
        """
        if signal.signal_type == SignalType.HOLD:
            return 0.0
        if stop_loss is None or stop_loss == signal.price:
            return 0.0

        risk_amount = self.params.account_balance * self.params.risk_per_trade
        price_distance = abs(signal.price - stop_loss)
        if price_distance <= 0:
            return 0.0

        size = risk_amount / price_distance
        size = min(size, self.params.max_position_size)
        return round(size, 2)

    def check_daily_loss_limit(self) -> bool:
        """Return False if the daily loss limit has been breached."""
        if self.params.account_balance <= 0:
            return False
        loss_pct = abs(self.daily_pnl) / self.params.account_balance
        return loss_pct < self.params.max_daily_loss

    def validate_signal(self, signal: Signal) -> bool:
        """Basic validation: non-HOLD, has stops, meets reward:risk."""
        if signal.signal_type == SignalType.HOLD:
            return False
        if signal.stop_loss is None or signal.take_profit is None:
            return False
        risk = abs(signal.price - signal.stop_loss)
        reward = abs(signal.take_profit - signal.price)
        if risk <= 0:
            return False
        return (reward / risk) >= self.params.min_risk_reward

    def compute_pnl(self, trade: TradeResult, exit_price: float) -> float:
        """PnL for a closed trade (quote currency per unit)."""
        if trade.direction == SignalType.BUY:
            pnl = (exit_price - trade.entry_price) * trade.size
        else:
            pnl = (trade.entry_price - exit_price) * trade.size
        return round(pnl, 2)

    def update_daily(self, pnl: float) -> None:
        self.daily_pnl += pnl
        self.daily_trades += 1