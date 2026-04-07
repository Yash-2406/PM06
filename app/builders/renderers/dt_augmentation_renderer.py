"""DT Augmentation renderer — different CAPEX title and scenarios."""

from __future__ import annotations

import re
from typing import Optional

from app.builders.renderers.base_renderer import BaseRenderer, pick_pole_ref


class DTAugmentationRenderer(BaseRenderer):
    """Text blocks for DT-AUG work type."""

    @staticmethod
    def _format_dt_capacity(cap: str) -> str:
        """Normalize DT capacity for display: '100kVA DT' → '100 KVA'."""
        import re
        if not cap:
            return cap
        m = re.search(r'(\d+)\s*[kK][vV][aA]', cap)
        if m:
            return f"{m.group(1)} KVA"
        return cap

    def capex_title(
        self,
        notification_no: str,
        existing_dt_capacity: Optional[str] = None,
        new_transformer_rating: Optional[str] = None,
        acb_description: Optional[str] = None,
    ) -> str:
        dt_from = self._format_dt_capacity(existing_dt_capacity or "[Existing DT Capacity]")
        dt_to = self._format_dt_capacity(new_transformer_rating or "[New Transformer Rating]")
        acb_part = f" along with {acb_description}" if acb_description else ""
        return (
            f"DT augmentation from {dt_from} TO {dt_to}"
            f"{acb_part} required for releasing new connection "
            f"vide Notification No. {notification_no}"
        )

    def existing_scenario(
        self,
        notification_no: str,
        dt_loading: str | None = None,
        existing_dt_capacity: str | None = None,
        detailed_reason: str | None = None,
    ) -> str:
        # Use the detailed reason from PM06 Excel when available
        if detailed_reason:
            # Clean embedded line breaks from Excel cell formatting
            clean = re.sub(r'\s*\n\s*', ' ', detailed_reason).strip()
            # Collapse multiple spaces
            clean = re.sub(r'  +', ' ', clean)
            prefix = (
                f"TATA Power Company Limited had requested for connection "
                f"vide consumer notification {notification_no}."
            )
            return f"{prefix} {clean}"
        # Fallback: build a generic sentence, include DT loading if available
        loading_detail = ""
        if dt_loading and existing_dt_capacity:
            dt_cap = self._format_dt_capacity(existing_dt_capacity)
            loading_detail = f" (DT Loading: {dt_loading} kVA on {dt_cap})"
        return (
            f"TATA Power Company Limited had requested for connection "
            f"vide consumer notification {notification_no}. "
            f"Existing DT is already running at its peak load hence "
            f"no margin available on DT to release new connection.{loading_detail}"
        )

    def proposed_scenario(
        self,
        tapping_pole: Optional[str],
        existing_dt_capacity: Optional[str],
        new_transformer_rating: Optional[str] = None,
        acb_description: Optional[str] = None,
        substation_name: Optional[str] = None,
    ) -> str:
        dt_from = self._format_dt_capacity(existing_dt_capacity or "[Existing DT Capacity]")
        dt_to = self._format_dt_capacity(new_transformer_rating or "[New Transformer Rating]")
        acb_part = f" along with {acb_description}" if acb_description else ""
        pole = pick_pole_ref(tapping_pole, substation_name)
        return (
            f"DT augmentation required from {dt_from} TO {dt_to}"
            f"{acb_part} for releasing new connection "
            f"at pole no. {pole}."
        )

    def sub_head(self) -> str:
        return "LT Augmentation"
