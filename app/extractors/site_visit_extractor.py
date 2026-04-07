"""Site Visit Form PDF extractor — rules SVF-1 through SVF-6.

OPTIONAL document. Only extracts Order No. and Notification No.
for cross-validation. Graceful degradation if Tesseract is missing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.domain.constants import OCR_CONFIDENCE_THRESHOLD, RE_NC_NOTIF, RE_ORDER_NO
from app.domain.enums import FieldConfidence
from app.domain.models import ExtractionResult
from app.extractors.base_extractor import BaseExtractor
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)

# SVF-5: Check Tesseract availability at module load
TESSERACT_AVAILABLE: bool = False
try:
    import pytesseract
    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except (ImportError, EnvironmentError, OSError):
    logger.warning("Tesseract not installed — OCR features disabled")


class SiteVisitExtractor(BaseExtractor):
    """Extract Order No. and Notification No. from scanned Site Visit Form.

    OPTIONAL — never blocks if missing, unreadable, or Tesseract unavailable.
    Only extracts two fields for cross-validation purposes.
    """

    def _do_extract(self, file_path: Path) -> dict[str, ExtractionResult]:
        """SVF-2: Extract only Order No. and Notification No."""
        results: dict[str, ExtractionResult] = {}

        if not TESSERACT_AVAILABLE:
            results["order_no"] = ExtractionResult(
                value=None, confidence=FieldConfidence.LOW,
                source="tesseract_missing",
                message="Tesseract OCR not installed — cannot read scanned form",
            )
            results["notification_no"] = ExtractionResult(
                value=None, confidence=FieldConfidence.LOW,
                source="tesseract_missing",
                message="Tesseract OCR not installed — cannot read scanned form",
            )
            return results

        # SVF-6: Process ALL pages, use first valid match
        order_no: Optional[str] = None
        notif_no: Optional[str] = None

        try:
            pages = self._load_pdf_pages(file_path)
        except Exception as e:
            logger.error("Cannot load site visit PDF: %s", e)
            return {
                "order_no": self._not_found("Order No.", f"Cannot read PDF: {e}"),
                "notification_no": self._not_found("Notification No.", f"Cannot read PDF: {e}"),
            }

        for page_idx, page_img in enumerate(pages):
            # SVF-3: Preprocess
            processed = self._preprocess_scan(page_img)

            # SVF-4: Confidence gate
            avg_conf = self._get_ocr_confidence(processed)
            if avg_conf < OCR_CONFIDENCE_THRESHOLD:
                logger.info(
                    "Page %d OCR confidence %.0f%% — below threshold", page_idx + 1, avg_conf
                )
                # Try PSM 11 for degraded scans
                text = self._ocr_text(processed, psm=11)
            else:
                text = self._ocr_text(processed, psm=6)

            # Try top 15% crop for better digit extraction
            if not order_no or not notif_no:
                top_crop = self._crop_top(processed, fraction=0.15)
                top_text = self._ocr_text(top_crop, psm=6, digits_only=True)
                text = top_text + "\n" + text

            # Extract Order No
            if not order_no:
                match = RE_ORDER_NO.search(text)
                if match:
                    order_no = match.group(1)

            # Extract Notification No
            if not notif_no:
                match = RE_NC_NOTIF.search(text)
                if match:
                    notif_no = match.group(1)
                else:
                    # Try bare 10-digit number
                    ten_digit = re.search(r"\b(\d{10})\b", text)
                    if ten_digit:
                        notif_no = ten_digit.group(1)

            if order_no and notif_no:
                break

        conf = FieldConfidence.MEDIUM  # All OCR results are MEDIUM confidence

        results["order_no"] = ExtractionResult(
            value=order_no, confidence=conf if order_no else FieldConfidence.LOW,
            source="ocr" if order_no else "not_found",
            message=None if order_no else "Order No. not readable from scan",
        )
        results["notification_no"] = ExtractionResult(
            value=notif_no, confidence=conf if notif_no else FieldConfidence.LOW,
            source="ocr" if notif_no else "not_found",
            message=None if notif_no else "Notification No. not readable from scan",
        )
        return results

    # ------------------------------------------------------------------
    # PDF page loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_pdf_pages(file_path: Path) -> list[Image.Image]:
        """Load all pages as PIL Images using PyMuPDF."""
        import fitz

        pages: list[Image.Image] = []
        doc = fitz.open(str(file_path))
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            pages.append(img)
        doc.close()
        return pages

    # ------------------------------------------------------------------
    # SVF-3: OCR preprocessing pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess_scan(img: Image.Image) -> Image.Image:
        """Preprocess scanned image for OCR.

        Steps: grayscale → expand borders → deskew → contrast → sharpen → binarize.
        """
        img = img.convert("L")
        img = ImageOps.expand(img, border=20, fill=255)

        # Try rotation correction via OSD
        if TESSERACT_AVAILABLE:
            try:
                osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
                angle = osd.get("rotate", 0)
                conf = osd.get("orientation_conf", 0)
                if conf > 2.0 and angle in (90, 180, 270):
                    img = img.rotate(-angle, expand=True)
            except Exception:
                pass

        img = ImageEnhance.Contrast(img).enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        # Binarize
        arr = np.array(img)
        arr = np.where(arr > arr.mean(), 255, 0).astype(np.uint8)
        return Image.fromarray(arr)

    # ------------------------------------------------------------------
    # SVF-4: OCR confidence gate
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ocr_confidence(img: Image.Image) -> float:
        """Return average OCR confidence for the image."""
        if not TESSERACT_AVAILABLE:
            return 0.0
        try:
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            confidences = [c for c in ocr_data["conf"] if isinstance(c, (int, float)) and c > 0]
            return float(np.mean(confidences)) if confidences else 0.0
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # OCR text extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _ocr_text(img: Image.Image, psm: int = 6, digits_only: bool = False) -> str:
        """Run Tesseract OCR on a preprocessed image."""
        if not TESSERACT_AVAILABLE:
            return ""
        config = f"--psm {psm}"
        if digits_only:
            config += " -c tessedit_char_whitelist=0123456789/NC "
        try:
            return pytesseract.image_to_string(img, config=config) or ""
        except Exception as e:
            logger.debug("OCR failed: %s", e)
            return ""

    @staticmethod
    def _crop_top(img: Image.Image, fraction: float = 0.15) -> Image.Image:
        """Crop the top portion of an image for focused extraction."""
        w, h = img.size
        return img.crop((0, 0, w, int(h * fraction)))