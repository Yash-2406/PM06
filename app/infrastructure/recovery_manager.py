"""Recovery manager — auto-save in-progress work and restore on startup.

Uses atexit handler to save current session state to recovery/ folder.
On startup, checks for recovery files and offers to restore.
"""

from __future__ import annotations

import atexit
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app.infrastructure.file_utils import ensure_directory
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


class RecoveryManager:
    """Manages auto-save / restore of in-progress work."""

    def __init__(self, recovery_dir: Path) -> None:
        self._recovery_dir = recovery_dir
        self._current_state: dict[str, Any] = {}
        self._registered = False

    def register_atexit(self) -> None:
        """Register the atexit handler for crash recovery."""
        if not self._registered:
            atexit.register(self._save_on_exit)
            self._registered = True
            logger.info("Recovery atexit handler registered")

    def update_state(self, key: str, value: Any) -> None:
        """Update a key in the current in-progress state."""
        self._current_state[key] = value

    def clear_state(self) -> None:
        """Clear current state (call after successful generation)."""
        self._current_state.clear()

    def _save_on_exit(self) -> None:
        """Save current state to recovery file if there is unsaved work."""
        if not self._current_state:
            return
        ensure_directory(self._recovery_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recovery_path = self._recovery_dir / f"recovery_{timestamp}.json"
        try:
            serialisable = self._make_serialisable(self._current_state)
            with open(recovery_path, "w", encoding="utf-8") as f:
                json.dump(serialisable, f, indent=2, default=str)
            logger.info("Recovery state saved to %s", recovery_path)
        except (OSError, TypeError) as e:
            logger.error("Failed to save recovery state: %s", e)

    def has_recovery_data(self) -> bool:
        """Check if any recovery files exist."""
        if not self._recovery_dir.exists():
            return False
        return any(self._recovery_dir.glob("recovery_*.json"))

    def get_latest_recovery(self) -> Optional[dict[str, Any]]:
        """Load the most recent recovery file."""
        if not self._recovery_dir.exists():
            return None
        files = sorted(self._recovery_dir.glob("recovery_*.json"), reverse=True)
        if not files:
            return None
        try:
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded recovery data from %s", files[0])
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to load recovery data: %s", e)
            return None

    def clear_recovery_files(self) -> None:
        """Remove all recovery files after successful restore or dismiss."""
        if not self._recovery_dir.exists():
            return
        for f in self._recovery_dir.glob("recovery_*.json"):
            try:
                f.unlink()
            except OSError as e:
                logger.warning("Failed to remove recovery file %s: %s", f, e)
        logger.info("Recovery files cleared")

    @staticmethod
    def _make_serialisable(obj: Any) -> Any:
        """Convert non-serialisable types to strings for JSON export."""
        if isinstance(obj, dict):
            return {k: RecoveryManager._make_serialisable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [RecoveryManager._make_serialisable(item) for item in obj]
        if isinstance(obj, Path):
            return str(obj)
        return obj
