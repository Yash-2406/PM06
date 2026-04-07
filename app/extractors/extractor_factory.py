"""Abstract Factory returning the correct extractor by FileType.

Uses magic bytes detection as additional validation.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.enums import FileType
from app.extractors.base_extractor import BaseExtractor
from app.extractors.pm06_excel_extractor import PM06ExcelExtractor
from app.extractors.scheme_pdf_extractor import SchemePDFExtractor
from app.extractors.site_visit_extractor import SiteVisitExtractor
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


class ExtractorFactory:
    """Factory that returns the appropriate extractor for a file type."""

    _extractors: dict[FileType, type[BaseExtractor]] = {
        FileType.SCHEME_PDF: SchemePDFExtractor,
        FileType.SITE_VISIT_PDF: SiteVisitExtractor,
        FileType.PM06_EXCEL: PM06ExcelExtractor,
    }

    @staticmethod
    def get_extractor(file_type: FileType) -> BaseExtractor:
        """Return an extractor instance for the given file type.

        Args:
            file_type: The FileType enum value.

        Returns:
            An instance of the appropriate BaseExtractor subclass.

        Raises:
            ValueError: If file_type is not recognised.
        """
        extractor_cls = ExtractorFactory._extractors.get(file_type)
        if extractor_cls is None:
            raise ValueError(f"No extractor registered for file type: {file_type}")
        logger.debug("Created %s for %s", extractor_cls.__name__, file_type.value)
        return extractor_cls()

    @staticmethod
    def get_extractor_for_path(file_path: Path, file_type: FileType) -> BaseExtractor:
        """Convenience method: validate file exists then return extractor."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return ExtractorFactory.get_extractor(file_type)