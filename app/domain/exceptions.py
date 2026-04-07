"""Custom exception classes for the TPDDL PM06 tool.

Every exception carries a user-friendly message suitable for display
in a dialog box to non-technical TPDDL staff.
"""


class TPDDLBaseError(Exception):
    """Base exception for all TPDDL PM06 tool errors."""

    def __init__(self, message: str, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message: str = user_message or message


class ExtractionError(TPDDLBaseError):
    """Raised when a data extraction step fails irrecoverably.

    Examples: PDF cannot be opened, required sheet missing from Excel.
    """


class ValidationError(TPDDLBaseError):
    """Raised when validation of extracted data fails a blocking check."""


class TrackerWriteError(TPDDLBaseError):
    """Raised when writing to the tracker Excel or DB fails.

    Common cause: Excel file open by another program (PermissionError).
    """


class DBCorruptionError(TPDDLBaseError):
    """Raised when SQLite integrity_check fails on startup."""


class ConfigError(TPDDLBaseError):
    """Raised when config.ini or JSON config files are invalid or missing."""


class FileTypeError(TPDDLBaseError):
    """Raised when a file does not match its expected type (magic bytes)."""


class OCRError(TPDDLBaseError):
    """Raised when OCR processing fails (Tesseract error, low quality, etc.)."""
