@echo off
REM Eenmalige installatie op Windows. Alles gratis.
cd /d "%~dp0"
py -3 -m venv .venv 2>nul || python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
echo.
python -m clipos kostenwacht
echo.
where claude >nul 2>nul || echo Let op: Claude Code is nog niet geinstalleerd - zie https://code.claude.com/docs (inloggen met je Pro-account).
echo Klaar. Volgende stappen:
echo   1. start.bat                  - dashboard openen
echo   2. claude, dan /campagne      - campagne toevoegen (of /video ^<link^>)
echo   3. python -m clipos planning  - dagelijkse run inplannen
pause
