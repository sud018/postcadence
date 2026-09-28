@echo off
rem Double-click to start PostCadence. The first run sets everything up.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First run: creating a private Python environment in .venv ...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo.
        echo Python 3.10 or newer is needed. Get it from https://www.python.org/downloads/
        echo and tick "Add python.exe to PATH" during install. Then double-click this file again.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 (
        echo.
        echo Installing the packages failed - check your internet connection and try again.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m web
pause
