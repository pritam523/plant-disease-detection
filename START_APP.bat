@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv-app\Scripts\python.exe"

if not exist "%PY%" (
    echo Creating local Python environment. This happens only once.
    py -3.12 -m venv .venv-app
    if errorlevel 1 python -m venv .venv-app
    if errorlevel 1 (
        echo.
        echo Python 3.12 is required. Install it from python.org, then run this file again.
        pause
        exit /b 1
    )
    "%~dp0.venv-app\Scripts\python.exe" -m pip install --upgrade pip
    "%~dp0.venv-app\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist ".env" (
    echo Creating .env from .env.example.
    echo Add optional API keys and admin settings later; see CONFIGURATION.md.
    copy /Y .env.example .env >nul
)

echo.
echo Starting Plant Disease Detection...
echo Open http://127.0.0.1:8000/ in your browser.
echo Press Ctrl+C to stop the server.
echo.

"%PY%" run.py check
if errorlevel 1 (
    echo.
    echo Startup check failed. Read the message above, then fix the issue and run again.
    pause
    exit /b 1
)

"%PY%" run.py
pause
