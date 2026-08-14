@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "PID_FILE=logs\windowverse.pid"
if not exist "%PID_FILE%" set "PID_FILE=logs\windowverse.pid"
if not exist "%PID_FILE%" ( echo No running WindowVerse process found. & pause & exit /b 0 )
set /p MV_PID=<"%PID_FILE%"
taskkill /PID !MV_PID! /T /F >nul 2>&1
del "logs\windowverse.pid" >nul 2>&1
del "logs\windowverse.pid" >nul 2>&1
echo WindowVerse stopped.
pause
