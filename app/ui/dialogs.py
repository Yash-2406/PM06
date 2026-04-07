"""Dialogs — user-facing message dialogs for the TPDDL PM06 tool.

- Error, warning, confirm dialogs (friendly text, no tracebacks)
- Recovery dialog
- Duplicate order dialog
- Setup wizard (first-run: engineer name + output folder)
"""

from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Tuple

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

logger = logging.getLogger(__name__)


def show_error(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """Show an error dialog with friendly text."""
    messagebox.showerror(title, message, parent=parent)


def show_warning(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """Show a warning dialog."""
    messagebox.showwarning(title, message, parent=parent)


def show_info(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """Show an info dialog."""
    messagebox.showinfo(title, message, parent=parent)


def ask_yes_no(title: str, message: str, parent: Optional[tk.Widget] = None) -> bool:
    """Show a yes/no confirmation dialog."""
    return messagebox.askyesno(title, message, parent=parent)


def ask_duplicate_order(
    order_no: str, parent: Optional[tk.Widget] = None
) -> bool:
    """Ask user whether to overwrite an existing order."""
    return messagebox.askyesno(
        "Duplicate Order Number",
        f"Order No '{order_no}' already exists in the database.\n\n"
        "Do you want to update the existing record?\n"
        "(Click 'No' to cancel this operation.)",
        parent=parent,
    )


def ask_recovery(parent: Optional[tk.Widget] = None) -> bool:
    """Ask user whether to restore from a recovery file."""
    return messagebox.askyesno(
        "Recovery Available",
        "A previous session was interrupted.\n\n"
        "Would you like to restore your last working state?",
        parent=parent,
    )


class SetupWizardDialog(ttk.Toplevel):
    """First-run setup wizard: engineer name + output folder."""

    def __init__(self, master: tk.Widget, config_manager):
        super().__init__(master)
        self.title("First-Time Setup")
        self.geometry("450x300")
        self.resizable(False, False)
        self.grab_set()

        self._config = config_manager
        self._result: Optional[dict] = None

        # Header
        ttk.Label(
            self,
            text="Welcome to the TPDDL PM06 Tool",
            font=("Calibri", 14, "bold"),
            bootstyle="primary",
        ).pack(pady=(20, 10))

        ttk.Label(
            self,
            text="Please provide initial settings:",
            font=("Calibri", 10),
        ).pack(pady=(0, 15))

        # Engineer name
        frame_name = ttk.Frame(self)
        frame_name.pack(fill=X, padx=30, pady=5)
        ttk.Label(frame_name, text="Engineer Name:", width=15).pack(side=LEFT)
        self._name_var = tk.StringVar()
        ttk.Entry(frame_name, textvariable=self._name_var, width=30).pack(
            side=LEFT, fill=X, expand=YES
        )

        # Output folder
        frame_dir = ttk.Frame(self)
        frame_dir.pack(fill=X, padx=30, pady=5)
        ttk.Label(frame_dir, text="Output Folder:", width=15).pack(side=LEFT)
        self._dir_var = tk.StringVar(
            value=str(config_manager.output_dir)
        )
        ttk.Entry(frame_dir, textvariable=self._dir_var, width=22).pack(
            side=LEFT, fill=X, expand=YES
        )
        ttk.Button(
            frame_dir, text="Browse", command=self._browse_dir, bootstyle="outline"
        ).pack(side=RIGHT, padx=(5, 0))

        # Buttons
        frame_btn = ttk.Frame(self)
        frame_btn.pack(pady=30)
        ttk.Button(
            frame_btn, text="Save & Continue", command=self._save, bootstyle="success"
        ).pack(side=LEFT, padx=10)
        ttk.Button(
            frame_btn, text="Skip", command=self._skip, bootstyle="secondary"
        ).pack(side=LEFT)

    def _browse_dir(self) -> None:
        directory = filedialog.askdirectory(initialdir=self._dir_var.get())
        if directory:
            self._dir_var.set(directory)

    def _save(self) -> None:
        name = self._name_var.get().strip()
        out_dir = self._dir_var.get().strip()
        if not name:
            show_warning("Missing Name", "Please enter your name.", parent=self)
            return

        self._config.engineer_name = name
        self._config.output_dir = Path(out_dir)
        self._config.set("General", "first_run_done", "true")
        self._config.save()
        self._result = {"name": name, "output_dir": out_dir}
        self.destroy()

    def _skip(self) -> None:
        self._config.set("General", "first_run_done", "true")
        self._config.save()
        self.destroy()

    @property
    def result(self) -> Optional[dict]:
        return self._result
