"""Scheme Copy PDF extractor — rules SC-1 through SC-7.

Uses pdfplumber for text/table extraction, PyMuPDF for rendering.
All regex patterns imported from constants (compiled at module level).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import pdfplumber

from app.domain.constants import (
    RE_BOM_ROW,
    RE_BOM_TOTAL,
    RE_BOS_TOTAL,
    RE_DELHI_PIN,
    RE_EIF_TOTAL,
    RE_GRAND_TOT,
    RE_NAME_INLINE,
    RE_NC_NOTIF,
    RE_ORDER_NO_LABELLED,
    RE_RRC_TOTAL,
    RE_SLASH_NOTIF,
    ADDRESS_TERMINATORS,
)
from app.domain.enums import FieldConfidence
from app.domain.models import ExtractionResult, Material
from app.extractors.base_extractor import BaseExtractor
from app.infrastructure.file_utils import validate_file_type
from app.domain.enums import FileType
from app.infrastructure.logger import get_logger
from app.infrastructure.text_utils import strip_pdf_headers

logger = get_logger(__name__)


class SchemePDFExtractor(BaseExtractor):
    """Extract data from the SAP-generated Scheme Copy PDF.

    MANDATORY document. Extracts Order No, Notification Nos,
    applicant info, cost values, and BOM materials.
    """

    def _validate_file(self, file_path: Path) -> None:
        super()._validate_file(file_path)
        validate_file_type(file_path, FileType.SCHEME_PDF)

    def _do_extract(self, file_path: Path) -> dict[str, ExtractionResult]:
        """Extract all fields from the Scheme Copy PDF."""
        results: dict[str, ExtractionResult] = {}

        # Read and strip headers (SC-1)
        full_text = self._read_pdf_text(file_path)
        if not full_text:
            return self._error_result("Could not extract text from Scheme Copy PDF")

        cleaned = strip_pdf_headers(full_text)

        # SC-2: Order No
        results["order_no"] = self._extract_order_no(full_text, cleaned)

        # SC-3: Notification Nos (multi-applicant)
        notif_nos = self._extract_notification_nos(cleaned)
        results["notification_nos"] = self._make_result(
            notif_nos, source="regex_match"
        ) if notif_nos else self._not_found("Notification No.")
        results["notification_no"] = self._make_result(
            notif_nos[0], source="regex_match"
        ) if notif_nos else self._not_found("Primary Notification No.")

        # SC-4: Applicant Name
        results["applicant_name"] = self._extract_name(cleaned)

        # SC-5: Address and PIN
        results["address"] = self._extract_address(cleaned)
        results["pin_code"] = self._extract_pin(cleaned)

        # SC-6: Cost values
        cost_results = self._extract_costs(cleaned)
        results.update(cost_results)

        # SC-7: BOM materials
        materials = self._extract_bom_materials(file_path, cleaned)
        results["materials"] = self._make_result(materials, source="table_extraction")

        # Nature of scheme
        results["nature_of_scheme"] = self._extract_nature(cleaned)

        return results

    # ------------------------------------------------------------------
    # PDF text reading
    # ------------------------------------------------------------------

    @staticmethod
    def _read_pdf_text(file_path: Path) -> str:
        """Read all text from PDF using pdfplumber, handling password."""
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)
                return "\n".join(pages_text)
        except Exception as e:
            # Try with empty password for encrypted PDFs
            try:
                with pdfplumber.open(str(file_path), password="") as pdf:
                    pages_text = []
                    for page in pdf.pages:
                        text = page.extract_text() or ""
                        pages_text.append(text)
                    return "\n".join(pages_text)
            except Exception:
                logger.error("Cannot read PDF %s: %s", file_path, e)
                return ""

    # ------------------------------------------------------------------
    # Field extraction methods
    # ------------------------------------------------------------------

    def _extract_order_no(self, raw_text: str, cleaned_text: str) -> ExtractionResult:
        """SC-2: Extract Order No from page header first, then body."""
        # Best source: page header (most reliable)
        match = RE_ORDER_NO_LABELLED.search(raw_text)
        if match:
            return self._make_result(match.group(1), source="page_header")

        # Fallback: search cleaned text
        match = RE_ORDER_NO_LABELLED.search(cleaned_text)
        if match:
            return self._make_result(match.group(1), source="body_text")

        return self._not_found("Order No.", "Could not find 8-digit Order Number")

    @staticmethod
    def _extract_notification_nos(text: str) -> list[str]:
        """SC-3: Extract all Notification Numbers (multi-applicant support)."""
        primary = RE_NC_NOTIF.findall(text)
        secondary = RE_SLASH_NOTIF.findall(text)
        all_nos = list(dict.fromkeys(primary + secondary))
        return all_nos

    def _extract_name(self, text: str) -> ExtractionResult:
        """SC-4: Extract applicant name."""
        match = RE_NAME_INLINE.search(text)
        if match:
            name = match.group(1).strip()
            if len(name) > 2:
                return self._make_result(name, source="regex_match")

        # Fallback: look for name after N/C number line
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if RE_NC_NOTIF.search(line):
                # Name might be on same line after the number
                after_nc = RE_NC_NOTIF.sub("", line).strip()
                if after_nc and len(after_nc) > 2:
                    name = after_nc.split("  ")[0].strip()
                    if name:
                        return self._make_result(name, FieldConfidence.MEDIUM, "line_after_nc")
                # Or on the next line
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line[0].isdigit():
                        return self._make_result(next_line, FieldConfidence.MEDIUM, "next_line")

        return self._not_found("Applicant Name", "Name not found — please enter manually")

    def _extract_address(self, text: str) -> ExtractionResult:
        """SC-5: Extract address block."""
        # Find text after name, before terminators
        lines = text.split("\n")
        address_lines: list[str] = []
        in_address = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Start collecting after N/C line
            nc_match = RE_NC_NOTIF.search(stripped)
            if nc_match:
                in_address = True
                # Also capture text AFTER the notification number on the same line
                after_nc = stripped[nc_match.end():].strip()
                if after_nc and len(after_nc) > 2:
                    address_lines.append(after_nc)
                continue

            if in_address:
                # Stop at terminators
                if any(term.lower() in stripped.lower() for term in ADDRESS_TERMINATORS):
                    break
                # Stop at PIN code (but include the line with it)
                if RE_DELHI_PIN.search(stripped):
                    address_lines.append(stripped)
                    break
                address_lines.append(stripped)
                if len(address_lines) > 5:
                    break

        if address_lines:
            full_addr = ", ".join(address_lines)
            return self._make_result(full_addr, source="text_block")

        return self._not_found("Address")

    def _extract_pin(self, text: str) -> ExtractionResult:
        """SC-5: Extract Delhi PIN code."""
        match = RE_DELHI_PIN.search(text)
        if match:
            return self._make_result(match.group(1), source="regex_match")
        return ExtractionResult(
            value=None, confidence=FieldConfidence.MEDIUM,
            source="not_found", message="No Delhi PIN code found (non-blocking)"
        )

    def _extract_costs(self, text: str) -> dict[str, ExtractionResult]:
        """SC-6: Extract cost values from the summary table."""
        results: dict[str, ExtractionResult] = {}

        for field_name, pattern in [
            ("bom_total", RE_BOM_TOTAL),
            ("bos_total", RE_BOS_TOTAL),
            ("eif_total", RE_EIF_TOTAL),
            ("rrc_total", RE_RRC_TOTAL),
            ("grand_total", RE_GRAND_TOT),
        ]:
            match = pattern.search(text)
            if match:
                try:
                    val = Decimal(match.group(1).replace(",", ""))
                    results[field_name] = self._make_result(val, source="cost_table_regex")
                except InvalidOperation:
                    results[field_name] = self._not_found(field_name, f"Invalid number: {match.group(1)}")
            else:
                results[field_name] = self._not_found(field_name)

        return results

    def _extract_nature(self, text: str) -> ExtractionResult:
        """Extract Nature of Scheme text."""
        import re
        pattern = re.compile(r"Nature\s+of\s+Scheme\s*:?\s*(.+?)(?:\n|$)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return self._make_result(match.group(1).strip(), source="regex_match")
        return self._not_found("Nature of Scheme")

    # ------------------------------------------------------------------
    # BOM materials
    # ------------------------------------------------------------------

    def _extract_bom_materials(self, file_path: Path, cleaned_text: str) -> list[Material]:
        """SC-7: Extract BOM materials using table extraction then regex fallback."""
        materials = self._extract_bom_from_tables(file_path)
        if not materials:
            materials = self._extract_bom_from_regex(cleaned_text)
        return materials

    @staticmethod
    def _extract_bom_from_tables(file_path: Path) -> list[Material]:
        """Try to extract BOM via pdfplumber table extraction."""
        materials: list[Material] = []
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                in_bom = False
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    found_part1 = "Part-1 Estimate of Work" in text or "Part-1" in text
                    found_part2 = "Part-2 Estimate of Work" in text or "Part-2" in text
                    if found_part1:
                        in_bom = True
                    # Process tables on this page before turning off in_bom
                    # (Part-1 and Part-2 may appear on the same page)
                    if in_bom:
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                if not row or len(row) < 7:
                                    continue
                                mat = SchemePDFExtractor._parse_bom_row(row)
                                if mat:
                                    materials.append(mat)
                    if found_part2:
                        in_bom = False
        except Exception as e:
            logger.warning("Table extraction failed, will try regex: %s", e)
        return materials

    @staticmethod
    def _extract_bom_from_regex(text: str) -> list[Material]:
        """Fallback: extract BOM rows using regex on text."""
        materials: list[Material] = []
        for match in RE_BOM_ROW.finditer(text):
            try:
                mat = Material(
                    sr_no=int(match.group(1)),
                    code=match.group(2),
                    description=match.group(3).strip(),
                    unit=match.group(4).upper(),
                    unit_rate=Decimal(match.group(5).replace(",", "")),
                    quantity=Decimal(match.group(6).replace(",", "")),
                    amount=Decimal(match.group(7).replace(",", "")),
                )
                materials.append(mat)
            except (ValueError, InvalidOperation) as e:
                logger.debug("Skipping BOM row: %s", e)
        return materials

    @staticmethod
    def _parse_bom_row(row: list) -> Optional[Material]:
        """Parse a single BOM table row into a Material."""
        try:
            cells = [str(c).strip() if c else "" for c in row]
            # Look for 9-digit SAP code
            code_idx = None
            for i, cell in enumerate(cells):
                if cell.isdigit() and len(cell) == 9:
                    code_idx = i
                    break
            if code_idx is None:
                return None

            sr_no = int(cells[code_idx - 1]) if code_idx > 0 and cells[code_idx - 1].isdigit() else 0

            def _parse_decimal(s: str) -> Decimal:
                return Decimal(s.replace(",", "")) if s else Decimal("0")

            return Material(
                sr_no=sr_no,
                code=cells[code_idx],
                description=cells[code_idx + 1] if code_idx + 1 < len(cells) else "",
                unit=cells[code_idx + 2] if code_idx + 2 < len(cells) else "",
                unit_rate=_parse_decimal(cells[code_idx + 3]) if code_idx + 3 < len(cells) else Decimal("0"),
                quantity=_parse_decimal(cells[code_idx + 4]) if code_idx + 4 < len(cells) else Decimal("0"),
                amount=_parse_decimal(cells[code_idx + 5]) if code_idx + 5 < len(cells) else Decimal("0"),
            )
        except (ValueError, IndexError, InvalidOperation):
            return None