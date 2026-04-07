"""MIS Tab — Management Information System summary.

Displays counts by district/zone/status/work-type, total amounts,
monthly trend, and District × Status matrix.  Supports Excel export
and drill-down into the Tracker tab.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Callable, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.infrastructure.formatting import format_indian_amount
from app.services.export_service import ExportService
from app.ui.dialogs import show_error, show_info

logger = logging.getLogger(__name__)

# Status → card colour mapping
_STATUS_STYLE: dict[str, str] = {
    "Approved": "success",
    "Pending": "warning",
    "Rejected": "danger",
}


class MISTab(ttk.Frame):
    """Tab for MIS summary reporting."""

    def __init__(
        self,
        master: tk.Widget,
        export_service: ExportService,
        on_drill_down: Optional[Callable[[str, str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._export_service = export_service
        self._on_drill_down = on_drill_down
        self._build_ui()
        self.refresh()

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        # Title + action bar
        top = ttk.Frame(self)
        top.pack(fill=X, padx=20, pady=(15, 5))

        ttk.Label(
            top, text="MIS Summary", font=("Calibri", 14, "bold")
        ).pack(side=LEFT)

        ttk.Button(
            top, text="Export Excel", command=self._export,
            bootstyle="outline-success",
        ).pack(side=RIGHT, padx=5)

        ttk.Button(
            top, text="↻ Refresh", command=self.refresh,
            bootstyle="outline-info",
        ).pack(side=RIGHT, padx=5)

        # ── Summary cards row ───────────────────────────────────
        self._summary_frame = ttk.Frame(self)
        self._summary_frame.pack(fill=X, padx=20, pady=10)

        self._total_var = tk.StringVar(value="Total Cases: 0")
        self._amount_var = tk.StringVar(value="Total Amount: ₹0")
        self._approved_var = tk.StringVar(value="Approved: 0")
        self._pending_var = tk.StringVar(value="Pending: 0")
        self._rejected_var = tk.StringVar(value="Rejected: 0")

        for var, style in [
            (self._total_var, "primary"),
            (self._amount_var, "success"),
            (self._approved_var, "success"),
            (self._pending_var, "warning"),
            (self._rejected_var, "danger"),
        ]:
            lbl = ttk.Label(
                self._summary_frame,
                textvariable=var,
                font=("Calibri", 11, "bold"),
                bootstyle=style,
            )
            lbl.pack(side=LEFT, padx=12)

        # ── Scrollable body ─────────────────────────────────────
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=VERTICAL, command=canvas.yview)
        self._body = ttk.Frame(canvas)
        self._body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=YES, padx=10)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── District breakdown ──────────────────────────────────
        self._add_section_label("By District  (double-click to drill down)")
        self._district_tree = self._make_tree(
            ("district", "count", "amount"),
            [("District", 120), ("Count", 80), ("Amount (₹)", 160)],
        )
        self._district_tree.bind("<Double-1>", self._on_district_drill)

        # ── Zone breakdown ──────────────────────────────────────
        self._add_section_label("By Zone")
        self._zone_tree = self._make_tree(
            ("zone", "count"),
            [("Zone", 120), ("Count", 80)],
        )

        # ── Work Type breakdown ─────────────────────────────────
        self._add_section_label("By Work Type")
        self._wt_tree = self._make_tree(
            ("work_type", "count"),
            [("Work Type", 200), ("Count", 80)],
        )

        # ── Monthly Trend ───────────────────────────────────────
        self._add_section_label("Monthly Trend")
        self._trend_tree = self._make_tree(
            ("month", "count", "amount"),
            [("Month", 120), ("Cases", 80), ("Amount (₹)", 160)],
        )

        # ── District × Status matrix ───────────────────────────
        self._add_section_label("District × Status Matrix")
        self._matrix_tree = ttk.Treeview(
            self._body, show="headings", height=10, bootstyle="info",
        )
        self._matrix_tree.pack(fill=X, padx=10, pady=5)

    # ── Helpers ─────────────────────────────────────────────────

    def _add_section_label(self, text: str) -> None:
        ttk.Label(
            self._body, text=text, font=("Calibri", 11, "bold"),
        ).pack(pady=(12, 4), anchor="w", padx=10)

    def _make_tree(
        self,
        col_ids: tuple[str, ...],
        col_defs: list[tuple[str, int]],
    ) -> ttk.Treeview:
        tree = ttk.Treeview(
            self._body, columns=col_ids, show="headings",
            height=6, bootstyle="info",
        )
        for cid, (heading, width) in zip(col_ids, col_defs):
            tree.heading(cid, text=heading, anchor="w")
            tree.column(cid, width=width, minwidth=60)
        tree.pack(fill=X, padx=10, pady=5)
        return tree

    @staticmethod
    def _populate_tree(tree: ttk.Treeview, rows: list[tuple]) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tree.insert("", tk.END, values=row)

    # ── Data refresh ────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload MIS data from the database."""
        try:
            data = self._export_service.get_mis_data()
        except Exception:
            logger.exception("Failed to load MIS data")
            return

        # Summary cards
        total = data.get("total_cases", 0)
        by_status = data.get("by_status", {})
        self._total_var.set(f"Total Cases: {total}")
        self._amount_var.set(
            f"Total Amount: ₹{data.get('total_amount_formatted', '0')}"
        )
        self._approved_var.set(f"Approved: {by_status.get('Approved', 0)}")
        self._pending_var.set(f"Pending: {by_status.get('Pending', 0)}")
        self._rejected_var.set(f"Rejected: {by_status.get('Rejected', 0)}")

        # District table
        amount_by_district = data.get("amount_by_district", {})
        district_rows = [
            (d, c, format_indian_amount(amount_by_district.get(d, 0)))
            for d, c in sorted(data.get("by_district", {}).items())
        ]
        self._populate_tree(self._district_tree, district_rows)

        # Zone table
        zone_rows = [
            (z, c) for z, c in sorted(data.get("by_zone", {}).items())
        ]
        self._populate_tree(self._zone_tree, zone_rows)

        # Work type table
        wt_rows = [
            (wt, c) for wt, c in sorted(data.get("by_work_type", {}).items())
        ]
        self._populate_tree(self._wt_tree, wt_rows)

        # Monthly trend
        trend_rows = [
            (r["month"], r["cnt"], format_indian_amount(r["total"]))
            for r in data.get("monthly_trend", [])
        ]
        self._populate_tree(self._trend_tree, trend_rows)

        # District × Status matrix
        self._refresh_matrix(data)

    def _refresh_matrix(self, data: dict) -> None:
        """Build District × Status pivot table."""
        records = data.get("district_status_counts", [])
        statuses = sorted({r["status"] for r in records if r.get("status")})
        if not statuses:
            statuses = ["Pending", "Approved", "Rejected"]

        col_ids = ["district"] + statuses + ["total"]
        col_headings = ["District"] + statuses + ["Total"]

        self._matrix_tree.configure(columns=col_ids)
        for cid, heading in zip(col_ids, col_headings):
            self._matrix_tree.heading(cid, text=heading, anchor="w")
            w = 100 if cid != "district" else 120
            self._matrix_tree.column(cid, width=w, minwidth=60)

        # Build pivot
        matrix: dict[str, dict[str, int]] = {}
        for r in records:
            d = r.get("district_code") or "UNKNOWN"
            s = r.get("status") or "UNKNOWN"
            matrix.setdefault(d, {})[s] = r["count"]

        rows = []
        for district in sorted(matrix.keys()):
            vals = [district]
            row_total = 0
            for s in statuses:
                c = matrix[district].get(s, 0)
                vals.append(c)
                row_total += c
            vals.append(row_total)
            rows.append(tuple(vals))
        self._populate_tree(self._matrix_tree, rows)

    # ── Drill-down ──────────────────────────────────────────────

    def _on_district_drill(self, event) -> None:
        """Double-click on a district row navigates to
        Tracker tab filtered by that district."""
        sel = self._district_tree.selection()
        if not sel or not self._on_drill_down:
            return
        values = self._district_tree.item(sel[0], "values")
        if values:
            self._on_drill_down("district", str(values[0]))

    # ── Export ──────────────────────────────────────────────────

    def _export(self) -> None:
        """Export MIS summary to Excel."""
        from tkinter import filedialog
        from datetime import datetime as _dt

        default_name = f"MIS_Summary_{_dt.now().strftime('%d-%b-%Y')}.xlsx"
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=default_name,
        )
        if not path:
            return
        try:
            out = self._export_service.export_mis_to_excel(path)
            show_info(
                "MIS Export Complete",
                f"Report saved to:\n{out}",
                parent=self,
            )
        except Exception as e:
            logger.exception("MIS export failed")
            show_error("Export Failed", str(e), parent=self)
