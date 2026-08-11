@echo off
setlocal EnableDelayedExpansion

rem ── MultiVerse stop ─────────────────────────────────────────────────────
rem Double-click this when you're done. It stops the background backend
rem process started by "Start MultiVerse.bat". Closing the browser tab
rem alone does NOT stop the backend -- use this instead.
rem ────────────────────────────────────────────────────────────────────────

cd /d "%~dp0"

if not exist "logs\multiverse.pid" (
    echo No running MultiVerse process found ^(logs\multiverse.pid is missing^).
    echo If you know it's still running, open Task Manager and end "pythonw.exe".
    pause
    exit /b 0
)

set /p MV_PID=<"logs\multiverse.pid"

tasklist /FI "PID eq !MV_PID!" 2>nul | find "!MV_PID!" >nul
if errorlevel 1 (
    echo MultiVerse ^(PID !MV_PID!^) isn't running anymore -- nothing to stop.
    del "logs\multiverse.pid" >nul 2>&1
    pause
    exit /b 0
)

taskkill /PID !MV_PID! /T /F >nul 2>&1
if errorlevel 1 (
    echo Could not stop PID !MV_PID! -- it may need Task Manager to end it manually.
) else (
    echo MultiVerse stopped ^(PID !MV_PID!^).
)

del "logs\multiverse.pid" >nul 2>&1
pause
