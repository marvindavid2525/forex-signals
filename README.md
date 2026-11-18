# Forex Signals System

A production-style **forex trading signals system** with technical indicators,
signal generation, event-driven backtesting, risk management, a REST API, and a
command-line interface.

> This repository was previously empty (placeholder README only). The system below
> was built from scratch in this workspace.

## Features

- **Technical indicators** (pure pandas/numpy, no TA-Lib required):
  RSI, MACD, EMA/SMA, Bollinger Bands, Average True Range (ATR).
- **Signal generation**: BUY / SELL / HOLD with a confidence strength in [0, 1]
  and ATR-based stop-loss / take-profit levels.
- **Strategies**: `default`, `trend_following`, `mean_reversion` — easy to extend.
- **Event-driven backtester**: TP/SL exits, position sizing, commission &
  slippage support, equity curve, win rate, max drawdown, profit factor.
  No look-ahead bias.
- **Risk management**: fixed-fractional position sizing, daily loss limit,
  minimum reward-to-risk ratio.
- **REST API** (FastAPI): generate signals, run backtests, mock data endpoint.
- **CLI** (argparse + rich): `signal`, `backtest`, `version` commands.
- **Tests**: 20 passing tests covering indicators, signals, risk, backtesting.

## Installation

```bash
# clone
git clone https://github.com/marvindavid2525/forex-signals.git
cd forex-signals

# virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
```

## Quick start

### Generate signals (CLI)
```bash
python -m src.cli signal --symbol EURUSD --timeframe H1 --periods 200 \
  --strategy default --seed 3 --volatility 0.002
```

### Run a backtest (CLI)
```bash
python -m src.cli backtest --symbol EURUSD --timeframe H1 --periods 400 \
  --strategy trend_following --seed 9 --volatility 0.002 \
  --balance 10000 --risk 0.01
```

### Show version
```bash
python -m src.cli version
```

### Run the API
```bash
uvicorn src.api:app --reload
```
Then visit `http://localhost:8000/docs` for the interactive Swagger UI.

Example calls:
```bash
curl -X POST "http://localhost:8000/signals/generate?symbol=EURUSD&timeframe=H1&periods=100&strategy=mean_reversion&seed=5"

curl -X POST "http://localhost:8000/backtest?symbol=EURUSD&timeframe=H1&periods=300&strategy=default&seed=1&initial_balance=10000&risk_per_trade=0.01"
```

## Run tests
```bash
pytest -q
```

## Project structure
```
forex-signals/
├── README.md
├── requirements.txt
├── pyproject.toml
├── data/
│   └── sample_forex.csv          # synthetic OHLCV forex data (500 H1 candles)
├── src/
│   ├── __init__.py
│   ├── models.py                 # Pydantic models (Candle, Signal, TradeResult, ...)
│   ├── indicators.py             # RSI, MACD, EMA/SMA, Bollinger Bands, ATR
│   ├── signals.py                # Signal generation (BUY/SELL/HOLD + strength)
│   ├── strategy.py               # Strategies + signal-from-dataframe helper
│   ├── risk.py                   # Position sizing, stops, reward:risk, daily loss
│   ├── backtest.py               # Event-driven backtesting engine
│   ├── data.py                   # CSV loader + mock forex data generator
│   ├── api.py                    # FastAPI REST API
│   └── cli.py                    # argparse + rich CLI
└── tests/
    ├── test_indicators.py
    ├── test_signals.py
    ├── test_risk.py
    └── test_backtest.py
```

## Example output

```
$ python -m src.cli backtest --symbol EURUSD --timeframe H1 --periods 200 \
    --strategy trend_following --seed 9 --volatility 0.002

 Backtest Results — EURUSD (H1) [trend_following]
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Metric          ┃ Value      ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Total Trades    │ 12         │
│ Winning Trades  │ 4          │
│ Win Rate        │ 0.3333     │
│ Total PnL       │ -1.0600    │
│ Max Drawdown    │ 0.0002     │
│ Profit Factor   │ 0.7446     │
└─────────────────┴────────────┘
```

## Notes

- The included data generator produces **synthetic** forex candles (geometric
  random walk with optional drift). It is intended for backtesting, demos, and
  CI — not live trading. Wire `src/data.py`'s `load_csv()` to a real broker or
  data feed for live use.
- This is educational/research software, not financial advice. Trading forex
  carries substantial risk of loss.

## License
MIT
