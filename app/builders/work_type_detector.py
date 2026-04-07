"""Work type detection from BOM materials — Part 3.

Priority: DT_AUGMENTATION > ABC_WIRING > LT_HT_POLE > LT_STANDARD.
Never raises an exception — always returns a WorkType.
"""

from __future__ import annotations

from app.domain.constants import (
    WT_ABC_KW,
    WT_DT_AUG_NATURE_KW,
    WT_LT_HT_KW,
    WT_TRANSFORMER_KW,
)
from app.domain.enums import WorkType
from app.domain.models import Material
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


def detect_work_type(materials: list[Material], nature_text: str) -> WorkType:
    """Detect work type from BOM materials and nature-of-scheme text.

    Priority order:
        1. DT Augmentation — transformer in BOM or augmentation in nature
        2. ABC Wiring — ABC/Aerial Bunched cable in BOM
        3. LT with HT Pole — 2-core single-phase cable in BOM
        4. LT Standard — default

    Args:
        materials: List of Material dataclass instances from BOM extraction.
        nature_text: Nature of Scheme text from Scheme Copy.

    Returns:
        WorkType enum value. Never raises.
    """
    descs = [m.description.upper() for m in materials]
    nature = nature_text.upper() if nature_text else ""

    # Priority 1: DT Augmentation
    if any(any(kw in d for kw in WT_TRANSFORMER_KW) for d in descs):
        logger.info("Work type detected: DT_AUGMENTATION (transformer in BOM)")
        return WorkType.DT_AUGMENTATION
    if any(kw in nature for kw in WT_DT_AUG_NATURE_KW):
        logger.info("Work type detected: DT_AUGMENTATION (nature text)")
        return WorkType.DT_AUGMENTATION

    # Priority 2: ABC Wiring
    if any(any(kw in d for kw in WT_ABC_KW) for d in descs):
        logger.info("Work type detected: ABC_WIRING")
        return WorkType.ABC_WIRING

    # Priority 3: LT with HT Pole
    if any(any(kw in d for kw in WT_LT_HT_KW) for d in descs):
        logger.info("Work type detected: LT_HT_POLE")
        return WorkType.LT_HT_POLE

    # Default
    logger.info("Work type detected: LT_STANDARD (default)")
    return WorkType.LT_STANDARD