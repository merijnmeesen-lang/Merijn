"""Read-only wrapper rond het MetaTrader5 Python-package.

Belangrijk: deze module roept nooit `order_send` of vergelijkbare
order-functies aan. Alleen koersdata wordt uitgelezen.

Het `MetaTrader5`-package is Windows-only en vereist een draaiende,
ingelogde MT5-terminal. De import gebeurt daarom lazy (pas bij gebruik),
zodat de rest van de tool ook werkt op systemen waar dat package niet
beschikbaar is (zie `mt5_signals.data_source` voor de fallback).
"""

from __future__ import annotations

import pandas as pd

TIMEFRAME_NAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]


class MT5UnavailableError(RuntimeError):
    """MT5-terminal/package is niet beschikbaar of levert geen data."""


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
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise MT5UnavailableError(
            "Het 'MetaTrader5' package is niet geinstalleerd (alleen "
            "beschikbaar op Windows met een MT5-terminal)."
        ) from exc

    if not mt5.initialize():
        error = mt5.last_error()
        raise MT5UnavailableError(
            f"MT5-terminal kon niet geinitialiseerd worden: {error}. "
            "Zorg dat MT5 open en ingelogd is."
        )

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
