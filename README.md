# TPDDL PM06 Executive Summary Generator & Tracker

## Overview
The TPDDL PM06 Executive Summary Generator & Tracker is a production-ready Python desktop application designed for Tata Power Delhi Distribution Limited's Maintenance Planning Group (MPG). This tool automates the generation of executive summaries for new electrical connection schemes and integrates with local trackers.

## Features
- **Document Parsing**: Extracts data from Scheme Copy PDFs (pdfplumber + PyMuPDF), scanned Site Visit Forms (Tesseract OCR), and PM06 Format Excel files (openpyxl).
- **Work Type Detection**: Auto-detects LT Standard, LT with HT/PSCC Pole, DT Augmentation, and ABC Wiring from BOM materials.
- **Executive Summary Generation**: Creates formatted Word documents (.docx) with CAPEX title, bullet headers, material tables, cost table images, existing/proposed scenarios.
- **14-Point Validation**: 8 blocking + 6 warning checks per FR-02 specification.
- **Tracker Integration**: Updates local Excel tracker (New_Connection_FY26.xlsx) and SQLite database with full audit trail.
- **MIS Reporting**: Counts by district/status, total amounts.
- **Recovery**: Automatic state save on crash with restore-on-startup prompt.
- **Tkinter GUI**: ttkbootstrap "litera" theme with tabs for Generate, Review, Tracker, MIS, Settings, and Help.
- **Offline Operation**: Fully standalone, no network dependencies.

## Requirements
- Python 3.9 or later
- Tesseract OCR (optional, for site-visit form processing)
- Windows 10/11 (primary target), Linux/macOS supported

## Folder Structure
```
tpddl_mpg_tool/
├── run.py                    # Entry point (Python 3.9+ check)
├── app/
│   ├── main.py               # Bootstrap (logging → config → DB → UI)
│   ├── domain/                # Enums, models, constants, exceptions
│   ├── infrastructure/        # Logger, config, file utils, formatting
│   ├── data/                  # SQLite DB, case repository, Excel repo
│   ├── extractors/            # PDF, OCR, Excel extraction
│   ├── builders/              # DocxBuilder, work-type renderers
│   ├── services/              # Generator, validator, tracker, export
│   └── ui/                    # Tkinter widgets, tabs, main window
├── config/
│   ├── zone_district_map.json # 12 zones → district codes
│   ├── wbs_map.json           # 5 WBS entries
│   └── work_types.json        # Detection signals per work type
├── templates/
│   └── work_types/            # Jinja2 templates (4 work types)
├── tests/                     # pytest test suite
├── requirements.txt
├── install.bat                # Windows installer (venv + shortcut)
└── install.sh                 # Linux/macOS installer
```

## Installation

### Windows (recommended)
```batch
install.bat
```
This creates a virtual environment, installs dependencies, and adds a desktop shortcut.

### Linux / macOS
```bash
chmod +x install.sh
./install.sh
```

### Manual
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Usage
```bash
python run.py
```

### Workflow
1. **Generate Tab** — Drop/browse the Scheme Copy PDF, Site Visit Form, and PM06 Excel
2. **Review Tab** — Verify extracted data (editable fields, confidence icons)
3. **Approve/Reject** — Approve to save to tracker, or reject with correction notes
4. **Tracker Tab** — Search, filter, export cases
5. **MIS Tab** — View summary statistics
6. **Settings Tab** — Configure output folder, zone-district maps, WBS maps

## Dependencies
See `requirements.txt` for the full list. Key libraries:
- pdfplumber, PyMuPDF — PDF text/table/image extraction
- pytesseract, Pillow — OCR for scanned forms
- python-docx — Word document generation
- openpyxl — Excel read/write
- ttkbootstrap — modern Tkinter theming
- filelock — concurrent file access protection
- Jinja2 — text templating

## License
This project is proprietary and intended for internal use by Tata Power-DDL.