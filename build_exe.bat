@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
".venv\Scripts\python.exe" -m PyInstaller --onefile --name update_data scripts\scrape_bca_dashboard.py

echo.
echo Build finished. EXE output:
echo %~dp0dist\update_data.exe
pause
