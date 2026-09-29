#!/usr/bin/env bash
# Eenmalige installatie op Mac/Linux. Alles gratis.
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
chmod +x dagelijks.sh start.sh
echo
python -m clipos kostenwacht || true
echo
if ! command -v claude >/dev/null 2>&1; then
  echo "⚠️  Claude Code is nog niet geïnstalleerd: zie https://code.claude.com/docs (inloggen met je Pro-account)."
fi
echo "Klaar. Volgende stappen:"
echo "  1. ./start.sh             → dashboard openen"
echo "  2. claude  → /campagne    → campagne toevoegen (of /video <link>)"
echo "  3. python -m clipos planning   → dagelijkse run inplannen"
