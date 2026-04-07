"""Tracker Tab — searchable / filterable Treeview of all cases.

Supports district, zone, status filters, date range, and double-click editing.
"""

from __future__ import annotations

import logging
import tkinter as tk
from datetime import datetime
from typing import Callable, List, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.domain.enums import CaseStatus
from app.domain.models import Case
from app.services.tracker_service import TrackerService
from app.ui.dialogs import show_error, show_info

logger = logging.getLogger(__name__)


class TrackerTab(ttk.Frame):
    """Tab for viewing and managing all processed cases."""

    def __init__(
        self,
        master: tk.Widget,
        tracker_service: TrackerService,
        on_view_case: Optional[Callable[[Case], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._tracker = tracker_service
        self._on_view_case = on_view_case

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        # Title
        ttk.Label(
            self,
            text="Case Tracker",
            font=("Calibri", 14, "bold"),
        ).pack(pady=(15, 5))

        # Filter bar
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=X, padx=15, pady=5)

        ttk.Label(filter_frame, text="District:").pack(side=LEFT, padx=(0, 5))
        self._district_var = tk.StringVar(value="All")
        self._district_combo = ttk.Combobox(
            filter_frame, textvariable=self._district_var, width=12, state="readonly"
        )
        self._district_combo.pack(side=LEFT, padx=(0, 10))

        ttk.Label(filter_frame, text="Status:").pack(side=LEFT, padx=(0, 5))
        self._status_var = tk.StringVar(value="All")
        self._status_combo = ttk.Combobox(
            filter_frame,
            textvariable=self._status_var,
            values=["All"] + [s.value for s in CaseStatus],
            width=12,
            state="readonly",
        )
        self._status_combo.pack(side=LEFT, padx=(0, 10))

        ttk.Label(filter_frame, text="Search:").pack(side=LEFT, padx=(0, 5))
        self._search_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self._search_var, width=20).pack(
            side=LEFT, padx=(0, 10)
        )

        ttk.Button(
            filter_frame,
            text="🔍 Filter",
            command=self.refresh,
            bootstyle="outline-primary",
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            filter_frame,
            text="↻ Refresh",
            command=self.refresh,
            bootstyle="outline-info",
        ).pack(side=LEFT)

        # Treeview
        columns = ("id", "order_no", "notif_no", "name", "zone", "district", "status", "date")
        self._tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            selectmode="browse",
            bootstyle="primary",
        )

        col_config = {
            "id": ("ID", 40),
            "order_no": ("Order No", 100),
            "notif_no": ("Notification No", 120),
            "name": ("Consumer Name", 180),
            "zone": ("Zone", 80),
            "district": ("District", 80),
            "status": ("Status", 80),
            "date": ("Date", 90),
        }
        for col, (heading, width) in col_config.items():
            self._tree.heading(col, text=heading, anchor="w")
            self._tree.column(col, width=width, minwidth=40)

        # Scrollbar
        tree_scroll = ttk.Scrollbar(self, orient=VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_scroll.set)

        self._tree.pack(fill=BOTH, expand=YES, padx=15, pady=5, side=LEFT)
        tree_scroll.pack(fill=Y, side=RIGHT, pady=5, padx=(0, 15))

        # Double-click to view
        self._tree.bind("<Double-1>", self._on_double_click)

        # Bottom bar
        bottom = ttk.Frame(self)
        bottom.pack(fill=X, padx=15, pady=10)
        self._count_label = ttk.Label(bottom, text="0 cases", bootstyle="secondary")
        self._count_label.pack(side=LEFT)

        ttk.Button(
            bottom,
            text="Export to Excel",
            command=self._export,
            bootstyle="outline-success",
        ).pack(side=RIGHT)

    def refresh(self) -> None:
        """Reload data into the treeview."""
        # Clear
        for item in self._tree.get_children():
            self._tree.delete(item)

        # Get filter values
        district = self._district_var.get()
        status_str = self._status_var.get()
        search = self._search_var.get().strip().lower()

        district_filter = None if district == "All" else district
        status_filter = None
        if status_str != "All":
            try:
                status_filter = CaseStatus(status_str)
            except ValueError:
                pass

        cases = self._tracker.list_cases(
            district=district_filter, status=status_filter
        )

        # Apply text search
        if search:
            cases = [
                c for c in cases
                if search in (c.order_no or "").lower()
                or search in (c.notification_no or "").lower()
                or search in (c.applicant_name or "").lower()
            ]

        # Populate
        for case in cases:
            date_str = ""
            if case.created_at:
                date_str = case.created_at.strftime("%d-%m-%Y")
            self._tree.insert(
                "",
                tk.END,
                iid=str(case.id),
                values=(
                    case.id,
                    case.order_no or "",
                    case.notification_no or "",
                    case.applicant_name or "",
                    case.zone or "",
                    case.district or "",
                    case.status.value if case.status else "",
                    date_str,
                ),
            )

        self._count_label.configure(text=f"{len(cases)} cases")

        # Update district combo values
        all_districts = sorted({c.district for c in cases if c.district})
        self._district_combo.configure(values=["All"] + all_districts)

    def _on_double_click(self, event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        case_id = int(sel[0])
        case = self._tracker.get_case(case_id)
        if case and self._on_view_case:
            self._on_view_case(case)

    def _export(self) -> None:
        from tkinter import filedialog
        from app.services.export_service import ExportService

        # Read current filter state so export matches the visible data
        district = self._district_var.get()
        district_filter = None if district == "All" else district

        status_str = self._status_var.get()
        status_filter = None
        if status_str != "All":
            try:
                from app.domain.enums import CaseStatus as _CS
                status_filter = _CS(status_str)
            except ValueError:
                pass

        # Build a descriptive default filename
        from datetime import datetime as _dt
        parts = ["Tracker"]
        if district_filter:
            parts.append(district_filter)
        if status_filter:
            parts.append(status_filter.value)
        parts.append(_dt.now().strftime("%d-%b-%Y"))
        default_name = "_".join(parts) + ".xlsx"

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=default_name,
        )
        if path:
            try:
                svc = ExportService(db=self._tracker._db, config=self._tracker._config)
                svc.export_to_excel(
                    path,
                    district=district_filter,
                    status=status_filter,
                )
                count = len(self._tree.get_children())
                show_info(
                    "Export Complete",
                    f"Exported {count} cases to:\n{path}",
                    parent=self,
                )
            except Exception as e:
                show_error("Export Failed", str(e), parent=self)
