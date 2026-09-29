#!/usr/bin/env bash
# Opent het dashboard in je browser. Laat dit venster open zolang je video's goedkeurt.
cd "$(dirname "$0")"
source .venv/bin/activate || { echo "Eerst ./setup.sh draaien"; exit 1; }
python -m clipos dashboard
