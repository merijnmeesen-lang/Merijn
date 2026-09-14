"""Kiest de koersdatabron: live MT5 (read-only) met terugval op demo-data."""

from __future__ import annotations

import pandas as pd

from mt5_signals.config import Config
from mt5_signals.mt5_client import MT5UnavailableError, fetch_rates
from mt5_signals.sample_data import generate_sample_ohlc


def get_price_data(symbol: str, config: Config) -> tuple[pd.DataFrame, str]:
    """Levert OHLC-data voor `symbol` en meldt de gebruikte bron.

    Probeert eerst een live, read-only MT5-verbinding. Is die niet
    beschikbaar (geen package, terminal niet open/ingelogd, symbool
    onbekend), dan wordt teruggevallen op deterministische demo-data zodat
    de tool toch een volledig rapport kan tonen.
    """
    try:
        df = fetch_rates(symbol, config.timeframe, config.bars_count)
        return df, "MT5 (live)"
    except MT5UnavailableError as exc:
        df = generate_sample_ohlc(symbol, config.bars_count)
        return df, f"demo-data (MT5 niet beschikbaar: {exc})"
