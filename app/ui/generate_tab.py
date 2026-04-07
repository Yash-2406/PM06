"""Generate Tab — file pickers, process button, progress bar.

Three drop zones for scheme PDF, site-visit PDF, PM06 Excel.
Process button runs the pipeline in a WorkerThread.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import TYPE_CHECKING, Callable, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.domain.models import Case
from app.services.generator_service import GeneratorService
from app.ui.dialogs import show_error, show_info
from app.ui.widgets import DragDropFrame, ProgressOverlay

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class GenerateTab(ttk.Frame):
    """Tab for uploading files and generating the executive summary."""

    def __init__(
        self,
        master: tk.Widget,
        generator_service: GeneratorService,
        on_generated: Optional[Callable[[Case], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._gen_service = generator_service
        self._on_generated = on_generated

        self._build_ui()

    def _build_ui(self) -> None:
        # Title
        ttk.Label(
            self,
            text="Upload Source Documents",
            font=("Calibri", 14, "bold"),
        ).pack(pady=(15, 10))

        ttk.Label(
            self,
            text="Drop files or click to browse. All three are recommended.",
            font=("Calibri", 9),
            bootstyle="secondary",
        ).pack(pady=(0, 10))

        # Drop zones
        zones_frame = ttk.Frame(self)
        zones_frame.pack(fill=BOTH, expand=YES, padx=20, pady=5)

        self._scheme_drop = DragDropFrame(
            zones_frame,
            label="📄 Scheme Copy PDF\n(Drop here or click)",
            filetypes=[("PDF files", "*.pdf")],
        )
        self._scheme_drop.pack(fill=X, pady=5, ipady=15)

        self._sv_drop = DragDropFrame(
            zones_frame,
            label="📋 Site Visit Form PDF\n(Drop here or click)",
            filetypes=[("PDF files", "*.pdf")],
        )
        self._sv_drop.pack(fill=X, pady=5, ipady=15)

        self._pm06_drop = DragDropFrame(
            zones_frame,
            label="📊 PM06 Format Excel\n(Drop here or click)",
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        self._pm06_drop.pack(fill=X, pady=5, ipady=15)

        # Process button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        self._process_btn = ttk.Button(
            btn_frame,
            text="▶  Generate Executive Summary",
            command=self._on_process,
            bootstyle="success",
            width=35,
        )
        self._process_btn.pack()

        self._reset_btn = ttk.Button(
            btn_frame,
            text="↺  Reset",
            command=self._on_reset,
            bootstyle="outline",
            width=15,
        )
        self._reset_btn.pack(pady=(5, 0))

        # Progress
        self._progress = ProgressOverlay(self)
        self._progress.pack(fill=X, padx=20, pady=(0, 10))

    def _on_process(self) -> None:
        scheme = self._scheme_drop.file_path
        sv = self._sv_drop.file_path
        pm06 = self._pm06_drop.file_path

        if not any([scheme, sv, pm06]):
            show_error(
                "No Files Selected",
                "Please select at least one source document.",
                parent=self,
            )
            return

        self._process_btn.configure(state=DISABLED)

        def _progress(percent: int, message: str) -> None:
            self.after(0, lambda: self._progress.update_progress(percent, message))

        def _done(case: Case | None, error: Exception | None) -> None:
            self.after(0, lambda: self._on_done(case, error))

        self._gen_service.generate_async(
            scheme_pdf_path=scheme,
            site_visit_pdf_path=sv,
            pm06_excel_path=pm06,
            progress_cb=_progress,
            done_cb=_done,
        )

    def _on_done(self, case: Case | None, error: Exception | None) -> None:
        self._process_btn.configure(state=NORMAL)
        if error:
            show_error(
                "Generation Failed",
                f"An error occurred:\n{error}",
                parent=self,
            )
            self._progress.update_progress(0, f"Error: {error}")
            return

        if case:
            show_info(
                "Success",
                f"Executive Summary generated for Order {case.order_no}.\n"
                f"Saved to: {case.output_docx_path}",
                parent=self,
            )
            if self._on_generated:
                self._on_generated(case)

    def _on_reset(self) -> None:
        self._scheme_drop.reset()
        self._sv_drop.reset()
        self._pm06_drop.reset()
        self._progress.reset()
