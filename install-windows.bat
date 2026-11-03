@echo off
:: Conekit installer for VLC 3 on Windows.
:: Copies the Conekit skins into VLC's skins folder so they show up in VLC's skin chooser.
setlocal
set "DEST=%APPDATA%\vlc\skins"
set "SRC=%~dp0"
if exist "%SRC%dist\Conekit-Dark.vlt" set "SRC=%SRC%dist\"

if not exist "%SRC%Conekit-Dark.vlt" (
  echo Could not find Conekit-Dark.vlt next to this script.
  echo Put install-windows.bat in the same folder as the .vlt files and run it again.
  pause
  exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%Conekit-*.vlt" "%DEST%\" >nul

echo.
echo Conekit skins installed to:
echo   %DEST%
echo.
echo To turn it on in VLC:
echo   1. Tools ^> Preferences ^> Interface
echo   2. Choose "Use custom skin", then pick Conekit-Dark.vlt or Conekit-Light.vlt from the folder above
echo   3. Save and restart VLC
echo.
echo Once a skin is active, you can switch between them by right-clicking the player and choosing Interface ^> Choose skin.
echo.
pause
