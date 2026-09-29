@echo off
REM Dagelijkse run: Claude bedenkt nieuwe ideeen en zet een melding in het dashboard.
REM Draait op je Claude Pro-abonnement. HARDE KOSTENSTOP: zie hieronder.
cd /d "%~dp0"
if not exist data mkdir data

REM 1) Nooit via betaalde sleutels (anders rekent Claude Code per gebruik af i.p.v. via Pro).
set ANTHROPIC_API_KEY=
set ANTHROPIC_AUTH_TOKEN=
set CLAUDE_CODE_USE_BEDROCK=
set CLAUDE_CODE_USE_VERTEX=
set OPENAI_API_KEY=
set ELEVENLABS_API_KEY=
set REPLICATE_API_TOKEN=
set ASSEMBLYAI_API_KEY=
set DEEPGRAM_API_KEY=
set GEMINI_API_KEY=

call .venv\Scripts\activate.bat || (echo Eerst setup.bat draaien & exit /b 1)

REM 2) Kostenwacht moet groen zijn, anders start Claude niet eens.
python -m clipos kostenwacht >> data\dagelijks.log 2>&1
if errorlevel 1 (
  echo %date% %time% Dagelijkse run gestopt door de kostenwacht >> data\dagelijks.log
  exit /b 1
)

REM 3) Claude (Pro-login) met een maximum aantal stappen.
echo === %date% %time% === >> data\dagelijks.log
claude -p "/dagelijks" --permission-mode acceptEdits --max-turns 80 >> data\dagelijks.log 2>&1
