@echo off
REM ═══════════════════════════════════════════════════════════════
REM  PM06 Tool — Build distributable package
REM  Creates dist\PM06_Tool\ folder with everything needed.
REM  Share the entire PM06_Tool folder — no Python needed.
REM ═══════════════════════════════════════════════════════════════

echo.
echo ══════════════════════════════════════════════════════════════
echo   PM06 Tool — Build Script
echo ══════════════════════════════════════════════════════════════
echo.

REM Activate venv
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [ERROR] No virtual environment found. Run install.bat first.
    pause
    exit /b 1
)

REM Install PyInstaller if not present
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller --quiet
)

REM Clean previous builds
if exist "dist\PM06_Tool" (
    echo [INFO] Cleaning previous build...
    rmdir /s /q dist\PM06_Tool
)
if exist "build" (
    rmdir /s /q build
)

REM Build
echo.
echo [INFO] Building PM06_Tool...
echo        This may take 2-5 minutes on first run.
echo.

pyinstaller pm06_tool.spec --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output above.
    pause
    exit /b 1
)

REM Copy config files next to exe (user-editable copies)
echo [INFO] Copying config files...
if not exist "dist\PM06_Tool\config" mkdir "dist\PM06_Tool\config"
copy /y config\*.json dist\PM06_Tool\config\ >nul

REM Copy diagnose script
copy /y diagnose.py dist\PM06_Tool\ >nul

echo.
echo ══════════════════════════════════════════════════════════════
echo   BUILD COMPLETE!
echo ══════════════════════════════════════════════════════════════
echo.
echo   Output:  dist\PM06_Tool\
echo   Exe:     dist\PM06_Tool\PM06_Tool.exe
echo.
echo   TO DISTRIBUTE:
echo     1. Zip the entire dist\PM06_Tool\ folder
echo     2. Send PM06_Tool.zip to the other person
echo     3. They extract and double-click PM06_Tool.exe
echo     4. If issues, they run: python diagnose.py
echo.
echo   Note: Tesseract OCR must be installed separately
echo         if Site Visit form OCR is needed.
echo.
pause
