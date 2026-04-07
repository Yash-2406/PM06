"""Rotating file logger for the TPDDL PM06 tool.

Creates daily log files under logs/ with automatic rotation
at 10 MB and 30-day retention.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.domain.constants import LOG_MAX_BYTES, LOG_RETENTION_DAYS, LOGS_DIR

_ROOT_DIR: Path = Path(__file__).resolve().parents[2]
_LOG_DIR: Path = _ROOT_DIR / LOGS_DIR


def _ensure_log_dir() -> None:
    """Create the logs directory if it does not exist."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def _cleanup_old_logs() -> None:
    """Remove log files older than LOG_RETENTION_DAYS."""
    if not _LOG_DIR.exists():
        return
    today = date.today()
    for log_file in _LOG_DIR.glob("app_*.log*"):
        try:
            age_days = (today - date.fromtimestamp(log_file.stat().st_mtime)).days
            if age_days > LOG_RETENTION_DAYS:
                log_file.unlink(missing_ok=True)
        except OSError:
            pass  # skip files we can't stat


def get_logger(name: str) -> logging.Logger:
    """Return a named logger writing to the daily rotating log file.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        Configured ``logging.Logger``.
    """
    _ensure_log_dir()
    _cleanup_old_logs()

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)

    log_filename = _LOG_DIR / f"app_{date.today().isoformat()}.log"
    file_handler = RotatingFileHandler(
        str(log_filename),
        maxBytes=LOG_MAX_BYTES,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def setup_logging() -> None:
    """Configure the root logger for the entire application.

    Call once at startup before any other imports that use logging.
    """
    _ensure_log_dir()
    _cleanup_old_logs()

    root = logging.getLogger()
    if root.handlers:
        return  # already set up

    root.setLevel(logging.DEBUG)

    # Suppress noisy third-party loggers
    for noisy in ("pdfminer", "pdfminer.psparser", "pdfminer.pdfinterp",
                  "pdfminer.pdfpage", "pdfminer.converter", "pdfminer.cmapdb"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    log_filename = _LOG_DIR / f"app_{date.today().isoformat()}.log"
    file_handler = RotatingFileHandler(
        str(log_filename),
        maxBytes=LOG_MAX_BYTES,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
