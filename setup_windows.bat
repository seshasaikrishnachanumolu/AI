@echo off
rem ===================================================================================================
rem  SmartWaste AI - one-time setup for Windows. Double-click it (or run it in a terminal).
rem  It is safe to run again. Needs Python 3.10 - 3.13 (64-bit) and an internet connection.
rem ===================================================================================================
setlocal
cd /d "%~dp0"
title SmartWaste AI - setup
echo.
echo ===== SmartWaste AI setup =====
echo.

rem ---- 1. find a suitable Python -------------------------------------------------------------------
set "PY="
call :try python
call :try "py -3.12"
call :try "py -3.13"
call :try "py -3.11"
call :try "py -3.10"
if defined PY goto :have_python

echo [ERROR] No suitable Python found. You need Python 3.10, 3.11, 3.12 or 3.13 - 64-bit.
python --version 2>nul && echo        The Python on this computer is not in that range.
echo.
echo   1. Download Python 3.12 from https://www.python.org/downloads/windows/
echo   2. In the installer tick "Add python.exe to PATH", then click Install.
echo   3. Close this window and run setup_windows.bat again.
goto :fail

:try
if defined PY goto :eof
%~1 -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) and sys.maxsize>2**32 else 1)" >nul 2>nul
if not errorlevel 1 set "PY=%~1"
goto :eof

:have_python
echo [1/4] Using Python: %PY%
%PY% --version

rem ---- 2. private environment ----------------------------------------------------------------------
echo.
echo [2/4] Creating the private Python environment (.venv) ...
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the .venv folder. Is there free disk space, and is this folder writable?
    goto :fail
  )
) else (
  echo       .venv already exists - keeping it.
)

rem ---- 3. packages ---------------------------------------------------------------------------------
echo.
echo [3/4] Installing packages. This downloads about 500 MB and takes 5 to 15 minutes.
echo       Please wait - do not close this window. Yellow warnings are normal.
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Package installation failed. Most often this is a lost internet connection.
  echo         Check your connection and run setup_windows.bat again - it continues where it stopped.
  goto :fail
)

rem ---- 4. settings + database ----------------------------------------------------------------------
echo.
echo [4/4] Creating settings and the database ...
".venv\Scripts\python.exe" scripts\first_run.py
if errorlevel 1 goto :fail

echo.
echo ===== All done! =====
echo   Start the app by double-clicking  start_app.bat   (or run:  .venv\Scripts\python serve.py )
echo   Then open  http://localhost:8000  in your browser.
echo   Administrator login page:  http://localhost:8000/admin/login
if /i not "%~1"=="nopause" pause
exit /b 0

:fail
echo.
echo Setup did not finish. Read the message above, fix it, and run setup_windows.bat again.
echo More help: README.md and docs\SmartWaste_AI_Setup_and_User_Guide.pdf (section "Troubleshooting").
if /i not "%~1"=="nopause" pause
exit /b 1
