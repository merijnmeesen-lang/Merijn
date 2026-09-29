@echo off
REM Opent het dashboard in je browser. Laat dit venster open zolang je video's goedkeurt.
cd /d "%~dp0"
call .venv\Scripts\activate.bat || (echo Eerst setup.bat draaien & pause & exit /b 1)
python -m clipos dashboard
pause
