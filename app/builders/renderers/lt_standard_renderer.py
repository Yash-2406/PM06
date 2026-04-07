"""LT Standard renderer — LT Line Extension (Standard)."""

from __future__ import annotations

from typing import Optional

from app.builders.renderers.base_renderer import BaseRenderer, pick_pole_ref


class LTStandardRenderer(BaseRenderer):
    """Text blocks for LT-STD work type."""

    def capex_title(
        self,
        notification_no: str,
        existing_dt_capacity: Optional[str] = None,
        new_transformer_rating: Optional[str] = None,
        acb_description: Optional[str] = None,
    ) -> str:
        return (
            f"LT extension required for releasing new connection "
            f"vide Notification No. {notification_no}"
        )

    def existing_scenario(self, notification_no: str, **kwargs) -> str:
        return (
            f"TATA Power Company Limited had requested for connection "
            f"vide consumer notification no. {notification_no}"
        )

    def proposed_scenario(
        self,
        tapping_pole: Optional[str],
        existing_dt_capacity: Optional[str],
        new_transformer_rating: Optional[str] = None,
        acb_description: Optional[str] = None,
        substation_name: Optional[str] = None,
    ) -> str:
        pole = pick_pole_ref(tapping_pole, substation_name)
        dt = existing_dt_capacity or "[DT Capacity]"
        return (
            f"LT line extension is proposed from pole no. {pole} of "
            f"{dt} to applicant's premises to release the applied new connection."
        )

    def sub_head(self) -> str:
        return "LT Line Extension up to 5 Poles"
