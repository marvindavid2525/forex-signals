"""Vectorized/event-driven backtesting engine for forex signals."""

from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from src.indicators import compute_all_indicators
from src.models import Candle, Signal, SignalType, TradeResult
from src.risk import RiskManager
from src.strategy import BaseStrategy


@dataclass
class BacktestConfig:
    initial_balance: float = 10_000.0
    risk_per_trade: float = 0.01
    max_position_size: float = 100.0
    min_risk_reward: float = 1.5
    commission_per_trade: float = 0.0
    slippage_pips: float = 0.0


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: List[TradeResult] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    summary: Optional[dict] = None

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades if t.status != "OPEN")

    @property
    def win_rate(self) -> float:
        closed = [t for t in self.trades if t.status != "OPEN"]
        if not closed:
            return 0.0
        wins = sum(1 for t in closed if t.pnl > 0)
        return wins / len(closed)

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    @property
    def max_drawdown(self) -> float:
        peak = self.config.initial_balance
        max_dd = 0.0
        running = self.config.initial_balance
        for t in self.trades:
            if t.status != "OPEN":
                running += t.pnl
            if running > peak:
                peak = running
            dd = (peak - running) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

class Backtester:
    def __init__(self, strategy: BaseStrategy, config: Optional[BacktestConfig] = None):
        self.strategy = strategy
        self.config = config or BacktestConfig()
        risk_mod = __import__("src.risk", fromlist=["RiskParameters", "RiskManager"])
        self.risk = RiskManager(
            risk_mod.RiskParameters(
                account_balance=self.config.initial_balance,
                risk_per_trade=self.config.risk_per_trade,
                max_position_size=self.config.max_position_size,
            )
        )

    def run(self, df: pd.DataFrame, symbol: str, timeframe) -> BacktestResult:
        result = BacktestResult(config=self.config)
        enriched = compute_all_indicators(df) if "rsi" not in df.columns else df
        enriched = enriched.reset_index(drop=True)

        open_trade: Optional[TradeResult] = None
        equity = self.config.initial_balance

        for _, row in enriched.iterrows():
            ts = row["timestamp"]
            high = float(row["high"])
            low = float(row["low"])
            close = float(row["close"])
            just_closed = False

            # --- Manage open trade: check TP/SL against current candle ---
            if open_trade is not None:
                hit_tp = hit_sl = False
                exit_price = None

                if open_trade.direction == SignalType.BUY:
                    if low <= open_trade.stop_loss:
                        hit_sl = True
                        exit_price = open_trade.stop_loss
                    elif high >= open_trade.take_profit:
                        hit_tp = True
                        exit_price = open_trade.take_profit
                else:  # SELL
                    if high >= open_trade.stop_loss:
                        hit_sl = True
                        exit_price = open_trade.stop_loss
                    elif low <= open_trade.take_profit:
                        hit_tp = True
                        exit_price = open_trade.take_profit

                if hit_tp or hit_sl:
                    exit_price = round(exit_price, 5)
                    pnl = self.risk.compute_pnl(open_trade, exit_price)
                    pnl -= self.config.commission_per_trade
                    open_trade.exit_time = ts
                    open_trade.exit_price = exit_price
                    open_trade.pnl = pnl
                    denom = open_trade.entry_price * open_trade.size
                    open_trade.pnl_pct = round((pnl / denom) * 100, 4) if denom else 0.0
                    open_trade.status = "CLOSED_WIN" if pnl > 0 else ("CLOSED_LOSS" if pnl < 0 else "CLOSED_BREAKEVEN")
                    self.risk.update_daily(pnl)
                    equity += pnl
                    result.trades.append(open_trade)
                    open_trade = None
                    just_closed = True


            # --- Generate signal for entry using indicators up to this candle ---
            indicators = self._row_to_indicators(row, symbol, ts)
            signal = self.strategy.generate_signal(
                symbol=symbol,
                timestamp=ts,
                price=close,
                indicators=indicators,
                timeframe=timeframe,
            )

            if (not just_closed) and open_trade is None and signal.signal_type != SignalType.HOLD:
                stop_loss = signal.stop_loss
                take_profit = signal.take_profit
                size = 0.0
                if self.risk.validate_signal(signal):
                    size = self.risk.position_size(signal, stop_loss)
                if size > 0:
                    # Apply slippage to entry
                    entry_price = close
                    if self.config.slippage_pips > 0:
                        slip = self.config.slippage_pips * 0.0001
                        entry_price = round(close + slip if signal.signal_type == SignalType.BUY else close - slip, 5)

                    open_trade = TradeResult(
                        symbol=symbol,
                        entry_time=ts,
                        entry_price=entry_price,
                        direction=signal.signal_type,
                        size=size,
                        stop_loss=round(stop_loss, 5),
                        take_profit=round(take_profit, 5),
                        status="OPEN",
                    )
                    equity -= self.config.commission_per_trade

            result.equity_curve.append(equity)

        # Close any still-open trade at the last close price
        if open_trade is not None and len(enriched) > 0:
            last_close = float(enriched.iloc[-1]["close"])
            last_ts = enriched.iloc[-1]["timestamp"]
            pnl = self.risk.compute_pnl(open_trade, last_close)
            pnl -= self.config.commission_per_trade
            open_trade.exit_time = last_ts
            open_trade.exit_price = round(last_close, 5)
            open_trade.pnl = pnl
            denom = open_trade.entry_price * open_trade.size
            open_trade.pnl_pct = round((pnl / denom) * 100, 4) if denom else 0.0
            open_trade.status = "CLOSED_WIN" if pnl > 0 else ("CLOSED_LOSS" if pnl < 0 else "CLOSED_BREAKEVEN")
            self.risk.update_daily(pnl)
            equity += pnl
            result.trades.append(open_trade)
            # Fold the final mark-to-market close into the last equity point so
            # the curve always has exactly one point per candle.
            if result.equity_curve:
                result.equity_curve[-1] = equity
            else:
                result.equity_curve.append(equity)

        result.summary = {
            "symbol": symbol,
            "initial_balance": self.config.initial_balance,
            "final_balance": equity,
            "total_pnl": round(result.total_pnl, 2),
            "total_pnl_pct": round((result.total_pnl / self.config.initial_balance) * 100, 4),
            "total_trades": len(result.trades),
            "winning_trades": sum(1 for t in result.trades if t.pnl > 0),
            "losing_trades": sum(1 for t in result.trades if t.pnl < 0),
            "win_rate": round(result.win_rate, 4),
            "max_drawdown": round(result.max_drawdown, 4),
            "profit_factor": round(result.profit_factor, 4),
        }
        return result

    @staticmethod
    def _row_to_indicators(row, symbol: str, ts):
        from src.models import IndicatorValues

        return IndicatorValues(
            symbol=symbol,
            timestamp=ts,
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

