@echo off
REM ═══════════════════════════════════════════════════════════════
REM  PM06 Tool — First-Time Setup
REM  Creates Desktop shortcut and Start Menu entry.
REM  Run this ONCE after extracting the zip.
REM ═══════════════════════════════════════════════════════════════

echo.
echo ══════════════════════════════════════════════════════════════
echo   PM06 Tool — Setup
echo ══════════════════════════════════════════════════════════════
echo.

set "APP_DIR=%~dp0"
set "EXE_PATH=%APP_DIR%PM06_Tool.exe"

REM Check exe exists
if not exist "%EXE_PATH%" (
    echo [ERROR] PM06_Tool.exe not found in this folder.
    echo         Make sure you extracted the full zip.
    pause
    exit /b 1
)

REM ── Create Desktop Shortcut ──────────────────────────────────
echo [1/2] Creating Desktop shortcut...
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\PM06 Tool.lnk"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%SHORTCUT%'); ^
   $sc.TargetPath = '%EXE_PATH%'; ^
   $sc.WorkingDirectory = '%APP_DIR%'; ^
   $sc.Description = 'TPDDL PM06 Executive Summary Generator'; ^
   $sc.Save()"

if exist "%SHORTCUT%" (
    echo         Desktop shortcut created.
) else (
    echo         [WARN] Could not create Desktop shortcut.
)

REM ── Create Start Menu Entry ──────────────────────────────────
echo [2/2] Creating Start Menu entry...
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "SM_SHORTCUT=%STARTMENU%\PM06 Tool.lnk"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $sc = $ws.CreateShortcut('%SM_SHORTCUT%'); ^
   $sc.TargetPath = '%EXE_PATH%'; ^
   $sc.WorkingDirectory = '%APP_DIR%'; ^
   $sc.Description = 'TPDDL PM06 Executive Summary Generator'; ^
   $sc.Save()"

if exist "%SM_SHORTCUT%" (
    echo         Start Menu entry created.
    echo         You can now search "PM06 Tool" in Windows search.
) else (
    echo         [WARN] Could not create Start Menu entry.
)

echo.
echo ══════════════════════════════════════════════════════════════
echo   Setup complete! You can now:
echo     - Double-click "PM06 Tool" on your Desktop
echo     - Search "PM06 Tool" in Windows Start Menu
echo     - Or double-click PM06_Tool.exe directly
echo ══════════════════════════════════════════════════════════════
echo.
pause
