# TPDDL PM06 Executive Summary Generator & Tracker

## What This Is
A desktop application (Python + Tkinter) used by TPDDL (Tata Power Delhi Distribution Limited) engineers to auto-generate Executive Summary documents from PM06 intake files. It extracts data from PDFs and Excel files, validates it, generates a Word document, and tracks cases in an Excel tracker.

## Architecture (Layered, No Circular Dependencies)

```
UI (Tkinter/ttkbootstrap) → Services → Domain + Infrastructure → Data (SQLite + Excel)
```

### Key Layers
- **`app/domain/`** — Models (`Case`, `ExtractionResult`, `Material`, `TrackerRow`), Enums (`WorkType`, `CaseStatus`), Constants (compiled regex), Exceptions
- **`app/extractors/`** — Template Method pattern. `BaseExtractor.extract()` → `_do_extract()`. Three concrete: `SchemePDFExtractor` (PDF text/tables), `PM06ExcelExtractor` (label-value map from Excel), `SiteVisitExtractor` (OCR, optional). Factory: `ExtractorFactory`
- **`app/services/`** — `GeneratorService` (orchestrates extract→merge→validate→build→persist pipeline), `ValidatorService` (17 checks: 8 blocking + 6 warning + 3 cross-field), `TrackerService` (case lifecycle), `ExportService` (Excel export + MIS)
- **`app/builders/`** — `DocxBuilder` (13-section Word doc), `CostTableExtractor` (PDF→PNG), `WorkTypeDetector` (material keyword classification). Strategy pattern: `renderers/` with 4 renderers per work type
- **`app/data/`** — `Database` (SQLite with WAL mode, migrations), `CaseRepository` (parameterised SQL, CRUD + MIS aggregation), `ExcelRepository` (file-locked atomic Excel writes)
- **`app/infrastructure/`** — `ConfigManager` (thread-safe singleton), logging (rotating), backup, recovery, formatting, text/file utilities
- **`app/ui/`** — 6 tabs (Generate, Review, Tracker, MIS, Settings, Help), drag-drop, dialogs

### Data Flow
```
Scheme PDF + PM06 Excel + Site Visit PDF (optional)
  → Extract (regex + tables + OCR)
  → Merge (3-source priority: scheme > pm06 > site_visit)
  → Enrich (zone/WBS lookup, DT fields, CAPEX year)
  → Validate (17 checks)
  → Build DOCX (renderer per work type)
  → Persist (SQLite cases + audit_log + tracker Excel sync)
```

### Database Tables
`cases` (30 columns), `source_files`, `generated_docs`, `audit_log`, `db_metadata`

## Key Patterns
- **Factory**: `ExtractorFactory`, `get_renderer()`
- **Strategy**: 4 renderers (LT Standard, LT HT Pole, DT Augmentation, ABC Wiring)
- **Template Method**: `BaseExtractor.extract()` → `_do_extract()`
- **Repository**: `CaseRepository`, `ExcelRepository`
- **Singleton**: `ConfigManager`
- **DTO**: `ExtractionResult[T]` wraps all extracted values

## Commands
- **Run app**: `python run.py`
- **Run tests**: `.\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short`
- **Diagnose issues**: `python diagnose.py`
- **Install**: `install.bat` (creates venv, installs deps)

## Conventions
- All SQL is parameterised (`?` placeholders) — never use f-strings in queries
- Extractors NEVER raise exceptions — wrap failures in `ExtractionResult(value=None, confidence=LOW)`
- File writes are atomic (temp file → `os.replace`)
- All regex patterns are compiled in `app/domain/constants.py`
- Type annotations on all functions (95%+ coverage)
- 613 passing tests in `tests/`

## Dependencies
pdfplumber, PyMuPDF, pytesseract (optional), Pillow, numpy, python-docx, openpyxl, ttkbootstrap, filelock

## FY Context
Current financial year: 2026-27 (April 2026 – March 2027). CAPEX year derived from file path dates.
