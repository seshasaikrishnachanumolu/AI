@echo off
rem Double-click to start SmartWaste AI. Keep this window open while using the app; close it to stop the server.
cd /d "%~dp0"
title SmartWaste AI server

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Virtual environment not found. Run these first:
  echo    python -m venv .venv
  echo    .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)

rem MySQL must be running (service MySQL92). Start it if it is stopped; needs an administrator prompt.
sc query MySQL92 | find "RUNNING" >nul
if errorlevel 1 (
  echo MySQL service is not running. Trying to start it...
  net start MySQL92
)

echo.
echo Starting SmartWaste AI on http://localhost:8000 ...
start "" /b cmd /c "timeout /t 12 /nobreak >nul & start http://localhost:8000"
".venv\Scripts\python.exe" serve.py
echo.
echo Server stopped.
pause
