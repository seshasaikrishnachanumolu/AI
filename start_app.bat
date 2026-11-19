@echo off
rem Double-click to start SmartWaste AI. Keep this window open while using the app; close it (or press Ctrl+C) to stop.
setlocal
cd /d "%~dp0"
title SmartWaste AI server

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] The app is not set up yet. Double-click setup_windows.bat first.
  if /i not "%~1"=="nopause" pause
  exit /b 1
)
if not exist ".env" (
  echo [ERROR] The settings file .env is missing. Double-click setup_windows.bat first.
  if /i not "%~1"=="nopause" pause
  exit /b 1
)

if not defined PORT set "PORT=8000"
echo.
echo Starting SmartWaste AI on http://localhost:%PORT% ...
echo The browser opens by itself in a few seconds. If port %PORT% is busy, close the other program or set PORT=8001 first.
echo.
start "" /b cmd /c "timeout /t 12 /nobreak >nul & start http://localhost:%PORT%"
".venv\Scripts\python.exe" serve.py
echo.
echo Server stopped.
if /i not "%~1"=="nopause" pause
