#!/usr/bin/env bash
# Opent Clip-OS in je browser (Chrome). Laat dit venster open zolang je werkt.
cd "$(dirname "$0")"
source .venv/bin/activate || { echo "Eerst ./setup.sh draaien"; exit 1; }
python -m clipos dashboard
