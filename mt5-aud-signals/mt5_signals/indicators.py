"""Pure indicatorberekeningen (EMA, RSI, ATR) op pandas-data.

Bevat geen afhankelijkheid van MT5: werkt op elke OHLC-DataFrame met de
kolommen 'high', 'low' en 'close'.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponentieel voortschrijdend gemiddelde."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder-smoothing)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    # Als er geen verliezen zijn geweest is de RSI per definitie 100.
    result = result.fillna(100.0)
    result[avg_gain.isna()] = np.nan
    return result


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder-smoothing)."""
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    true_range = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
