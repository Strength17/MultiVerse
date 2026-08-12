@echo off
setlocal
cd /d "%~dp0"
set "SRC=dist\MultiVerse"
set "DEST=%ProgramFiles%\MultiVerse"
if not exist "%SRC%\MultiVerse.exe" (
  echo Run PyInstaller first: pyinstaller multiverse.spec --noconfirm
  pause
  exit /b 1
)
echo Installing MultiVerse to %DEST% ...
mkdir "%DEST%" 2>nul
xcopy /E /I /Y "%SRC%\*" "%DEST%\"
echo.
echo Installed. User data folder: %USERPROFILE%\Documents\MultiVerse\data\
echo Put Bible databases there — see data\README_DATA.txt
echo.
pause
