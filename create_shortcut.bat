@echo off
title Studforge - Desktop-Verknuepfung einrichten
color 0A
cd /d "%~dp0"

echo.
echo  ================================================
echo   Studforge - Verknuepfung wird eingerichtet ...
echo  ================================================
echo.

:: Python suchen
set PYTHON=
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "C:\Python311\python.exe"
  "C:\Python312\python.exe"
  "C:\Python310\python.exe"
  "python.exe"
) do (
  if exist %%~P set PYTHON=%%~P
)

if not defined PYTHON (
  echo  [FEHLER] Python nicht gefunden.
  echo  Bitte zuerst INSTALL.bat ausfuehren!
  echo.
  pause
  exit /b 1
)

echo  Python gefunden: %PYTHON%
echo.

:: Icon generieren
echo  Erstelle Icon ...
"%PYTHON%" "%~dp0icon.py"
if errorlevel 1 (
  echo.
  echo  [FEHLER] Icon konnte nicht erstellt werden.
  pause
  exit /b 1
)

:: Desktop-Verknuepfung per PowerShell erstellen
echo  Erstelle Desktop-Verknuepfung ...

set APPDIR=%~dp0
:: Letzten Backslash entfernen
if "%APPDIR:~-1%"=="\" set APPDIR=%APPDIR:~0,-1%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws  = New-Object -ComObject WScript.Shell;" ^
  "$dsk = [Environment]::GetFolderPath('Desktop');" ^
  "$sc  = $ws.CreateShortcut($dsk + '\Studforge.lnk');" ^
  "$sc.TargetPath      = '%APPDIR%\launcher.vbs';" ^
  "$sc.WorkingDirectory= '%APPDIR%';" ^
  "$sc.IconLocation    = '%APPDIR%\icon.ico';" ^
  "$sc.Description     = 'Studforge 3D Manufaktur';" ^
  "$sc.Save();" ^
  "Write-Host '  Verknuepfung gespeichert unter: ' + $dsk + '\Studforge.lnk'"

if errorlevel 1 (
  echo.
  echo  [FEHLER] Verknuepfung konnte nicht erstellt werden.
  pause
  exit /b 1
)

echo.
echo  ================================================
echo   Fertig! "Studforge" ist jetzt auf dem Desktop.
echo   Doppelklick startet das Programm direkt.
echo  ================================================
echo.
pause
