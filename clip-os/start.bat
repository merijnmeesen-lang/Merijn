@echo off
REM Opent Clip-OS in je browser (Chrome). Laat dit venster open zolang je werkt.
cd /d "%~dp0"
call .venv\Scripts\activate.bat || (echo Eerst setup.bat draaien & pause & exit /b 1)
python -m clipos dashboard
pause
