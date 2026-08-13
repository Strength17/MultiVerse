@echo off
setlocal EnableDelayedExpansion

rem ── Window Verse launcher ───────────────────────────────────────────────
cd /d "%~dp0"

if not exist "logs" mkdir "logs"

set "WV_PY=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%WV_PY%" set "WV_PY=pythonw.exe"

echo Checking for an already-running Window Verse...
if exist "logs\windowverse.pid" (
    set /p OLD_PID=<"logs\windowverse.pid"
    tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
    if not errorlevel 1 (
        echo Window Verse is already running ^(PID !OLD_PID!^) -- opening the UI.
        start "" "http://127.0.0.1:8766/ui/index.html"
        timeout /t 2 >nul
        exit /b 0
    )
)
if exist "logs\multiverse.pid" (
    set /p OLD_PID=<"logs\multiverse.pid"
    tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
    if not errorlevel 1 (
        echo Window Verse backend already running ^(legacy PID !OLD_PID!^).
        start "" "http://127.0.0.1:8766/ui/index.html"
        timeout /t 2 >nul
        exit /b 0
    )
)

echo Starting Window Verse backend in the background...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Start-Process -FilePath '%WV_PY%' -ArgumentList 'server.py' -WorkingDirectory '%~dp0' -RedirectStandardOutput 'logs\server_boot.log' -RedirectStandardError 'logs\server_boot_err.log' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ascii 'logs\windowverse.pid'"

if not exist "logs\windowverse.pid" (
    echo Backend failed to start. See logs\server_boot_err.log
    if exist "logs\server_boot_err.log" notepad "logs\server_boot_err.log"
    pause
    exit /b 1
)

timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8766/ui/index.html"
echo Window Verse is running. Use "Stop Window Verse.bat" to stop.
timeout /t 5 >nul
