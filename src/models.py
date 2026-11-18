"""Pydantic data models for the forex signals system."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class Candle(BaseModel):
    """A single OHLCV candle."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class IndicatorValues(BaseModel):
    """Calculated technical indicator values for a candle."""

    symbol: str
    timestamp: datetime
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    sma_20: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None


class Signal(BaseModel):
    """A trading signal emitted by a strategy."""

    symbol: str
    timestamp: datetime
    signal_type: SignalType
    strength: float = Field(default=0.0, ge=0.0, le=1.0, description="Signal confidence 0-1")
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = "default"
    timeframe: Timeframe = Timeframe.H1
    indicators: Optional[IndicatorValues] = None


class TradeResult(BaseModel):
    """Result of a simulated/backtested trade."""

    symbol: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    direction: SignalType
    size: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = "OPEN"  # OPEN, CLOSED_WIN, CLOSED_LOSS, CLOSED_BREAKEVEN
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class BacktestSummary(BaseModel):
    """Aggregate backtest performance metrics."""

    symbol: str
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    avg_trade_pnl: float = 0.0


class MarketDataResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: List[Candle]
    count: int


class SignalResponse(BaseModel):
    symbol: str
    timestamp: datetime
    signal_type: SignalType
    strength: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str