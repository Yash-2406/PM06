#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  TPDDL PM06 Executive Summary Generator — Linux/macOS Installer
# ═══════════════════════════════════════════════════════════════

set -e

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  TPDDL PM06 Tool Installer"
echo "══════════════════════════════════════════════════════════════"
echo ""

# 1. Check Python 3.9+
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "Please install Python 3.9+ from https://python.org"
    exit 1
fi

PY_VER=$(python3 --version 2>&1)
echo "[OK] $PY_VER found."

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "[OK] Virtual environment activated."

# 3. Upgrade pip
python -m pip install --upgrade pip --quiet

# 4. Install dependencies
echo "[INFO] Installing dependencies..."
pip install -r requirements.txt --quiet
echo "[OK] All dependencies installed."

# 5. Check Tesseract OCR
if ! command -v tesseract &> /dev/null; then
    echo ""
    echo "[WARNING] Tesseract OCR not found."
    echo "Install with: sudo apt install tesseract-ocr (Ubuntu/Debian)"
    echo "or: brew install tesseract (macOS)"
    echo ""
else
    echo "[OK] Tesseract OCR found."
fi

# 6. Create required directories
mkdir -p output logs backups recovery
echo "[OK] Directories created."

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  Installation complete!"
echo "  Run the tool with: python run.py"
echo "══════════════════════════════════════════════════════════════"
echo ""