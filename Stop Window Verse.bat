@echo off
setlocal EnableDelayedExpansion

rem ── Window Verse stop ───────────────────────────────────────────────────
cd /d "%~dp0"

set "PID_FILE=logs\windowverse.pid"
if not exist "%PID_FILE%" set "PID_FILE=logs\multiverse.pid"

if not exist "%PID_FILE%" (
    echo No running Window Verse process found.
    pause
    exit /b 0
)

set /p WV_PID=<"%PID_FILE%"

tasklist /FI "PID eq !WV_PID!" 2>nul | find "!WV_PID!" >nul
if errorlevel 1 (
    echo Window Verse ^(PID !WV_PID!^) isn't running anymore.
    del "logs\windowverse.pid" >nul 2>&1
    del "logs\multiverse.pid" >nul 2>&1
    pause
    exit /b 0
)

taskkill /PID !WV_PID! /T /F >nul 2>&1
if errorlevel 1 (
    echo Could not stop PID !WV_PID!.
) else (
    echo Window Verse stopped ^(PID !WV_PID!^).
)

del "logs\windowverse.pid" >nul 2>&1
del "logs\multiverse.pid" >nul 2>&1
pause
