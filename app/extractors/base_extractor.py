"""Abstract base extractor with template method pattern.

All extractors return Dict[str, ExtractionResult] — never raise
from extraction, never return None directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.domain.enums import FieldConfidence
from app.domain.models import ExtractionResult
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for all document extractors.

    Template method pattern:
        extract() → _validate_file() → _do_extract() → _post_process()
    """

    def extract(self, file_path: Path | str) -> dict[str, ExtractionResult]:
        """Run the full extraction pipeline.

        Returns:
            Dict mapping field names to ExtractionResult instances.
            Never raises — wraps all errors in LOW-confidence results.
        """
        try:
            file_path = Path(file_path)
            self._validate_file(file_path)
            raw = self._do_extract(file_path)
            return self._post_process(raw)
        except FileNotFoundError:
            logger.error("File not found: %s", file_path)
            return self._error_result(f"File not found: {file_path.name}")
        except PermissionError:
            logger.error("Permission denied: %s", file_path)
            return self._error_result(f"Cannot read file: {file_path.name}")
        except Exception as e:
            logger.exception("Extraction failed for %s: %s", file_path, e)
            return self._error_result(f"Extraction failed: {e}")

    def _validate_file(self, file_path: Path) -> None:
        """Validate file exists and is readable. Override for type checks."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise FileNotFoundError(f"Not a file: {file_path}")

    @abstractmethod
    def _do_extract(self, file_path: Path) -> dict[str, ExtractionResult]:
        """Perform the actual extraction. Subclasses implement this."""
        ...

    def _post_process(self, results: dict[str, ExtractionResult]) -> dict[str, ExtractionResult]:
        """Optional post-processing hook. Override if needed."""
        return results

    @staticmethod
    def _make_result(
        value: Any,
        confidence: FieldConfidence = FieldConfidence.HIGH,
        source: str = "regex_match",
        message: str | None = None,
    ) -> ExtractionResult:
        """Helper to create a successful ExtractionResult."""
        return ExtractionResult(
            value=value, confidence=confidence, source=source, message=message
        )

    @staticmethod
    def _not_found(field_name: str, message: str | None = None) -> ExtractionResult:
        """Helper to create a not-found ExtractionResult."""
        return ExtractionResult(
            value=None,
            confidence=FieldConfidence.LOW,
            source="not_found",
            message=message or f"{field_name} could not be extracted",
        )

    @staticmethod
    def _error_result(message: str) -> dict[str, ExtractionResult]:
        """Return a dict with just an error entry."""
        return {
            "_error": ExtractionResult(
                value=None,
                confidence=FieldConfidence.LOW,
                source="error",
                message=message,
            )
        }