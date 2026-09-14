#!/usr/bin/env python3
"""Test de read-only MT5-koppeling zonder de volledige analyse te draaien.

Handig om te controleren of de terminal open/ingelogd is, en of de
geconfigureerde symbolen bestaan bij jouw broker, voordat je `analyze.py`
draait. Plaatst geen orders en wijzigt niets.
"""

from __future__ import annotations

import sys

from mt5_signals.config import load_config
from mt5_signals.mt5_client import check_connection


def main() -> int:
    config = load_config()
    diagnostics = check_connection(config.pairs)
    terminal = diagnostics.terminal

    print("=== MT5 connectie-check (read-only, plaatst geen orders) ===")
    if not terminal.connected:
        print(f"NIET verbonden: {terminal.error}")
        print()
        print("Controleer:")
        print("  - is de MT5-terminal open en ingelogd op je account?")
        print("  - is het 'MetaTrader5' python-package geinstalleerd")
        print("    (pip install -r requirements.txt)?")
        print("  - draait Python met dezelfde architectuur (64-bit) als de terminal?")
        return 1

    print(f"Verbonden met terminal: {terminal.terminal_name}")
    print(f"Account: {terminal.account_login} @ {terminal.account_server}")
    print(f"Trade allowed (terminal-instelling, niet gebruikt hier): {terminal.trade_allowed}")
    print()
    print(f"{'Symbool':<10} {'Status':<10} {'Bid':>10} {'Ask':>10}  Toelichting")
    print("-" * 60)

    all_ok = True
    for status in diagnostics.symbols:
        if status.available:
            print(f"{status.symbol:<10} {'OK':<10} {status.bid:>10.5f} {status.ask:>10.5f}")
        else:
            all_ok = False
            print(f"{status.symbol:<10} {'FOUT':<10} {'-':>10} {'-':>10}  {status.error}")

    print()
    if all_ok:
        print("Alle geconfigureerde paren zijn beschikbaar. Je kunt `python analyze.py` draaien.")
        return 0

    print(
        "Een of meer paren zijn niet gevonden. Controleer de exacte symboolnamen "
        "in het Market Watch-venster van MT5 (broker-suffixes zoals '.a' of 'm') "
        "en pas config.yaml aan."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
