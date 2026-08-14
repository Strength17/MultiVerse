@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "MV_PY=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%MV_PY%" set "MV_PY=pythonw.exe"
if exist "logs\windowverse.pid" (
    set /p OLD_PID=<"logs\windowverse.pid"
    tasklist /FI "PID eq !OLD_PID!" 2>nul | find "!OLD_PID!" >nul
    if not errorlevel 1 (
        start "" "http://127.0.0.1:8766/ui/index.html"
        exit /b 0
    )
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Start-Process -FilePath '%MV_PY%' -ArgumentList 'server.py' -WorkingDirectory '%~dp0' -RedirectStandardOutput 'logs\server_boot.log' -RedirectStandardError 'logs\server_boot_err.log' -WindowStyle Hidden -PassThru; $p.Id | Out-File -Encoding ascii 'logs\windowverse.pid'"
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:8766/ui/index.html"
