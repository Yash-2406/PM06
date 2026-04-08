"""Settings Tab — config editor, zone/WBS map editors.

Provides UI for editing:
  - Output folder, font size, engineer name
  - Zone-district map (JSON table)
  - WBS map (JSON table)
"""

from __future__ import annotations

import json
import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.infrastructure.config_manager import ConfigManager
from app.ui.dialogs import show_error, show_info

logger = logging.getLogger(__name__)


class SettingsTab(ttk.Frame):
    """Tab for application configuration."""

    def __init__(
        self, master: tk.Widget, config: ConfigManager, **kwargs
    ):
        super().__init__(master, **kwargs)
        self._config = config
        self._build_ui()

    def _build_ui(self) -> None:
        # Title
        ttk.Label(
            self,
            text="Settings",
            font=("Calibri", 14, "bold"),
        ).pack(pady=(15, 10))

        # ── General settings ────────────────────────────────────
        general_frame = ttk.LabelFrame(self, text="General")
        general_frame.pack(fill=X, padx=20, pady=5)

        # Engineer name
        row1 = ttk.Frame(general_frame)
        row1.pack(fill=X, pady=3)
        ttk.Label(row1, text="Engineer Name:", width=15).pack(side=LEFT)
        self._name_var = tk.StringVar(value=self._config.engineer_name or "")
        ttk.Entry(row1, textvariable=self._name_var, width=40).pack(
            side=LEFT, fill=X, expand=YES
        )

        # Output folder
        row2 = ttk.Frame(general_frame)
        row2.pack(fill=X, pady=3)
        ttk.Label(row2, text="Output Folder:", width=15).pack(side=LEFT)
        self._dir_var = tk.StringVar(value=str(self._config.output_dir))
        ttk.Entry(row2, textvariable=self._dir_var, width=35).pack(
            side=LEFT, fill=X, expand=YES
        )
        ttk.Button(
            row2, text="Browse", command=self._browse_dir, bootstyle="outline"
        ).pack(side=RIGHT, padx=(5, 0))

        # Font size
        row3 = ttk.Frame(general_frame)
        row3.pack(fill=X, pady=3)
        ttk.Label(row3, text="Font Size:", width=15).pack(side=LEFT)
        self._font_var = tk.IntVar(
            value=int(self._config.get("General", "font_size", fallback="10"))
        )
        ttk.Spinbox(row3, from_=8, to=16, textvariable=self._font_var, width=5).pack(
            side=LEFT
        )

        # Save button row
        btn_row = ttk.Frame(general_frame)
        btn_row.pack(pady=(10, 0))
        ttk.Button(
            btn_row,
            text="Save Settings",
            command=self._save_settings,
            bootstyle="success",
        ).pack(side=LEFT, padx=(0, 10))
        ttk.Button(
            btn_row,
            text="Reset to Defaults",
            command=self._reset_defaults,
            bootstyle="danger-outline",
        ).pack(side=LEFT)

        # ── Zone-District Map ───────────────────────────────────
        zone_frame = ttk.LabelFrame(self, text="Zone \u2192 District Mapping")
        zone_frame.pack(fill=BOTH, expand=YES, padx=20, pady=5)

        self._zone_text = tk.Text(zone_frame, height=8, width=60, font=("Consolas", 9))
        self._zone_text.pack(fill=BOTH, expand=YES)

        zone_data = self._config.zone_district_map
        self._zone_text.insert("1.0", json.dumps(zone_data, indent=2))

        ttk.Button(
            zone_frame,
            text="Save Zone Map",
            command=self._save_zone_map,
            bootstyle="outline-success",
        ).pack(pady=(5, 0))

        # ── WBS Map ─────────────────────────────────────────────
        wbs_frame = ttk.LabelFrame(self, text="WBS Mapping")
        wbs_frame.pack(fill=BOTH, expand=YES, padx=20, pady=5)

        self._wbs_text = tk.Text(wbs_frame, height=6, width=60, font=("Consolas", 9))
        self._wbs_text.pack(fill=BOTH, expand=YES)

        wbs_data = self._config.wbs_map
        self._wbs_text.insert("1.0", json.dumps(wbs_data, indent=2))

        ttk.Button(
            wbs_frame,
            text="Save WBS Map",
            command=self._save_wbs_map,
            bootstyle="outline-success",
        ).pack(pady=(5, 0))

    def _browse_dir(self) -> None:
        directory = filedialog.askdirectory(initialdir=self._dir_var.get())
        if directory:
            self._dir_var.set(directory)

    def _save_settings(self) -> None:
        try:
            self._config.engineer_name = self._name_var.get().strip()
            self._config.output_dir = Path(self._dir_var.get().strip())
            self._config.set("General", "font_size", str(self._font_var.get()))
            self._config.save()
            show_info("Settings Saved", "Your settings have been saved.", parent=self)
        except Exception as e:
            show_error("Save Failed", str(e), parent=self)

    def _reset_defaults(self) -> None:
        from tkinter import messagebox
        if not messagebox.askyesno(
            "Reset to Defaults",
            "This will reset all settings to factory defaults.\nAre you sure?",
            parent=self,
        ):
            return
        try:
            self._config.reset_to_defaults()
            # Refresh UI fields
            self._name_var.set(self._config.engineer_name or "")
            self._dir_var.set(str(self._config.output_dir))
            self._font_var.set(int(self._config.get("General", "font_size", fallback="11")))
            show_info("Reset Complete", "Settings have been reset to defaults.", parent=self)
        except Exception as e:
            show_error("Reset Failed", str(e), parent=self)

    def _save_zone_map(self) -> None:
        try:
            raw = self._zone_text.get("1.0", tk.END).strip()
            data = json.loads(raw)
            self._config.save_zone_district_map(data)
            show_info("Saved", "Zone-District map updated.", parent=self)
        except json.JSONDecodeError as e:
            show_error("Invalid JSON", f"Please fix the JSON:\n{e}", parent=self)
        except Exception as e:
            show_error("Save Failed", str(e), parent=self)

    def _save_wbs_map(self) -> None:
        try:
            raw = self._wbs_text.get("1.0", tk.END).strip()
            data = json.loads(raw)
            self._config.save_wbs_map(data)
            show_info("Saved", "WBS map updated.", parent=self)
        except json.JSONDecodeError as e:
            show_error("Invalid JSON", f"Please fix the JSON:\n{e}", parent=self)
        except Exception as e:
            show_error("Save Failed", str(e), parent=self)
