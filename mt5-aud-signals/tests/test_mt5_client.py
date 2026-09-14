"""Tests voor de MT5-koppeling die geen live terminal nodig hebben.

Deze tests draaien op elk systeem waar het 'MetaTrader5' package niet
geinstalleerd is (zoals deze CI/sandbox-omgeving): ze valideren dat de
tool dat nette, voorspelbare foutafhandeling geeft in plaats van te crashen.
"""

from __future__ import annotations

import importlib.util

import pytest

from mt5_signals.mt5_client import MT5UnavailableError, check_connection, fetch_rates

MT5_PACKAGE_INSTALLED = importlib.util.find_spec("MetaTrader5") is not None

pytestmark = pytest.mark.skipif(
    MT5_PACKAGE_INSTALLED,
    reason="Deze tests valideren het gedrag zonder het MetaTrader5-package.",
)


def test_fetch_rates_raises_when_package_missing():
    with pytest.raises(MT5UnavailableError):
        fetch_rates("AUDUSD", "H1", 300)


def test_check_connection_reports_disconnected_when_package_missing():
    diagnostics = check_connection(["AUDUSD", "EURAUD"])

    assert diagnostics.terminal.connected is False
    assert diagnostics.terminal.error is not None
    assert diagnostics.symbols == []
