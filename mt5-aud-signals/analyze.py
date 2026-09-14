#!/usr/bin/env python3
"""Entrypoint van de AUD-signalentool.

Haalt koersdata op (live via MT5, of demo-data als MT5 niet beschikbaar is),
berekent per paar een BUY/SELL/HOLD-signaal met entry/stoploss/take-profit,
en print een leesbaar rapport.

Deze tool plaatst NOOIT orders -- ze is uitsluitend adviserend.
"""

from __future__ import annotations

import sys

from mt5_signals.config import load_config
from mt5_signals.data_source import get_price_data
from mt5_signals.report import print_report
from mt5_signals.signals import generate_signal


def main() -> int:
    config = load_config()

    results = []
    for symbol in config.pairs:
        df, source = get_price_data(symbol, config)
        result = generate_signal(df, config, symbol)
        results.append((result, source))

    print_report(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
