@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] The virtual environment is missing.
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m receipt_mvp gui
exit /b %errorlevel%
