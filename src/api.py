"""REST API for the forex signals system (FastAPI)."""

from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from src.data import generate_mock_forex_data, load_csv
from src.models import (
    Candle,
    Signal,
    SignalResponse,
    SignalType,
    Timeframe,
)
from src.indicators import compute_all_indicators
from src.signals import SignalGenerator
from src.strategy import get_strategy

app = FastAPI(
    title="Forex Signals API",
    description="Generate trading signals, run backtests, and manage risk.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"service": "forex-signals", "version": "0.1.0", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/data/mock", response_model=dict)
def get_mock_data(
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    periods: int = Query(500, ge=50, le=5000),
    seed: int = 42,
    trend: float = 0.0,
    volatility: float = 0.001,
):
    """Generate synthetic OHLCV forex data for backtesting/demos."""
    df = generate_mock_forex_data(
        symbol=symbol,
        timeframe=timeframe,
        periods=periods,
        seed=seed,
        trend=trend,
        volatility=volatility,
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "periods": len(df),
        "start": str(df["timestamp"].iloc[0]),
        "end": str(df["timestamp"].iloc[-1]),
        "candles": df.to_dict(orient="records"),
    }


@app.post("/signals/generate", response_model=List[SignalResponse])
def generate_signals(
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    periods: int = Query(200, ge=50, le=5000),
    strategy_name: str = "default",
    seed: int = 42,
    trend: float = 0.0,
    volatility: float = 0.001,
):
    """Generate signals over a mock dataset and return them as a list."""
    try:
        strategy = get_strategy(strategy_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    df = generate_mock_forex_data(
        symbol=symbol,
        timeframe=timeframe,
        periods=periods,
        seed=seed,
        trend=trend,
        volatility=volatility,
    )
    signals = strategy.generate_from_dataframe(df, symbol=symbol, timeframe=timeframe)

    # Only return non-HOLD signals for brevity, but capped
    actionable = [s for s in signals if s.signal_type != SignalType.HOLD][:100]
    return [
        SignalResponse(
            symbol=s.symbol,
            timestamp=s.timestamp,
            signal_type=s.signal_type,
            strength=s.strength,
            price=s.price,
            stop_loss=s.stop_loss,
            take_profit=s.take_profit,
            strategy=s.strategy,
        )
        for s in actionable
    ]


@app.post("/backtest", response_model=dict)
def run_backtest(
    symbol: str = "EURUSD",
    timeframe: Timeframe = Timeframe.H1,
    periods: int = Query(400, ge=100, le=5000),
    strategy_name: str = "default",
    seed: int = 42,
    trend: float = 0.0,
    volatility: float = 0.001,
    initial_balance: float = 10_000.0,
    risk_per_trade: float = 0.01,
):
    """Run a backtest on mock data and return performance summary + trades."""
    from src.backtest import Backtester, BacktestConfig

    try:
        strategy = get_strategy(strategy_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    df = generate_mock_forex_data(
        symbol=symbol,
        timeframe=timeframe,
        periods=periods,
        seed=seed,
        trend=trend,
        volatility=volatility,
    )

    config = BacktestConfig(
        initial_balance=initial_balance,
        risk_per_trade=risk_per_trade,
    )
    bt = Backtester(strategy=strategy, config=config)
    result = bt.run(df, symbol=symbol, timeframe=timeframe)

    return {
        "config": {
            "symbol": symbol,
            "timeframe": str(timeframe),
            "initial_balance": config.initial_balance,
            "risk_per_trade": config.risk_per_trade,
            "periods": len(df),
        },
        "summary": result.summary,
        "trades": [
            {
                "entry_time": str(t.entry_time),
                "exit_time": str(t.exit_time) if t.exit_time else None,
                "direction": str(t.direction),
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "size": t.size,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "status": t.status,
            }
            for t in result.trades
        ],
        "equity_curve": result.equity_curve,
    }