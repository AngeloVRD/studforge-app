@echo off
title Studforge - 3D Manufaktur
color 0A

set PYTHON=
for %%P in (
  "python.exe"
  "python3.exe"
  "C:\Python312\python.exe"
  "C:\Python311\python.exe"
  "C:\Python310\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
  if exist %%P set PYTHON=%%P
)

if not defined PYTHON (
  echo.
  echo  [FEHLER] Python nicht gefunden.
  echo  Bitte zuerst INSTALL.bat ausfuehren.
  echo.
  pause
  exit /b 1
)

:: PyWebView pruefen, sonst im Browser oeffnen
"%PYTHON%" -c "import webview" 2>nul
if errorlevel 1 (
  echo  PyWebView nicht gefunden, wird installiert ...
  "%PYTHON%" -m pip install pywebview --quiet
)

:: Flask pruefen
"%PYTHON%" -c "import flask" 2>nul
if errorlevel 1 (
  echo  Flask nicht gefunden, wird installiert ...
  "%PYTHON%" -m pip install flask --quiet
)

cd /d "%~dp0"
"%PYTHON%" main.py
