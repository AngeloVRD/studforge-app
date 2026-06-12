@echo off
title Studforge - Ersteinrichtung
color 0A
echo.
echo  =========================================
echo    STUDFORGE - Ersteinrichtung
echo  =========================================
echo.

set PYTHON=
for %%P in (
  "C:\Python312\python.exe"
  "C:\Python311\python.exe"
  "C:\Python310\python.exe"
  "C:\Python39\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
) do (
  if exist %%P set PYTHON=%%P
)

if defined PYTHON (
  echo  [OK] Python gefunden: %PYTHON%
  goto :install_packages
)

echo  Python wird heruntergeladen (ca. 25 MB) ...
powershell -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python-installer.exe' }"

if not exist "%TEMP%\python-installer.exe" (
  echo  [FEHLER] Download fehlgeschlagen.
  echo  Bitte Python manuell installieren: https://www.python.org/downloads/
  pause
  exit /b 1
)

echo  Python wird installiert ...
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
del "%TEMP%\python-installer.exe"

set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) do (
  if exist %%P set PYTHON=%%P
)

if not defined PYTHON (
  echo  [FEHLER] Installation fehlgeschlagen.
  echo  Bitte Python manuell installieren: https://www.python.org/downloads/
  pause
  exit /b 1
)

echo  [OK] Python installiert!
echo.

:install_packages
echo  Pakete werden installiert ...
"%PYTHON%" -m pip install --upgrade pip --quiet
"%PYTHON%" -m pip install flask pywebview --quiet

echo  [OK] Flask und PyWebView installiert!
echo.
echo  =========================================
echo    Installation abgeschlossen!
echo    Starte das Programm mit: start.bat
echo  =========================================
echo.
pause
