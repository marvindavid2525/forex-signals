"""Command-line interface for the forex signals system.

Parsing uses the standard library (:mod:`argparse`) so the CLI works reliably
without third-party command-parsing dependencies; :mod:`rich` is used only for
pretty terminal output.
"""

import argparse
import sys
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from src.backtest import BacktestConfig, Backtester
from src.data import generate_mock_forex_data
from src.models import Timeframe
from src.signals import SignalGenerator
from src.strategy import get_strategy

console = Console()


def _parse_timeframe(value: str) -> Timeframe:
    try:
        return Timeframe[value.upper()]
    except KeyError:
        valid = ", ".join(e.name for e in Timeframe)
        raise argparse.ArgumentTypeError(f"Invalid timeframe '{value}'. Use one of: {valid}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forex-signals", description="Forex Signals CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--symbol", "-s", default="EURUSD", help="Currency pair")
        p.add_argument("--timeframe", "-t", type=_parse_timeframe, default=Timeframe.H1, help="Timeframe (M1,M5,M15,H1,H4,D1)")
        p.add_argument("--periods", "-p", type=int, default=200, help="Number of candles")
        p.add_argument("--strategy", default="default", help="Strategy: default, trend_following, mean_reversion")
        p.add_argument("--seed", type=int, default=42, help="Random seed")
        p.add_argument("--trend", type=float, default=0.0, help="Drift/trend in mock data")
        p.add_argument("--volatility", type=float, default=0.001, help="Volatility of mock data")

    sig = sub.add_parser("signal", help="Generate trading signals from mock forex data")
    add_common(sig)

    bt = sub.add_parser("backtest", help="Run a backtest and print performance metrics")
    add_common(bt)
    bt.add_argument("--balance", "-b", type=float, default=10_000.0, help="Initial account balance")
    bt.add_argument("--risk", "-r", type=float, default=0.01, help="Risk per trade (fraction of account)")

    sub.add_parser("version", help="Show the version")

    return parser


def _cmd_signal(args: argparse.Namespace) -> int:
    try:
        strat = get_strategy(args.strategy)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    df = generate_mock_forex_data(
        symbol=args.symbol, timeframe=args.timeframe, periods=args.periods,
        seed=args.seed, trend=args.trend, volatility=args.volatility,
    )
    signals = strat.generate_from_dataframe(df, symbol=args.symbol, timeframe=args.timeframe)

    actionable = [s for s in signals if s.signal_type != "HOLD"]
    if not actionable:
        console.print("[yellow]No actionable signals generated.[/yellow]")
        return 0

    table = Table(title=f"Signals for {args.symbol} ({args.timeframe.name}) via '{args.strategy}' strategy")
    table.add_column("Time", style="cyan")
    table.add_column("Signal", style="bold")
    table.add_column("Strength", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Stop Loss", justify="right")
    table.add_column("Take Profit", justify="right")

    for sig_ in actionable[:50]:
        style = "green" if sig_.signal_type == "BUY" else "red"
        table.add_row(
            str(sig_.timestamp),
            f"[{style}]{sig_.signal_type}[/{style}]",
            f"{sig_.strength:.2f}",
            f"{sig_.price:.5f}",
            f"{sig_.stop_loss:.5f}" if sig_.stop_loss else "-",
            f"{sig_.take_profit:.5f}" if sig_.take_profit else "-",
        )

    console.print(table)
    console.print(f"\n[bold]Total signals:[/bold] {len(signals)}  [bold]Actionable:[/bold] {len(actionable)}")
    return 0


def _cmd_backtest(args: argparse.Namespace) -> int:
    try:
        strat = get_strategy(args.strategy)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1

    df = generate_mock_forex_data(
        symbol=args.symbol, timeframe=args.timeframe, periods=args.periods,
        seed=args.seed, trend=args.trend, volatility=args.volatility,
    )

    config = BacktestConfig(initial_balance=args.balance, risk_per_trade=args.risk)
    bt = Backtester(strategy=strat, config=config)
    result = bt.run(df, symbol=args.symbol, timeframe=args.timeframe)

    summary = result.summary or {}
    table = Table(title=f"Backtest Results — {args.symbol} ({args.timeframe.name}) [{args.strategy}]")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="bold")
    for key, label in [
        ("initial_balance", "Initial Balance"),
        ("final_balance", "Final Balance"),
        ("total_pnl", "Total PnL"),
        ("total_pnl_pct", "Total PnL %"),
        ("total_trades", "Total Trades"),
        ("winning_trades", "Winning Trades"),
        ("losing_trades", "Losing Trades"),
        ("win_rate", "Win Rate"),
        ("max_drawdown", "Max Drawdown"),
        ("profit_factor", "Profit Factor"),
    ]:
        val = summary.get(key, "-")
        if isinstance(val, float):
            val = f"{val:.4f}"
        table.add_row(label, str(val))

    console.print(table)
    if result.trades:
        console.print(f"\n[bold]Equity curve points:[/bold] {len(result.equity_curve)}")
        first = result.trades[0]
        console.print(f"[bold]First trade:[/bold] {first.entry_time} {first.direction} @ {first.entry_price}")
    return 0


def _cmd_version() -> int:
    from src import __version__

    console.print(f"forex-signals v{__version__}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "signal":
        return _cmd_signal(args)
    if args.command == "backtest":
        return _cmd_backtest(args)
    if args.command == "version":
        return _cmd_version()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
