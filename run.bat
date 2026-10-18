@echo off
cd /d "%~dp0"
if exist "Quant Trading AI.exe" (
  start "" "Quant Trading AI.exe"
  exit /b
)
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe launch.py
