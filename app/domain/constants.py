"""Constants used across the TPDDL PM06 tool.

All repeated string literals, column names, numeric thresholds, and
compiled regex patterns live here. Never hardcode these inline.
"""

import re

# ---------------------------------------------------------------------------
# Fallback mappings (authoritative source is config/*.json loaded by ConfigManager)
# ---------------------------------------------------------------------------

ZONE_DISTRICT_MAP: dict[str, list[int]] = {
    "CVL": [411, 418, 416, 424, 417, 421, 423],
    "MDT": [402, 415, 412, 413, 505],
    "MTN": [1301, 1302, 1303, 1304],
    "KPM": [422, 501, 520, 425, 502, 509],
    "BDL": [507, 516, 572],
    "BWN": [512, 521, 533],
    "MGP": [519, 515, 518],
    "NRL": [511, 514, 517, 522],
    "PPR": [504, 510, 508, 530],
    "RHN": [551, 561, 571, 581],
    "KRR": [523, 513],
    "SMB": [414, 503, 506, 531, 532],
}

WBS_MAP: dict[str, dict] = {
    "CE/N0000/00133": {"description": "City Circle New Connection 2026-27", "districts": ["MTN"]},
    "CE/N0000/00134": {"description": "Town Circle New Connection 2026-27", "districts": ["CVL", "MDT", "KPM"]},
    "CE/N0000/00135": {"description": "Metro Circle New Connection 2026-27", "districts": ["PPR", "MGP", "KRR"]},
    "CE/N0000/00136": {"description": "Urban Circle New Connection 2026-27", "districts": ["BDL", "SMB", "RHN"]},
    "CE/N0000/00137": {"description": "Sub Urban New Connection 2026-27", "districts": ["NRL", "BWN"]},
}

# ---------------------------------------------------------------------------
# Compiled regex patterns — ALWAYS defined at MODULE LEVEL, never in functions
# ---------------------------------------------------------------------------

# SC-1: Strip SAP page headers before ANY parsing
RE_PAGE_HEADER: re.Pattern[str] = re.compile(
    r"Page\s*No\.?\s*:\s*\d+\s*Order\s*No\.?\s*:\s*\d+", re.IGNORECASE
)
RE_LOGO_TEXT: re.Pattern[str] = re.compile(r"TATA\s*POWER[-\s]*DDL", re.IGNORECASE)

# SC-2: Order No — 8 numeric digits
RE_ORDER_NO: re.Pattern[str] = re.compile(r"\b(\d{8})\b")
RE_ORDER_NO_LABELLED: re.Pattern[str] = re.compile(
    r"Order\s*No\.?\s*:?\s*(\d{8})", re.IGNORECASE
)

# SC-3: Notification No — multi-applicant support
RE_NC_NOTIF: re.Pattern[str] = re.compile(r"N[/]?C\s*(\d{10})", re.IGNORECASE)
RE_SLASH_NOTIF: re.Pattern[str] = re.compile(r"/\s*(\d{10})")

# SC-4: Applicant name
RE_NAME_INLINE: re.Pattern[str] = re.compile(
    r"N[/]?C\s*\d{10}\s+"
    r"((?:Ms\.|Mr\.|Mrs\.|DR\.|SHRI|SMT|W/O|S/O|D/O)?\s*"
    r"[A-Z][A-Z\s/\.\-]+?)"
    r"(?:\n|Unelectrified|Electrified|\d{6}|Mobile|Email)",
    re.IGNORECASE,
)

# SC-5: Delhi PIN code — 6 digits starting with 10 or 11
RE_DELHI_PIN: re.Pattern[str] = re.compile(r"\b(1[01]\d{4})\b")

# SC-6: Cost values — handle SAP "Chargess" typo
RE_BOM_TOTAL: re.Pattern[str] = re.compile(r"Bill\s+of\s+[Mm]aterial\s+([\d,]+\.\d{2})")
RE_BOS_TOTAL: re.Pattern[str] = re.compile(r"Bill\s+of\s+[Ss]ervices?\s+([\d,]+\.\d{2})")
RE_EIF_TOTAL: re.Pattern[str] = re.compile(r"Electrical\s+Inspection\s+Fees?\s+([\d,]+\.\d{2})")
RE_RRC_TOTAL: re.Pattern[str] = re.compile(r"Road\s+Restoration\s+Charges{1,2}\s+([\d,]+\.\d{2})")
RE_GRAND_TOT: re.Pattern[str] = re.compile(r"Total\s*\(Rs\.\)\s*([\d,]+\.\d{2})")

# SC-7: BOM row — 9-digit SAP material code anchor
RE_BOM_ROW: re.Pattern[str] = re.compile(
    r"^(\d{1,3})\s+(\d{9})\s+(.+?)\s+"
    r"(EA|M|KG|ST|SET|NOS?)\s+"
    r"([\d,]+\.\d{2})\s+([\d,]+\.\d{3})\s+([\d,]+\.\d{2})",
    re.IGNORECASE | re.MULTILINE,
)

# DT capacity normalisation
RE_DT_CAPACITY_NUM: re.Pattern[str] = re.compile(r"(\d+(?:\.\d+)?)")

# Address terminators
ADDRESS_TERMINATORS: list[str] = [
    "Mobile", "Email", "Nature of Scheme", "Unelectrified", "Electrified",
]

# ---------------------------------------------------------------------------
# Tracker column names — must match New_Connection_FY26.xlsx exactly
# ---------------------------------------------------------------------------

TRACKER_COLUMNS: list[str] = [
    "Sl. No.",
    "Scheme no.",
    "N No.",
    "District",
    "Zone",
    "Date of Receiving",
    "Date of processing",
    "Status",
    "Remarks",
    "Amount in Rs.",
    "Correction suggested to zone?",
    "Correction details",
]

# ---------------------------------------------------------------------------
# Numeric thresholds
# ---------------------------------------------------------------------------

COST_MISMATCH_TOLERANCE_RS: float = 5.0
MIN_ESTIMATED_COST_RS: float = 1000.0
OCR_CONFIDENCE_THRESHOLD: float = 40.0
MAX_MAJOR_MATERIALS: int = 3
LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
LOG_RETENTION_DAYS: int = 30
COST_TABLE_IMAGE_DPI: int = 200
COST_TABLE_IMAGE_WIDTH_INCHES: float = 6.875
COST_LOWER_BOUND: float = 500.0       # Minimum realistic cost in Rs
COST_UPPER_BOUND: float = 50_000_000.0  # 5 crore upper bound

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

VALID_CATEGORIES: set[str] = {"DOMESTIC", "COMMERCIAL", "INDUSTRIAL", "AGRICULTURAL", "OTHERS"}

# ---------------------------------------------------------------------------
# String literals used in multiple places
# ---------------------------------------------------------------------------

APP_TITLE: str = "TPDDL PM06 Executive Summary Generator and Tracker"
DB_FILENAME: str = "tpddl_mpg.db"
TRACKER_FILENAME: str = "New_Connection_FY26.xlsx"

def get_tracker_filename() -> str:
    """Return tracker filename for the current financial year.

    E.g. in FY 2026-27 (Apr 2026 onward) → 'New_Connection_FY27.xlsx'.
    """
    from app.infrastructure.formatting import get_capex_year
    fy = get_capex_year()          # e.g. "2025-26" or "2026-27"
    suffix = fy.split("-")[1]      # "26" or "27"
    return f"New_Connection_FY{suffix}.xlsx"
DEFAULT_OUTPUT_DIR: str = "output"
RECOVERY_DIR: str = "recovery"
LOGS_DIR: str = "logs"
BACKUP_DIR: str = "backups"
CONFIG_FILENAME: str = "config.ini"

MAIN_SCHEME_CATEGORY: str = "Load Growth Schemes"
BUDGET_HEAD: str = "TPDDL-NC"
DEFAULT_STATUS: str = "Approved"
DEFAULT_REMARKS: str = "Scheme documents uploaded"

# File magic bytes for validation
PDF_MAGIC: bytes = b"%PDF"
XLSX_MAGIC: bytes = b"PK\x03\x04"

# PM06 Excel target sheet
PM06_SHEET_NAME: str = "Format"

# Scope-of-work engineering keywords for fallback detection
SCOPE_KEYWORDS: list[str] = [
    "extension", "from pole", "towards", "connection", "laying",
]

# Work-type BOM detection keywords
WT_TRANSFORMER_KW: list[str] = ["TRANSFORMER"]
WT_DT_AUG_NATURE_KW: list[str] = ["AUGMENTATION", "HT SCHEME"]
WT_ABC_KW: list[str] = ["ABC CABLE", "ABC WIRING", "AERIAL BUNCHED", "4X150", "4*150"]
WT_LT_HT_KW: list[str] = ["2X25", "2CX25", "2 X 25"]

# Major material selection keywords
MATERIAL_CABLE_KW: list[str] = ["CABLE", "ABC"]
MATERIAL_POLE_KW: list[str] = ["POLE"]
MATERIAL_DB_ACB_KW: list[str] = ["DIST.BOX", "DISTRIBUTION BOX", "ACB"]
MATERIAL_TRANSFORMER_KW: list[str] = ["TRANSFORMER"]