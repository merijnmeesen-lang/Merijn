"""Unit tests voor de signaal-/SL/TP-berekening, met vaste sample-OHLC-data.

Geen MT5-verbinding nodig.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mt5_signals.config import Config
from mt5_signals.indicators import atr as atr_indicator
from mt5_signals.signals import BUY, HOLD, SELL, TREND_DOWN, TREND_UP, generate_signal

TEST_CONFIG = Config(
    pairs=["TESTPAIR"],
    timeframe="H1",
    bars_count=60,
    ema_fast=5,
    ema_slow=10,
    rsi_period=5,
    rsi_buy_threshold=50.0,
    rsi_sell_threshold=50.0,
    atr_period=5,
    atr_multiplier=1.5,
    rr_ratio=2.0,
)


def _build_trending_df(direction: str, n: int = 60, seed: int = 42) -> pd.DataFrame:
    """Bouwt een deterministische OHLC-reeks met een duidelijke, vaste trend."""
    rng = np.random.default_rng(seed)
    step = 0.5 if direction == "up" else -0.5
    increments = rng.normal(loc=step, scale=0.05, size=n)
    close = 100.0 + np.cumsum(increments)
    open_ = np.concatenate([[100.0], close[:-1]])
    high = np.maximum(open_, close) + 0.2
    low = np.minimum(open_, close) - 0.2
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close})


def test_uptrend_with_strong_momentum_gives_buy_signal():
    df = _build_trending_df("up")
    result = generate_signal(df, TEST_CONFIG, "TESTPAIR")

    assert result.trend == TREND_UP
    assert result.signal == BUY
    assert result.rsi_value > TEST_CONFIG.rsi_buy_threshold


def test_downtrend_with_weak_momentum_gives_sell_signal():
    df = _build_trending_df("down")
    result = generate_signal(df, TEST_CONFIG, "TESTPAIR")

    assert result.trend == TREND_DOWN
    assert result.signal == SELL
    assert result.rsi_value < TEST_CONFIG.rsi_sell_threshold


def test_buy_signal_has_correct_stop_loss_and_take_profit():
    df = _build_trending_df("up")
    result = generate_signal(df, TEST_CONFIG, "TESTPAIR")
    assert result.signal == BUY

    expected_atr = atr_indicator(df, TEST_CONFIG.atr_period).iloc[-1]
    expected_entry = df["close"].iloc[-1]
    expected_sl = expected_entry - expected_atr * TEST_CONFIG.atr_multiplier
    expected_risk = expected_entry - expected_sl
    expected_tp = expected_entry + expected_risk * TEST_CONFIG.rr_ratio

    assert result.entry == pytest.approx(expected_entry)
    assert result.stop_loss == pytest.approx(expected_sl)
    assert result.take_profit == pytest.approx(expected_tp)
    # Stoploss moet onder de entry liggen, take-profit erboven, bij een BUY.
    assert result.stop_loss < result.entry < result.take_profit


def test_sell_signal_has_correct_stop_loss_and_take_profit():
    df = _build_trending_df("down")
    result = generate_signal(df, TEST_CONFIG, "TESTPAIR")
    assert result.signal == SELL

    expected_atr = atr_indicator(df, TEST_CONFIG.atr_period).iloc[-1]
    expected_entry = df["close"].iloc[-1]
    expected_sl = expected_entry + expected_atr * TEST_CONFIG.atr_multiplier
    expected_risk = expected_sl - expected_entry
    expected_tp = expected_entry - expected_risk * TEST_CONFIG.rr_ratio

    assert result.entry == pytest.approx(expected_entry)
    assert result.stop_loss == pytest.approx(expected_sl)
    assert result.take_profit == pytest.approx(expected_tp)
    # Stoploss moet boven de entry liggen, take-profit eronder, bij een SELL.
    assert result.take_profit < result.entry < result.stop_loss


def test_take_profit_respects_configured_risk_reward_ratio():
    df = _build_trending_df("up")
    custom_config = Config(**{**TEST_CONFIG.__dict__, "rr_ratio": 3.0})
    result = generate_signal(df, custom_config, "TESTPAIR")

    risk = result.entry - result.stop_loss
    reward = result.take_profit - result.entry
    assert reward == pytest.approx(risk * 3.0)


def test_hold_signal_when_momentum_does_not_confirm_trend():
    # Sterke uptrend, maar de RSI-drempel staat onhaalbaar hoog gezet ->
    # de trend wordt niet bevestigd door momentum, dus geen trade-advies.
    df = _build_trending_df("up")
    strict_config = Config(**{**TEST_CONFIG.__dict__, "rsi_buy_threshold": 200.0})
    result = generate_signal(df, strict_config, "TESTPAIR")

    assert result.signal == HOLD
    assert result.stop_loss is None
    assert result.take_profit is None


def test_generate_signal_raises_when_not_enough_bars():
    df = _build_trending_df("up", n=5)
    with pytest.raises(ValueError):
        generate_signal(df, TEST_CONFIG, "TESTPAIR")
