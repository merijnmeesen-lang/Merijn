"""Uitleg om de dagelijkse run in te plannen (gratis, met de planner van je eigen computer)."""

from __future__ import annotations

import sys

from . import werk


def uitleg() -> None:
    root = werk.ROOT.resolve()
    print("Dagelijkse run inplannen (elke dag om 07:00; je computer moet aan staan):\n")
    if sys.platform.startswith("win"):
        print("Open 'Opdrachtprompt' en plak:")
        print(f'  schtasks /Create /SC DAILY /ST 07:00 /TN "Clip-OS dagelijks" /TR "\\"{root}\\dagelijks.bat\\""')
        print("\nUitzetten:  schtasks /Delete /TN \"Clip-OS dagelijks\" /F")
    else:
        print("Open 'Terminal', typ  crontab -e  en voeg deze regel toe:")
        print(f'  0 7 * * * cd "{root}" && ./dagelijks.sh >> data/dagelijks.log 2>&1')
        print("\nUitzetten: haal de regel weer weg met  crontab -e")
    print("\nHandmatig testen kan altijd met dagelijks.bat (Windows) of ./dagelijks.sh (Mac/Linux).")
