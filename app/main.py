"""Application bootstrap — initialises logging, config, DB, then launches the UI."""

from __future__ import annotations

import logging
import sys


def main() -> None:
    """Bootstrap and run the application."""
    # 1. Initialise logging first
    from app.infrastructure.logger import setup_logging

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting TPDDL PM06 Tool (Python %s)", sys.version)

    try:
        # 2. Load configuration (creates config.ini on first run)
        from app.infrastructure.config_manager import ConfigManager

        config = ConfigManager()
        logger.info("Config loaded: output_dir=%s", config.output_dir)

        # 3. Initialise database (creates/migrates schema)
        from app.data.database import Database

        db = Database(config.db_path)
        db.initialise()
        logger.info("Database ready: %s", config.db_path)

        # 4. Launch UI
        from app.ui.main_window import MainWindow

        window = MainWindow()
        window.run()

    except Exception:
        logger.exception("Fatal error during startup")
        # Show a minimal error dialog if possible
        try:
            import tkinter.messagebox as mb

            mb.showerror(
                "Startup Error",
                "The application failed to start. Check the log files in the 'logs' folder.",
            )
        except Exception:
            pass
        sys.exit(1)