"""Deterministische demo-koersdata, gebruikt als fallback wanneer er geen
live MT5-verbinding beschikbaar is (bv. tijdens ontwikkelen/testen op een
systeem zonder MT5-terminal).

Dit is GEEN vervanging voor echte marktdata en dient uitsluitend om de tool
end-to-end te kunnen draaien zonder MT5. Voor echte signalen is een live,
ingelogde MT5-terminal vereist (zie README.md).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Indicatieve startprijzen per paar, puur om realistische orde-groottes
# te tonen in de demo-data.
BASE_PRICES = {
    "AUDUSD": 0.6500,
    "AUDJPY": 97.00,
    "AUDNZD": 1.0800,
    "AUDCAD": 0.9000,
    "AUDCHF": 0.5800,
    "EURAUD": 1.6200,
    "GBPAUD": 1.9000,
}

DEFAULT_BASE_PRICE = 1.0000


def generate_sample_ohlc(symbol: str, bars: int, seed: int | None = None) -> pd.DataFrame:
    """Genereert een deterministische OHLC-reeks voor demo-doeleinden.

    Dezelfde `symbol` + `bars` + `seed` geeft altijd exact dezelfde data.
    """
    base_price = BASE_PRICES.get(symbol, DEFAULT_BASE_PRICE)
    rng_seed = seed if seed is not None else abs(hash(symbol)) % (2**32)
    rng = np.random.default_rng(rng_seed)

    # Kleine random walk met een lichte drift, geschaald naar de prijs
    # zodat de volatiliteit realistisch aanvoelt voor elk paar.
    step_scale = base_price * 0.0015
    drift = rng.normal(loc=0.0, scale=step_scale * 0.1, size=bars)
    noise = rng.normal(loc=0.0, scale=step_scale, size=bars)
    close = base_price + np.cumsum(drift + noise)

    open_ = np.concatenate([[base_price], close[:-1]])
    intrabar_range = np.abs(rng.normal(loc=step_scale, scale=step_scale * 0.3, size=bars))
    high = np.maximum(open_, close) + intrabar_range
    low = np.minimum(open_, close) - intrabar_range

    timestamps = pd.date_range(end=pd.Timestamp.utcnow(), periods=bars, freq="h")

    return pd.DataFrame(
        {
            "time": timestamps,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": rng.integers(50, 500, size=bars),
        }
    )
