#!/usr/bin/env bash
# Clip-OS bijwerken naar de nieuwste versie. Je instellingen, campagnes en video's blijven staan.
set -e
cd "$(dirname "$0")"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Deze map is een zip-versie. Volg eenmalig 'Overstappen naar updates met 1 klik' in README.md."; exit 1; }
echo "Nieuwste versie ophalen..."
git pull --ff-only
source .venv/bin/activate
python -m pip install -r requirements.txt -q
python -m clipos kostenwacht
echo "Klaar! Stop Clip-OS (Ctrl+C) en start ./start.sh opnieuw."
