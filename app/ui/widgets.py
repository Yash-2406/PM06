"""Reusable UI widgets for the TPDDL PM06 tool.

- DragDropFrame: file drop zone with click-to-browse fallback
- VerificationPanel: red / yellow / green validation checks
- ProgressOverlay: non-blocking progress bar overlay
- FilePickerWidget: filename display with status icon
"""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

logger = logging.getLogger(__name__)

# Try to load tkinterdnd2 for native drag-drop; graceful fallback
try:
    from tkinterdnd2 import DND_FILES  # type: ignore[import-untyped]

    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    logger.info("tkinterdnd2 not available — drag-drop disabled, click-to-browse only")


class DragDropFrame(ttk.Frame):
    """File drop zone with click-to-browse fallback.

    Args:
        master: Parent widget.
        label: Text shown in the drop zone.
        filetypes: File type tuples for the file dialog.
        on_file_selected: Callback receiving the selected file path.
    """

    def __init__(
        self,
        master: tk.Widget,
        label: str = "Drop file here or click to browse",
        filetypes: Optional[list[tuple[str, str]]] = None,
        on_file_selected: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._filetypes = filetypes or [("All files", "*.*")]
        self._on_file_selected = on_file_selected
        self._file_path: Optional[str] = None

        self._label = ttk.Label(
            self,
            text=label,
            anchor="center",
            bootstyle="secondary",
            font=("Calibri", 10),
        )
        self._label.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Click-to-browse
        self._label.bind("<Button-1>", self._browse)
        self.bind("<Button-1>", self._browse)

        # Drag-and-drop
        if DND_AVAILABLE:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                logger.debug("DND registration failed", exc_info=True)

        # Visual styling
        self.configure(borderwidth=2, relief="groove")

    def _browse(self, _event=None) -> None:
        path = filedialog.askopenfilename(filetypes=self._filetypes)
        if path:
            self._set_file(path)

    def _on_drop(self, event) -> None:
        path = event.data
        # Strip curly braces that Windows sometimes adds
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        if path:
            self._set_file(path)

    def _set_file(self, path: str) -> None:
        self._file_path = path
        name = Path(path).name
        self._label.configure(text=f"✓ {name}", bootstyle="success")
        if self._on_file_selected:
            self._on_file_selected(path)

    @property
    def file_path(self) -> Optional[str]:
        return self._file_path

    def reset(self) -> None:
        self._file_path = None
        self._label.configure(
            text="Drop file here or click to browse", bootstyle="secondary"
        )


class VerificationPanel(ttk.Frame):
    """Displays validation checks as colored labels (red/yellow/green)."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)
        self._check_labels: list[ttk.Label] = []

    def set_checks(self, checks: list) -> None:
        """Update the panel with validation check results.

        Args:
            checks: List of ValidationCheck objects.
        """
        # Clear existing
        for lbl in self._check_labels:
            lbl.destroy()
        self._check_labels.clear()

        for check in checks:
            if check.passed:
                icon = "✓"
                style = "success"
            elif check.is_blocking:
                icon = "✗"
                style = "danger"
            else:
                icon = "⚠"
                style = "warning"

            text = f"{icon}  {check.field}: {check.message or check.rule}"
            lbl = ttk.Label(self, text=text, bootstyle=style, wraplength=500)
            lbl.pack(fill=X, padx=5, pady=2, anchor="w")
            self._check_labels.append(lbl)


class ProgressOverlay(ttk.Frame):
    """Non-blocking progress bar overlay."""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, **kwargs)
        self._progress_var = tk.DoubleVar(value=0)
        self._status_var = tk.StringVar(value="Ready")

        self._bar = ttk.Progressbar(
            self,
            variable=self._progress_var,
            maximum=100,
            bootstyle="success-striped",
        )
        self._bar.pack(fill=X, padx=10, pady=(5, 0))

        self._status_label = ttk.Label(
            self,
            textvariable=self._status_var,
            font=("Calibri", 9),
        )
        self._status_label.pack(fill=X, padx=10, pady=(2, 5))

    def update_progress(self, percent: int, message: str) -> None:
        """Thread-safe progress update."""
        self._progress_var.set(percent)
        self._status_var.set(message)

    def reset(self) -> None:
        self._progress_var.set(0)
        self._status_var.set("Ready")


class FilePickerWidget(ttk.Frame):
    """Compact file picker: filename + green check / red X icon."""

    def __init__(
        self,
        master: tk.Widget,
        label: str = "File:",
        filetypes: Optional[list[tuple[str, str]]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self._filetypes = filetypes or [("All files", "*.*")]
        self._file_path: Optional[str] = None

        ttk.Label(self, text=label, width=12).pack(side=LEFT, padx=(0, 5))

        self._name_var = tk.StringVar(value="(none)")
        self._name_label = ttk.Label(
            self, textvariable=self._name_var, bootstyle="secondary"
        )
        self._name_label.pack(side=LEFT, fill=X, expand=YES)

        self._icon_label = ttk.Label(self, text="✗", bootstyle="danger")
        self._icon_label.pack(side=LEFT, padx=5)

        btn = ttk.Button(
            self, text="Browse", command=self._browse, bootstyle="outline"
        )
        btn.pack(side=RIGHT)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(filetypes=self._filetypes)
        if path:
            self.set_file(path)

    def set_file(self, path: str) -> None:
        self._file_path = path
        self._name_var.set(Path(path).name)
        self._icon_label.configure(text="✓", bootstyle="success")

    @property
    def file_path(self) -> Optional[str]:
        return self._file_path

    def reset(self) -> None:
        self._file_path = None
        self._name_var.set("(none)")
        self._icon_label.configure(text="✗", bootstyle="danger")


def add_tooltip(widget: tk.Widget, text: str) -> None:
    """Add a simple hover tooltip to any widget."""
    tip = None

    def _enter(event):
        nonlocal tip
        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 10}")
        lbl = tk.Label(
            tip, text=text, background="#ffffe0", relief="solid", borderwidth=1,
            font=("Calibri", 9),
        )
        lbl.pack()

    def _leave(_event):
        nonlocal tip
        if tip:
            tip.destroy()
            tip = None

    widget.bind("<Enter>", _enter)
    widget.bind("<Leave>", _leave)
