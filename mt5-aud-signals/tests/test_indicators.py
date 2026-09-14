"""Unit tests voor de indicatoren, met vaste (deterministische) sample-data.

Geen MT5-verbinding nodig: alles werkt op handmatig opgebouwde pandas-data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mt5_signals.indicators import atr, ema, rsi


def test_ema_of_constant_series_equals_the_constant():
    closes = pd.Series([100.0] * 30)
    result = ema(closes, period=10)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_ema_matches_hand_computed_values():
    # span=3 -> alpha = 2 / (3 + 1) = 0.5
    closes = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = ema(closes, period=3)

    # y0=1, y1=0.5*2+0.5*1=1.5, y2=0.5*3+0.5*1.5=2.25,
    # y3=0.5*4+0.5*2.25=3.125, y4=0.5*5+0.5*3.125=4.0625
    expected = [1.0, 1.5, 2.25, 3.125, 4.0625]
    assert result.tolist() == pytest.approx(expected)


def test_rsi_is_100_when_price_only_rises():
    closes = pd.Series(np.arange(1, 50, dtype=float))
    result = rsi(closes, period=14)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_rsi_is_0_when_price_only_falls():
    closes = pd.Series(np.arange(50, 1, -1, dtype=float))
    result = rsi(closes, period=14)
    assert result.iloc[-1] == pytest.approx(0.0)


def test_rsi_is_nan_during_warmup_period():
    closes = pd.Series(np.arange(1, 10, dtype=float))  # minder dan period=14
    result = rsi(closes, period=14)
    assert result.isna().all()


def test_atr_is_zero_for_a_flat_market():
    n = 30
    df = pd.DataFrame({"high": [100.0] * n, "low": [100.0] * n, "close": [100.0] * n})
    result = atr(df, period=14)
    assert result.iloc[-1] == pytest.approx(0.0)


def test_atr_matches_hand_computed_value_for_constant_true_range():
    # close blijft vlak op 100, high/low liggen steeds 5 punten daarvan af
    # -> true range = high - low = 10 op elke candle.
    n = 30
    df = pd.DataFrame(
        {
            "high": [105.0] * n,
            "low": [95.0] * n,
            "close": [100.0] * n,
        }
    )
    result = atr(df, period=14)
    assert result.iloc[-1] == pytest.approx(10.0)
