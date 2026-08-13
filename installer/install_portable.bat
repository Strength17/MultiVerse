@echo off
setlocal
set "SRC=dist\WindowVerse"
set "DEST=%ProgramFiles%\WindowVerse"
if not exist "%SRC%\WindowVerse.exe" (
  echo Run PyInstaller first: pyinstaller windowverse.spec --noconfirm
  pause
  exit /b 1
)
echo Installing Window Verse to %DEST% ...
xcopy /E /I /Y "%SRC%" "%DEST%"
echo Installed. User data folder: %USERPROFILE%\Documents\WindowVerse\data\
pause
