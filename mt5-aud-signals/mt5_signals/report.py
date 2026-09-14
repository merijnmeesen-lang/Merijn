"""Leesbare terminal-output van de signalen. Geen orders, alleen advies."""

from __future__ import annotations

from mt5_signals.signals import BUY, SELL, SignalResult


def _fmt_price(value: float | None) -> str:
    return f"{value:.5f}" if value is not None else "-"


def format_report(results: list[tuple[SignalResult, str]]) -> str:
    header = (
        f"{'Paar':<8} {'Signaal':<6} {'Trend':<5} {'RSI':>6} "
        f"{'Entry':>10} {'Stoploss':>10} {'Take-profit':>12}  Bron"
    )
    lines = [
        "=" * len(header),
        "AUD SIGNALENTOOL -- alleen advies, plaatst nooit zelf orders",
        "=" * len(header),
        header,
        "-" * len(header),
    ]

    for result, source in results:
        lines.append(
            f"{result.symbol:<8} {result.signal:<6} {result.trend:<5} "
            f"{result.rsi_value:>6.1f} {_fmt_price(result.entry):>10} "
            f"{_fmt_price(result.stop_loss):>10} {_fmt_price(result.take_profit):>12}  {source}"
        )

    lines.append("-" * len(header))
    buy_count = sum(1 for r, _ in results if r.signal == BUY)
    sell_count = sum(1 for r, _ in results if r.signal == SELL)
    hold_count = len(results) - buy_count - sell_count
    lines.append(f"Samenvatting: {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD")

    return "\n".join(lines)


def print_report(results: list[tuple[SignalResult, str]]) -> None:
    print(format_report(results))
