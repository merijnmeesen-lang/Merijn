@echo off
REM Maakt op je bureaublad een snelkoppeling "Clip-OS" met het Clip-OS-pictogram.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Clip-OS.lnk');" ^
  "$s.TargetPath = '%~dp0start.bat'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = '%~dp0clip-os.ico,0';" ^
  "$s.Description = 'Clip-OS openen'; $s.Save()"
if errorlevel 1 (
  echo Snelkoppeling maken is niet gelukt.
) else (
  echo Klaar! Op je bureaublad staat nu "Clip-OS" met het Clip-OS-pictogram.
  echo Je oude snelkoppeling mag je weggooien.
)
pause
