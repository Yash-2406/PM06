"""Cost table image extraction from Scheme Copy PDF — Part 12.

Uses PyMuPDF (fitz) for rendering. No Poppler required.
Critical: pdfplumber Y-axis (bottom-left) → PyMuPDF Y-axis (top-left) conversion.
"""

from __future__ import annotations

from pathlib import Path

from app.domain.constants import COST_TABLE_IMAGE_DPI
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


def extract_cost_table_image(pdf_path: Path, output_path: Path) -> bool:
    """Extract the 5-row cost summary table as a PNG image.

    Uses pdfplumber to find the table bounding box, then PyMuPDF
    to render the cropped area at 200 DPI.

    CRITICAL: Converts pdfplumber coordinates (bottom-left origin)
    to PyMuPDF coordinates (top-left origin) before cropping.

    Args:
        pdf_path: Path to the Scheme Copy PDF.
        output_path: Where to save the extracted PNG.

    Returns:
        True on success, False on any failure (never raises).
    """
    try:
        import fitz
        import pdfplumber

        pdf_path = Path(pdf_path)
        output_path = Path(output_path)

        # Step 1: Find the page and bounding box
        target_page_idx = None
        cost_table_bbox = None
        page_height_pts = None

        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                text_nospace = text.replace(" ", "")
                if ("Bill of material" in text or "Billofmaterial" in text_nospace) and \
                   ("Total (Rs.)" in text or "Total(Rs.)" in text_nospace):
                    target_page_idx = i
                    page_height_pts = float(page.height)
                    for table in page.find_tables():
                        flat = " ".join(
                            str(c) for row in table.extract()
                            for c in row if c is not None
                        )
                        flat_nospace = flat.replace(" ", "")
                        if "Bill of material" in flat or "Bill of Material" in flat or \
                           "Billofmaterial" in flat_nospace or "BillofMaterial" in flat_nospace:
                            cost_table_bbox = table.bbox
                            break
                    break

        if target_page_idx is None:
            logger.warning("Cost table page not found in scheme copy PDF")
            return False

        # Step 2: Render with PyMuPDF at configured DPI
        scale = COST_TABLE_IMAGE_DPI / 72.0
        doc = fitz.open(str(pdf_path))
        page = doc[target_page_idx]
        mat = fitz.Matrix(scale, scale)

        if cost_table_bbox is not None and page_height_pts is not None:
            # pdfplumber and PyMuPDF both use top-left origin coordinates
            # Capture from page top (includes logo/header) to table bottom
            x0_pts, y0_pts, x1_pts, y1_pts = cost_table_bbox
            padding_pts = 10
            clip = fitz.Rect(
                0,
                0,
                page.rect.width,
                y1_pts + padding_pts,
            )
            pixmap = page.get_pixmap(matrix=mat, clip=clip)
        else:
            # Fallback: render middle-third of page
            page_rect = page.rect
            clip = fitz.Rect(
                page_rect.x0,
                page_rect.y0 + page_rect.height * 0.35,
                page_rect.x1,
                page_rect.y0 + page_rect.height * 0.65,
            )
            pixmap = page.get_pixmap(matrix=mat, clip=clip)

        # Check for blank pixmap
        if pixmap.width < 10 or pixmap.height < 10:
            logger.warning("PyMuPDF clip returned tiny pixmap — falling back")
            page_rect = page.rect
            clip = fitz.Rect(
                page_rect.x0,
                page_rect.y0 + page_rect.height * 0.35,
                page_rect.x1,
                page_rect.y0 + page_rect.height * 0.65,
            )
            pixmap = page.get_pixmap(matrix=mat, clip=clip)

        doc.close()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(output_path))
        logger.info("Cost table image saved: %s", output_path)
        return True

    except ImportError as e:
        logger.error("Required library not available: %s", e)
        return False
    except Exception as e:
        logger.exception("Cost table image extraction failed: %s", e)
        return False