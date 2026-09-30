@echo off
REM Eenmalig: je instellingen, campagnes, ideeen en video's uit de oude Clip-OS-map (de zip-versie)
REM overzetten naar deze map. De oude map blijft gewoon bestaan.
cd /d "%~dp0"
set "OUD=%USERPROFILE%\Downloads\Merijn-claude-tender-lovelace-ouybr3\Merijn-claude-tender-lovelace-ouybr3\clip-os"
if exist "%OUD%\clipos" goto gevonden
echo De oude Clip-OS-map staat niet op de verwachte plek.
set /p "OUD=Sleep de oude map clip-os in dit venster en druk op Enter: "
set "OUD=%OUD:"=%"
if not exist "%OUD%\clipos" (echo Dat is geen Clip-OS-map. & pause & exit /b 1)

:gevonden
echo Overzetten van: %OUD%
for %%F in (config.json lessenboek.md) do if exist "%OUD%\%%F" copy /Y "%OUD%\%%F" "%%F" >nul
robocopy "%OUD%\briefs" "briefs" *.json /XO /NFL /NDL /NJH /NJS /NP >nul
for %%D in (data jobs output) do if exist "%OUD%\%%D" robocopy "%OUD%\%%D" "%%D" /E /NFL /NDL /NJH /NJS /NP >nul
echo.
echo Klaar! Je accounts, campagnes, ideeen en video's staan nu ook in deze map.
echo Volgende stap: dubbelklik setup.bat (eenmalig) en daarna start.bat.
pause
