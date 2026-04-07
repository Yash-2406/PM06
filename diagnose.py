#!/usr/bin/env python3
"""PM06 Tool — Diagnostic Script.

Run this when the app won't start or behaves unexpectedly.
It checks Python, dependencies, config, DB, and Tesseract.

Usage:
    python diagnose.py
"""

import importlib
import os
import shutil
import sqlite3
import sys
from pathlib import Path

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

errors: list[str] = []
warnings: list[str] = []


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}[WARN]{RESET} {msg}")
    warnings.append(msg)


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")
    errors.append(msg)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def check_python() -> None:
    section("1. Python Environment")
    v = sys.version_info
    print(f"  Python {v.major}.{v.minor}.{v.micro} ({sys.executable})")
    if v >= (3, 9):
        ok(f"Python {v.major}.{v.minor} meets requirement (3.9+)")
    else:
        fail(f"Python {v.major}.{v.minor} is too old — need 3.9+")

    if sys.maxsize > 2**32:
        ok("64-bit Python")
    else:
        warn("32-bit Python — some libraries may not work")

    # Check venv
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if in_venv:
        ok("Running inside virtual environment")
    else:
        warn("Not in a virtual environment — run 'install.bat' first")


def check_dependencies() -> None:
    section("2. Dependencies")
    required = {
        "pdfplumber": "pdfplumber",
        "fitz": "PyMuPDF",
        "pytesseract": "pytesseract",
        "PIL": "Pillow",
        "numpy": "numpy",
        "docx": "python-docx",
        "openpyxl": "openpyxl",
        "ttkbootstrap": "ttkbootstrap",
        "filelock": "filelock",
    }
    optional = {
        "tkinterdnd2": "tkinterdnd2 (drag-drop support)",
    }

    for module, name in required.items():
        try:
            mod = importlib.import_module(module)
            version = getattr(mod, "__version__", "?")
            ok(f"{name} ({version})")
        except ImportError:
            fail(f"{name} — NOT INSTALLED.  Fix: pip install {name}")

    for module, name in optional.items():
        try:
            importlib.import_module(module)
            ok(f"{name}")
        except ImportError:
            warn(f"{name} — not installed (optional)")

    # Tkinter
    try:
        import tkinter
        ok(f"tkinter ({tkinter.TkVersion})")
    except ImportError:
        fail("tkinter NOT available — reinstall Python with tcl/tk")


def check_tesseract() -> None:
    section("3. Tesseract OCR (optional)")
    tess = shutil.which("tesseract")
    if tess:
        ok(f"Tesseract found: {tess}")
        try:
            import subprocess
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            ok(f"Version: {version_line}")
        except Exception as e:
            warn(f"Could not get Tesseract version: {e}")
    else:
        warn(
            "Tesseract not found on PATH — OCR (Site Visit form) will not work.\n"
            "         Install from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "         Then add to PATH or set TESSERACT_CMD in config."
        )


def check_config() -> None:
    section("4. Configuration")
    root = Path(__file__).parent
    config_ini = root / "config.ini"
    if config_ini.exists():
        ok(f"config.ini found ({config_ini.stat().st_size} bytes)")
    else:
        warn("config.ini not found — will be created on first run")

    json_files = ["zone_district_map.json", "wbs_map.json", "work_types.json"]
    config_dir = root / "config"
    for f in json_files:
        path = config_dir / f
        if path.exists():
            ok(f"config/{f} ({path.stat().st_size} bytes)")
        else:
            warn(f"config/{f} missing — some features may not work")


def check_database() -> None:
    section("5. Database")
    root = Path(__file__).parent

    # Find DB path from config.ini or default
    db_path = root / "tpddl_mpg.db"
    if not db_path.exists():
        # Try common locations
        for candidate in [root / "data" / "tpddl_mpg.db", root / "output" / "tpddl_mpg.db"]:
            if candidate.exists():
                db_path = candidate
                break

    if db_path.exists():
        ok(f"Database found: {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            if result == "ok":
                ok("Database integrity: OK")
            else:
                fail(f"Database integrity FAILED: {result}")

            # Count cases
            try:
                count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
                ok(f"Cases in database: {count}")
            except Exception:
                warn("Could not read cases table")
            conn.close()
        except Exception as e:
            fail(f"Cannot open database: {e}")
    else:
        warn("No database file found — will be created on first run")


def check_directories() -> None:
    section("6. Directories")
    root = Path(__file__).parent
    dirs = {
        "output": "Generated documents",
        "logs": "Log files",
        "backups": "Database backups",
        "recovery": "Crash recovery state",
        "config": "Configuration files",
    }
    for dirname, purpose in dirs.items():
        path = root / dirname
        if path.exists():
            file_count = sum(1 for _ in path.rglob("*") if _.is_file())
            ok(f"{dirname}/ — {purpose} ({file_count} files)")
        else:
            warn(f"{dirname}/ missing — will be created on first run")


def check_permissions() -> None:
    section("7. File Permissions")
    root = Path(__file__).parent
    # Test write permission
    test_file = root / ".write_test"
    try:
        test_file.write_text("test")
        test_file.unlink()
        ok("Write permission to app directory: OK")
    except PermissionError:
        fail(
            "Cannot write to app directory!\n"
            "         Fix: Right-click folder → Properties → Security → Full Control"
        )


def summary() -> None:
    section("SUMMARY")
    if not errors and not warnings:
        print(f"\n  {GREEN}All checks passed! The app should work correctly.{RESET}")
    elif errors:
        print(f"\n  {RED}{len(errors)} error(s) found — app may not start:{RESET}")
        for e in errors:
            print(f"    • {e}")
        if warnings:
            print(f"\n  {YELLOW}{len(warnings)} warning(s):{RESET}")
            for w in warnings:
                print(f"    • {w}")
    else:
        print(f"\n  {YELLOW}{len(warnings)} warning(s) — app should work but some features may be limited:{RESET}")
        for w in warnings:
            print(f"    • {w}")
    print()


if __name__ == "__main__":
    print()
    print("  PM06 Tool — System Diagnostic")
    print("  " + "─" * 40)

    check_python()
    check_dependencies()
    check_tesseract()
    check_config()
    check_database()
    check_directories()
    check_permissions()
    summary()

    input("Press Enter to close...")
