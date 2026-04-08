"""MainWindow — root application window with tab notebook.

Tabs: Generate | Review | Tracker | MIS | Settings | Help
Uses ttkbootstrap 'litera' theme.
"""

from __future__ import annotations

import logging
import tkinter as tk
from typing import Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.data.database import Database
from app.domain.constants import APP_TITLE
from app.domain.models import Case
from app.infrastructure.config_manager import ConfigManager
from app.infrastructure.recovery_manager import RecoveryManager
from app.infrastructure.update_checker import check_for_update
from app.services.export_service import ExportService
from app.services.generator_service import GeneratorService
from app.services.tracker_service import TrackerService
from app.ui.dialogs import SetupWizardDialog, ask_recovery
from app.ui.generate_tab import GenerateTab
from app.ui.help_tab import HelpTab
from app.ui.mis_tab import MISTab
from app.ui.review_tab import ReviewTab
from app.ui.settings_tab import SettingsTab
from app.ui.tracker_tab import TrackerTab

logger = logging.getLogger(__name__)

_DEFAULT_GEOMETRY = "1100x750"


class MainWindow:
    """Top-level application window."""

    def __init__(self) -> None:
        self._config = ConfigManager()
        self._db = Database(self._config.db_path)
        self._db.initialise()
        self._recovery = RecoveryManager(self._config.output_dir / "recovery")

        # Services
        self._gen_service = GeneratorService(db=self._db, config=self._config)
        self._tracker_service = TrackerService(db=self._db, config=self._config)
        self._export_service = ExportService(db=self._db, config=self._config)

        # Root window
        self._root = ttk.Window(
            title=APP_TITLE,
            themename="litera",
            size=(1100, 750),
            minsize=(900, 600),
        )

        # Restore geometry
        saved_geom = self._config.get("Window", "geometry", fallback=None)
        if saved_geom:
            try:
                self._root.geometry(saved_geom)
            except tk.TclError:
                pass

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_tabs()
        self._check_first_run()
        self._check_recovery()

    def _build_tabs(self) -> None:
        self._notebook = ttk.Notebook(self._root, bootstyle="primary")
        self._notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # Generate tab
        self._generate_tab = GenerateTab(
            self._notebook,
            generator_service=self._gen_service,
            on_generated=self._on_case_generated,
        )
        self._notebook.add(self._generate_tab, text="  Generate  ")

        # Review tab
        self._review_tab = ReviewTab(
            self._notebook,
            config=self._config,
            on_approve=self._on_approve,
            on_reject=self._on_reject,
        )
        self._notebook.add(self._review_tab, text="  Review  ")

        # Tracker tab
        self._tracker_tab = TrackerTab(
            self._notebook,
            tracker_service=self._tracker_service,
            on_view_case=self._on_view_case,
        )
        self._notebook.add(self._tracker_tab, text="  Tracker  ")

        # MIS tab
        self._mis_tab = MISTab(
            self._notebook,
            export_service=self._export_service,
            on_drill_down=self._on_mis_drill_down,
        )
        self._notebook.add(self._mis_tab, text="  MIS  ")

        # Settings tab
        self._settings_tab = SettingsTab(
            self._notebook,
            config=self._config,
        )
        self._notebook.add(self._settings_tab, text="  Settings  ")

        # Help tab
        self._help_tab = HelpTab(self._notebook)
        self._notebook.add(self._help_tab, text="  Help  ")

    def _check_first_run(self) -> None:
        done = self._config.get("General", "first_run_done", fallback="false")
        if done.lower() != "true":
            dlg = SetupWizardDialog(self._root, self._config)
            self._root.wait_window(dlg)

    def _check_recovery(self) -> None:
        if self._recovery.has_recovery_data():
            if ask_recovery(self._root):
                state = self._recovery.get_latest_recovery()
                logger.info("Restored recovery state: %s", state)
            self._recovery.clear_recovery_files()

    # ── Callbacks ───────────────────────────────────────────────

    def _on_case_generated(self, case: Case) -> None:
        """Switch to review tab after generation."""
        self._review_tab.load_case(case)
        self._notebook.select(self._review_tab)
        self._tracker_tab.refresh()
        self._mis_tab.refresh()

    def _on_approve(self, case: Case) -> None:
        if case.id:
            self._tracker_service.approve_case(case.id)
        self._tracker_tab.refresh()
        self._mis_tab.refresh()
        self._notebook.select(self._tracker_tab)

    def _on_reject(self, case: Case, correction_details: str) -> None:
        if case.id:
            self._tracker_service.reject_case(case.id, correction_details)
        self._tracker_tab.refresh()
        self._mis_tab.refresh()
        self._notebook.select(self._tracker_tab)

    def _on_view_case(self, case: Case) -> None:
        self._review_tab.load_case(case)
        self._notebook.select(self._review_tab)

    def _on_mis_drill_down(self, filter_type: str, value: str) -> None:
        """Navigate from MIS to Tracker tab with a pre-applied filter."""
        if filter_type == "district":
            self._tracker_tab._district_var.set(value)
            self._tracker_tab.refresh()
        self._notebook.select(self._tracker_tab)

    def _on_close(self) -> None:
        # Save window geometry
        try:
            self._config.set("Window", "geometry", self._root.geometry())
            self._config.save()
        except Exception:
            pass
        self._root.destroy()

    def run(self) -> None:
        """Start the Tkinter main loop."""
        logger.info("Application started")
        check_for_update(self._on_update_available)
        self._root.mainloop()

    # ── Update notification ─────────────────────────────────────

    def _on_update_available(self, version: str, url: str) -> None:
        """Show a non-blocking update banner (called from background thread)."""
        def _show() -> None:
            import webbrowser
            bar = ttk.Frame(self._root, bootstyle="info")
            bar.pack(fill="x", side="bottom", padx=5, pady=(0, 5))
            ttk.Label(
                bar,
                text=f"  Update available: {version}",
                bootstyle="inverse-info",
            ).pack(side="left", padx=5, pady=3)
            ttk.Button(
                bar,
                text="Download",
                bootstyle="info",
                command=lambda: webbrowser.open(url),
            ).pack(side="left", padx=5, pady=3)
            ttk.Button(
                bar,
                text="✕",
                bootstyle="info-link",
                command=bar.destroy,
            ).pack(side="right", padx=5, pady=3)
        self._root.after(0, _show)
