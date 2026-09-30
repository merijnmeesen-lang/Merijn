@echo off
REM Clip-OS bijwerken naar de nieuwste versie. Je instellingen, campagnes en video's blijven staan.
cd /d "%~dp0"
where git >nul 2>nul || (echo Git is niet gevonden. Installeer het eerst met:  winget install --id Git.Git -e & pause & exit /b 1)
git rev-parse --is-inside-work-tree >nul 2>nul || (echo Deze map is een zip-versie. Volg eenmalig "Overstappen naar updates met 1 klik" in README.md. & pause & exit /b 1)
echo Nieuwste versie ophalen...
git pull --ff-only || (echo. & echo Bijwerken lukte niet. Stuur een screenshot van dit venster naar Claude. & pause & exit /b 1)
call .venv\Scripts\activate.bat || (echo Eerst setup.bat draaien & pause & exit /b 1)
python -m pip install -r requirements.txt -q
echo.
python -m clipos kostenwacht
echo.
echo Klaar! Sluit Clip-OS (het zwarte venster) en open start.bat opnieuw.
pause
