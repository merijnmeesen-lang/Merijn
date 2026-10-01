#!/usr/bin/env bash
# Dagelijkse run: Claude bedenkt nieuwe ideeën en zet een melding in het dashboard.
# Draait op je Claude Pro-abonnement. HARDE KOSTENSTOP: zie hieronder.
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:$PATH"
mkdir -p data

# 1) Nooit via betaalde sleutels: als deze bestaan, rekent Claude Code per gebruik af i.p.v. via Pro.
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX \
      OPENAI_API_KEY ELEVENLABS_API_KEY REPLICATE_API_TOKEN ASSEMBLYAI_API_KEY DEEPGRAM_API_KEY GEMINI_API_KEY

source .venv/bin/activate || { echo "Eerst ./setup.sh draaien"; exit 1; }

# 2) Kostenwacht moet groen zijn, anders start Claude niet eens.
if ! python -m clipos kostenwacht; then
  echo "$(date) ⛔ Dagelijkse run gestopt door de kostenwacht" >> data/dagelijks.log
  exit 1
fi

# 3) Claude (Pro-login) met een maximum aantal stappen.
echo "=== $(date) ===" >> data/dagelijks.log
# 3a) Nieuwe video's zoeken, downloaden en uitschrijven (gewone code, geen Claude)
python -m clipos dag >> data/dagelijks.log 2>&1
claude -p "/dagelijks" --permission-mode acceptEdits --max-turns 80 >> data/dagelijks.log 2>&1
