"""Read-only wrapper rond het MetaTrader5 Python-package.

Belangrijk: deze module roept nooit `order_send` of vergelijkbare
order-functies aan. Alleen koersdata wordt uitgelezen.

Het `MetaTrader5`-package is Windows-only en vereist een draaiende,
ingelogde MT5-terminal. De import gebeurt daarom lazy (pas bij gebruik),
zodat de rest van de tool ook werkt op systemen waar dat package niet
beschikbaar is (zie `mt5_signals.data_source` voor de fallback).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

TIMEFRAME_NAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]


class MT5UnavailableError(RuntimeError):
    """MT5-terminal/package is niet beschikbaar of levert geen data."""


def _import_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise MT5UnavailableError(
            "Het 'MetaTrader5' package is niet geinstalleerd (alleen "
            "beschikbaar op Windows met een MT5-terminal)."
        ) from exc
    return mt5


def _initialize(mt5) -> None:
    if not mt5.initialize():
        error = mt5.last_error()
        raise MT5UnavailableError(
            f"MT5-terminal kon niet geinitialiseerd worden: {error}. "
            "Zorg dat MT5 open en ingelogd is."
        )


def _resolve_timeframe(mt5, timeframe: str):
    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    if timeframe not in mapping:
        raise MT5UnavailableError(
            f"Onbekende timeframe '{timeframe}', kies uit {TIMEFRAME_NAMES}"
        )
    return mapping[timeframe]


def fetch_rates(symbol: str, timeframe: str, count: int) -> pd.DataFrame:
    """Haalt de laatste `count` candles op voor `symbol` via MT5 (read-only).

    Raises:
        MT5UnavailableError: als het package ontbreekt, de terminal niet
            bereikbaar/ingelogd is, of het symbool geen data oplevert.
    """
    mt5 = _import_mt5()
    _initialize(mt5)

    try:
        if not mt5.symbol_select(symbol, True):
            raise MT5UnavailableError(f"Symbool '{symbol}' niet gevonden in MT5 Market Watch.")

        tf = _resolve_timeframe(mt5, timeframe)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            raise MT5UnavailableError(
                f"Geen koersdata ontvangen voor '{symbol}' ({mt5.last_error()})."
            )

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df[["time", "open", "high", "low", "close", "tick_volume"]]
    finally:
        mt5.shutdown()


@dataclass
class TerminalStatus:
    connected: bool
    terminal_name: str | None = None
    account_login: int | None = None
    account_server: str | None = None
    trade_allowed: bool | None = None
    error: str | None = None


@dataclass
class SymbolStatus:
    symbol: str
    available: bool
    bid: float | None = None
    ask: float | None = None
    error: str | None = None


@dataclass
class ConnectionDiagnostics:
    terminal: TerminalStatus
    symbols: list[SymbolStatus] = field(default_factory=list)


def check_connection(symbols: list[str]) -> ConnectionDiagnostics:
    """Test de read-only MT5-koppeling en de beschikbaarheid van `symbols`.

    Roept alleen informatieve, read-only functies aan (`initialize`,
    `terminal_info`, `account_info`, `symbol_select`, `symbol_info_tick`) --
    er wordt niets verhandeld of gewijzigd.
    """
    try:
        mt5 = _import_mt5()
    except MT5UnavailableError as exc:
        return ConnectionDiagnostics(terminal=TerminalStatus(connected=False, error=str(exc)))

    try:
        _initialize(mt5)
    except MT5UnavailableError as exc:
        return ConnectionDiagnostics(terminal=TerminalStatus(connected=False, error=str(exc)))

    try:
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        terminal = TerminalStatus(
            connected=True,
            terminal_name=getattr(terminal_info, "name", None),
            account_login=getattr(account_info, "login", None),
            account_server=getattr(account_info, "server", None),
            trade_allowed=getattr(terminal_info, "trade_allowed", None),
        )

        symbol_statuses = []
        for symbol in symbols:
            if not mt5.symbol_select(symbol, True):
                symbol_statuses.append(
                    SymbolStatus(
                        symbol=symbol, available=False, error="niet gevonden in Market Watch"
                    )
                )
                continue

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                symbol_statuses.append(
                    SymbolStatus(symbol=symbol, available=False, error="geen tick-data ontvangen")
                )
                continue

            symbol_statuses.append(
                SymbolStatus(symbol=symbol, available=True, bid=tick.bid, ask=tick.ask)
            )

        return ConnectionDiagnostics(terminal=terminal, symbols=symbol_statuses)
    finally:
        mt5.shutdown()
