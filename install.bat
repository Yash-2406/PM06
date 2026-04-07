@echo off
REM ═══════════════════════════════════════════════════════════════
REM  TPDDL PM06 Executive Summary Generator — Windows Installer
REM ═══════════════════════════════════════════════════════════════

echo.
echo ══════════════════════════════════════════════════════════════
echo   TPDDL PM06 Tool Installer
echo ══════════════════════════════════════════════════════════════
echo.

REM 1. Check Python 3.9+
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not on PATH.
    echo Please install Python 3.9 or higher from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% found.

REM 2. Create virtual environment
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated.

REM 3. Upgrade pip
python -m pip install --upgrade pip --quiet

REM 4. Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] All dependencies installed.

REM 5. Check Tesseract OCR
where tesseract >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [WARNING] Tesseract OCR not found on PATH.
    echo Site-visit form OCR will not work without Tesseract.
    echo Download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo.
) else (
    echo [OK] Tesseract OCR found.
)

REM 6. Create required directories
if not exist "output" mkdir output
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
if not exist "recovery" mkdir recovery
echo [OK] Directories created.

REM 7. Create desktop shortcut
echo [INFO] Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT_PATH=%USERPROFILE%\Desktop\TPDDL PM06 Tool.lnk
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = '%SCRIPT_DIR%venv\Scripts\pythonw.exe'; $sc.Arguments = '%SCRIPT_DIR%run.py'; $sc.WorkingDirectory = '%SCRIPT_DIR%'; $sc.Description = 'TPDDL PM06 Executive Summary Generator'; $sc.Save()" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Desktop shortcut created.
) else (
    echo [INFO] Could not create shortcut automatically.
)

echo.
echo ══════════════════════════════════════════════════════════════
echo   Installation complete!
echo   Run the tool with: python run.py
echo ══════════════════════════════════════════════════════════════
echo.
pause
