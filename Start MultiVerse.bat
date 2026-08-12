@echo off
setlocal EnableDelayedExpansion

rem ── MultiVerse launcher ─────────────────────────────────────────────────
rem Double-click this file to start everything. It:
rem   1. Starts server.py in the background, no visible console window.
rem   2. Waits a few seconds for it to actually bind the WebSocket port.
rem   3. Opens ui/index.html in your default browser.
rem You never need to open a terminal or run a Python command yourself.
rem This window (a small confirmation box) closes on its own -- it is not
rem the backend, and closing it does NOT stop MultiVerse.
rem ────────────────────────────────────────────────────────────────────────

cd /d "%~dp0"

if not exist "logs" mkdir "logs"

rem Prefer the project's own virtual environment if it exists, otherwise
rem fall back to whatever "python" resolves to on PATH.
set "MV_PY=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%MV_PY%" set "MV_PY=pythonw.exe"

echo Checking for an already-running MultiVerse...
if exist "logs\multiverse.pid" (
    set /p OLD_PID=<"logs\multiverse.pid"
    tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
    if not errorlevel 1 (
        echo MultiVerse is already running ^(PID !OLD_PID!^) -- just opening the UI.
        start "" "%~dp0ui\index.html"
        timeout /t 2 >nul
        exit /b 0
    )
)

echo Starting MultiVerse backend in the background...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Start-Process -FilePath '%MV_PY%' -ArgumentList 'server.py' -WorkingDirectory '%~dp0' -RedirectStandardOutput 'logs\server_boot.log' -RedirectStandardError 'logs\server_boot_err.log' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ascii 'logs\multiverse.pid'"

if not exist "logs\multiverse.pid" (
    echo.
    echo Something went wrong starting the backend. Opening logs\server_boot_err.log ...
    echo Also make sure the .venv folder exists here, or that "pythonw" works from
    echo a normal terminal ^(pythonw --version^).
    if exist "logs\server_boot_err.log" notepad "logs\server_boot_err.log"
    pause
    exit /b 1
)

echo Waiting for the backend to come online...
timeout /t 4 /nobreak >nul

echo Opening MultiVerse UI...
start "" "http://127.0.0.1:8766/ui/index.html"

echo.
echo MultiVerse is running in the background (no visible window -- that's
echo expected). The UI will show "connected" within a couple of seconds
echo even if it briefly says "disconnected" first.
echo.
echo Backend log:  logs\server_boot.log
echo Error log:    logs\server_boot_err.log
echo To stop MultiVerse, run "Stop MultiVerse.bat" -- do not just close
echo this window, it isn't the backend and closing it won't stop anything.
echo.
timeout /t 5 >nul
