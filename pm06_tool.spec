# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for TPDDL PM06 Executive Summary Generator.

Build commands:
  One-folder (faster startup, recommended):
    pyinstaller pm06_tool.spec

  Then distribute the entire 'dist/PM06_Tool/' folder.
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle config JSON files
        ("config/zone_district_map.json", "config"),
        ("config/wbs_map.json", "config"),
        ("config/work_types.json", "config"),
        # Bundle the diagnostic script
        ("diagnose.py", "."),
    ],
    hiddenimports=[
        # PDF processing
        "pdfplumber",
        "pdfplumber.table",
        "pdfplumber.ctm",
        "pdfplumber.utils",
        "fitz",
        # Image / OCR
        "PIL",
        "PIL.Image",
        "PIL.ImageEnhance",
        "PIL.ImageFilter",
        "PIL.ImageOps",
        "numpy",
        "pytesseract",
        # Document generation
        "docx",
        "docx.opc",
        "docx.opc.constants",
        "docx.opc.package",
        "docx.opc.part",
        "docx.opc.rel",
        "docx.opc.pkgreader",
        "docx.opc.pkgwriter",
        "docx.oxml",
        "docx.oxml.ns",
        # Excel
        "openpyxl",
        "openpyxl.styles",
        "openpyxl.utils",
        # UI
        "ttkbootstrap",
        "ttkbootstrap.constants",
        "ttkbootstrap.themes",
        "ttkbootstrap.style",
        "ttkbootstrap.widgets",
        "ttkbootstrap.dialogs",
        "tkinterdnd2",
        # Infrastructure
        "filelock",
        # Standard library (sometimes missed)
        "sqlite3",
        "configparser",
        "json",
        "decimal",
        "threading",
        "hashlib",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not used — remove to shrink bundle
        "pydantic",
        "dateutil",
        "python_dateutil",
        # Dev/test tools
        "pytest",
        "pytest_mock",
        "_pytest",
        # Unnecessary for desktop app
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "notebook",
        "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PM06_Tool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window — Tkinter GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PM06_Tool",
)
