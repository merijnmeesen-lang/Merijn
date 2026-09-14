"""Signaallogica: combineert trendfilter (EMA) en momentum (RSI) tot een
BUY/SELL/HOLD-advies, met ATR-gebaseerde stoploss en RR-gebaseerde take-profit.

Deze module plaatst nooit orders -- het resultaat is puur informatief advies.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mt5_signals.config import Config
from mt5_signals.indicators import atr, ema, rsi

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"

TREND_UP = "UP"
TREND_DOWN = "DOWN"
TREND_FLAT = "FLAT"


@dataclass
class SignalResult:
    symbol: str
    signal: str
    trend: str
    rsi_value: float
    ema_fast_value: float
    ema_slow_value: float
    atr_value: float
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


def _determine_trend(ema_fast_value: float, ema_slow_value: float) -> str:
    if ema_fast_value > ema_slow_value:
        return TREND_UP
    if ema_fast_value < ema_slow_value:
        return TREND_DOWN
    return TREND_FLAT


def generate_signal(df: pd.DataFrame, config: Config, symbol: str) -> SignalResult:
    """Bepaalt het handelssignaal voor één paar op basis van OHLC-data.

    `df` moet minstens de kolommen 'high', 'low' en 'close' bevatten, met
    genoeg rijen om `config.ema_slow` candles te kunnen middelen.
    """
    if len(df) < config.ema_slow:
        raise ValueError(
            f"{symbol}: te weinig candles ({len(df)}) voor ema_slow={config.ema_slow}"
        )

    close = df["close"]

    ema_fast_series = ema(close, config.ema_fast)
    ema_slow_series = ema(close, config.ema_slow)
    rsi_series = rsi(close, config.rsi_period)
    atr_series = atr(df, config.atr_period)

    ema_fast_value = float(ema_fast_series.iloc[-1])
    ema_slow_value = float(ema_slow_series.iloc[-1])
    rsi_value = float(rsi_series.iloc[-1])
    atr_value = float(atr_series.iloc[-1])
    entry = float(close.iloc[-1])

    trend = _determine_trend(ema_fast_value, ema_slow_value)

    signal = HOLD
    if trend == TREND_UP and rsi_value > config.rsi_buy_threshold:
        signal = BUY
    elif trend == TREND_DOWN and rsi_value < config.rsi_sell_threshold:
        signal = SELL

    stop_loss: float | None = None
    take_profit: float | None = None

    if signal == BUY:
        stop_loss = entry - atr_value * config.atr_multiplier
        risk = entry - stop_loss
        take_profit = entry + risk * config.rr_ratio
    elif signal == SELL:
        stop_loss = entry + atr_value * config.atr_multiplier
        risk = stop_loss - entry
        take_profit = entry - risk * config.rr_ratio

    return SignalResult(
        symbol=symbol,
        signal=signal,
        trend=trend,
        rsi_value=rsi_value,
        ema_fast_value=ema_fast_value,
        ema_slow_value=ema_slow_value,
        atr_value=atr_value,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )
