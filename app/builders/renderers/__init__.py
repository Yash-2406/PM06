"""Renderers — Strategy pattern: one renderer per work type."""

from app.builders.renderers.base_renderer import BaseRenderer
from app.builders.renderers.lt_standard_renderer import LTStandardRenderer
from app.builders.renderers.lt_ht_pole_renderer import LTHTPoleRenderer
from app.builders.renderers.dt_augmentation_renderer import DTAugmentationRenderer
from app.builders.renderers.abc_wiring_renderer import ABCWiringRenderer
from app.domain.enums import WorkType


_RENDERER_MAP: dict[WorkType, type[BaseRenderer]] = {
    WorkType.LT_STANDARD: LTStandardRenderer,
    WorkType.LT_HT_POLE: LTHTPoleRenderer,
    WorkType.DT_AUGMENTATION: DTAugmentationRenderer,
    WorkType.ABC_WIRING: ABCWiringRenderer,
}


def get_renderer(work_type: WorkType) -> BaseRenderer:
    """Return the appropriate renderer for the given work type."""
    cls = _RENDERER_MAP.get(work_type, LTStandardRenderer)
    return cls()
