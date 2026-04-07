"""Review Tab — editable fields, confidence icons, work-type override.

Shows extracted data with confidence indicators (✓ / ⚠ / ✗).
Supports manual editing, zone→district→WBS cascading, and validation.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.domain.enums import CaseStatus, WorkType
from app.domain.models import Case
from app.infrastructure.config_manager import ConfigManager
from app.services.validator_service import ValidatorService
from app.ui.widgets import VerificationPanel

logger = logging.getLogger(__name__)


class ReviewTab(ttk.Frame):
    """Tab for reviewing and editing extracted case data."""

    def __init__(
        self,
        master: tk.Widget,
        config: Optional[ConfigManager] = None,
        on_approve: Optional[Callable[[Case], None]] = None,
        on_reject: Optional[Callable[[Case, str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._config = config or ConfigManager()
        self._on_approve = on_approve
        self._on_reject = on_reject
        self._current_case: Optional[Case] = None
        self._validator = ValidatorService()

        self._fields: dict[str, tk.StringVar] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        # Title
        ttk.Label(
            self,
            text="Review Extracted Data",
            font=("Calibri", 14, "bold"),
        ).pack(pady=(15, 5))

        # Scrollable form
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=canvas.yview)
        self._form_frame = ttk.Frame(canvas)

        self._form_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=YES, padx=10)
        scrollbar.pack(side=RIGHT, fill=Y)

        # ── Extraction warnings banner (hidden by default) ──────
        self._warn_frame = ttk.Frame(self._form_frame)
        self._warn_frame.pack(fill=X, padx=10, pady=(5, 0))
        self._warn_labels: list[ttk.Label] = []

        # Build editable fields
        field_defs = [
            ("order_no", "Order No"),
            ("notification_no", "Notification No"),
            ("applicant_name", "Consumer Name"),
            ("address", "Address"),
            ("pin_code", "PIN Code"),
            ("zone", "Zone"),
            ("district", "District"),
            ("wbs_no", "WBS No"),
            ("load_applied", "Load Applied"),
            ("category", "Category"),
            ("grand_total", "Grand Total"),
            ("scope_of_work", "Scope of Work"),
            ("existing_dt_capacity", "Existing DT Capacity"),
            ("new_transformer_rating", "New Transformer Rating"),
            ("tapping_pole", "Tapping Pole"),
        ]

        for attr, label in field_defs:
            row = ttk.Frame(self._form_frame)
            row.pack(fill=X, padx=10, pady=3)
            ttk.Label(row, text=f"{label}:", width=20, anchor="w").pack(side=LEFT)
            var = tk.StringVar()
            entry = ttk.Entry(row, textvariable=var, width=50)
            entry.pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))
            self._fields[attr] = var

        # Zone → District cascade
        self._fields["zone"].trace_add("write", self._on_zone_changed)

        # Work type dropdown
        wt_frame = ttk.Frame(self._form_frame)
        wt_frame.pack(fill=X, padx=10, pady=3)
        ttk.Label(wt_frame, text="Work Type:", width=20, anchor="w").pack(side=LEFT)
        self._wt_var = tk.StringVar()
        wt_combo = ttk.Combobox(
            wt_frame,
            textvariable=self._wt_var,
            values=[wt.display_name for wt in WorkType],
            state="readonly",
            width=40,
        )
        wt_combo.pack(side=LEFT, padx=(5, 0))

        # Verification panel
        ttk.Separator(self._form_frame, orient=HORIZONTAL).pack(fill=X, padx=10, pady=10)
        self._verification = VerificationPanel(self._form_frame)
        self._verification.pack(fill=X, padx=10)

        # Action buttons
        btn_frame = ttk.Frame(self._form_frame)
        btn_frame.pack(pady=15)
        ttk.Button(
            btn_frame,
            text="↻ Re-validate",
            command=self._revalidate,
            bootstyle="outline-info",
            width=15,
        ).pack(side=LEFT, padx=10)
        ttk.Button(
            btn_frame,
            text="✓ Approve & Save",
            command=self._approve,
            bootstyle="success",
            width=20,
        ).pack(side=LEFT, padx=10)
        ttk.Button(
            btn_frame,
            text="✗ Reject",
            command=self._reject,
            bootstyle="danger",
            width=20,
        ).pack(side=LEFT, padx=10)

    # ── Extraction warnings ─────────────────────────────────────

    def _show_extraction_warnings(self, warnings: list[str]) -> None:
        """Show extraction-level warnings above the form."""
        for lbl in self._warn_labels:
            lbl.destroy()
        self._warn_labels.clear()

        for msg in warnings:
            lbl = ttk.Label(
                self._warn_frame,
                text=f"⚠ {msg}",
                bootstyle="warning",
                wraplength=500,
                font=("Calibri", 9),
            )
            lbl.pack(fill=X, pady=1, anchor="w")
            self._warn_labels.append(lbl)

    # ── Load / cascading ────────────────────────────────────────

    def load_case(self, case: Case) -> None:
        """Load a case into the review form."""
        self._current_case = case

        field_map = {
            "order_no": case.order_no,
            "notification_no": case.notification_no,
            "applicant_name": case.applicant_name,
            "address": case.address,
            "pin_code": case.pin_code,
            "zone": case.zone,
            "district": case.district,
            "wbs_no": case.wbs_no,
            "load_applied": case.load_applied,
            "category": case.category,
            "grand_total": str(case.grand_total) if case.grand_total else "",
            "scope_of_work": case.scope_of_work,
            "existing_dt_capacity": case.existing_dt_capacity,
            "new_transformer_rating": case.new_transformer_rating,
            "tapping_pole": case.tapping_pole,
        }
        for attr, val in field_map.items():
            self._fields[attr].set(val or "")

        if case.work_type:
            self._wt_var.set(case.work_type.display_name)

        # Trigger zone → district → WBS cascade after loading
        if case.zone:
            self._on_zone_changed()

        # Show extraction warnings if any
        warnings = getattr(case, "extraction_warnings", None) or []
        self._show_extraction_warnings(warnings)

        if case.validation_result:
            self._verification.set_checks(case.validation_result.checks)

    def _on_zone_changed(self, *_args) -> None:
        zone = self._fields["zone"].get().strip()
        if zone:
            district = self._config.get_district_for_zone(zone)
            if district:
                self._fields["district"].set(district)
                wbs = self._config.get_wbs_for_district(district)
                if wbs:
                    self._fields["wbs_no"].set(wbs)

    # ── Re-validation ───────────────────────────────────────────

    def _revalidate(self) -> None:
        """Re-run validation on the current (possibly edited) case data."""
        if not self._current_case:
            return
        self._apply_edits_to_case()
        result = self._validator.validate(self._current_case)
        self._current_case.validation_result = result
        self._verification.set_checks(result.checks)

    # ── Edit helpers ────────────────────────────────────────────

    def _apply_edits_to_case(self) -> None:
        """Push UI field values back to the current Case."""
        if not self._current_case:
            return
        case = self._current_case
        case.order_no = self._fields["order_no"].get().strip() or None
        case.notification_no = self._fields["notification_no"].get().strip() or None
        case.applicant_name = self._fields["applicant_name"].get().strip() or None
        case.address = self._fields["address"].get().strip() or None
        case.pin_code = self._fields["pin_code"].get().strip() or None
        case.zone = self._fields["zone"].get().strip() or None
        case.district = self._fields["district"].get().strip() or None
        case.wbs_no = self._fields["wbs_no"].get().strip() or None
        case.load_applied = self._fields["load_applied"].get().strip() or None
        case.category = self._fields["category"].get().strip() or None
        gt_str = self._fields["grand_total"].get().strip()
        if gt_str:
            try:
                case.grand_total = float(gt_str.replace(",", ""))
            except ValueError:
                pass
        case.scope_of_work = self._fields["scope_of_work"].get().strip() or None
        case.existing_dt_capacity = self._fields["existing_dt_capacity"].get().strip() or None
        case.new_transformer_rating = self._fields["new_transformer_rating"].get().strip() or None
        case.tapping_pole = self._fields["tapping_pole"].get().strip() or None

        # Work type from dropdown
        wt_name = self._wt_var.get()
        for wt in WorkType:
            if wt.display_name == wt_name:
                case.work_type = wt
                break

    def _approve(self) -> None:
        if not self._current_case:
            return
        self._apply_edits_to_case()
        if self._on_approve:
            self._on_approve(self._current_case)

    def _reject(self) -> None:
        if not self._current_case:
            return
        self._apply_edits_to_case()
        # Ask for correction details
        dlg = _CorrectionDialog(self)
        self.wait_window(dlg)
        if dlg.correction_text and self._on_reject:
            self._on_reject(self._current_case, dlg.correction_text)


class _CorrectionDialog(ttk.Toplevel):
    """Small dialog to enter correction/rejection details."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Rejection Details")
        self.geometry("400x200")
        self.grab_set()
        self.correction_text: Optional[str] = None

        ttk.Label(self, text="Correction details:", font=("Calibri", 10)).pack(
            padx=10, pady=(10, 5), anchor="w"
        )
        self._text = tk.Text(self, height=5, width=45)
        self._text.pack(padx=10, fill=BOTH, expand=YES)

        ttk.Button(self, text="Submit", command=self._submit, bootstyle="danger").pack(
            pady=10
        )

    def _submit(self) -> None:
        self.correction_text = self._text.get("1.0", tk.END).strip()
        self.destroy()
