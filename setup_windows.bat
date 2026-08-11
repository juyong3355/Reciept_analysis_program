@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.11 or 3.12 was not found in PATH.
  echo Install 64-bit Python and run this file again.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating virtual environment...
  python -m venv .venv || exit /b 1
)

echo [2/4] Updating packaging tools...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel || exit /b 1

echo [3/4] Installing runtime dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt || exit /b 1

echo [4/4] Installing Receipt MVP...
".venv\Scripts\python.exe" -m pip install --no-deps -e . || exit /b 1

echo.
echo Installation completed. Run run_app.bat to start the application.
exit /b 0
