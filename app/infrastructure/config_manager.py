"""Singleton configuration manager for the TPDDL PM06 tool.

Reads config.ini and JSON config files. Auto-creates config.ini
with sensible defaults on first run.
"""

from __future__ import annotations

import configparser
import json
import os
import stat
import threading
from pathlib import Path
from typing import Any, Optional

from app.domain.constants import (
    BACKUP_DIR,
    CONFIG_FILENAME,
    DB_FILENAME,
    DEFAULT_OUTPUT_DIR,
    LOGS_DIR,
    RECOVERY_DIR,
    TRACKER_FILENAME,
    ZONE_DISTRICT_MAP,
    WBS_MAP,
    get_tracker_filename,
)
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


def _get_app_root() -> Path:
    """Return the application root directory.

    Works both when running as a normal script and when
    bundled with PyInstaller (--onedir or --onefile).
    """
    import sys
    if getattr(sys, "frozen", False):
        # PyInstaller stores the bundle in sys._MEIPASS (onefile)
        # or the exe's directory (onedir). We want the directory
        # containing the exe so runtime files (config.ini, output/)
        # are stored next to it — not inside the temp extract folder.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


_ROOT_DIR: Path = _get_app_root()


class ConfigManager:
    """Singleton configuration manager.

    Thread-safe. Loads config.ini and all JSON config files.
    """

    _instance: Optional[ConfigManager] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> ConfigManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        self._initialised = True
        self._config = configparser.ConfigParser()
        self._root_dir = _ROOT_DIR
        self._config_path = self._root_dir / CONFIG_FILENAME
        self._zone_district_map: dict[str, list[int]] = {}
        self._wbs_map: dict[str, dict] = {}
        self._work_types_config: dict = {}
        self._load_config()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load config.ini and JSON config files."""
        if not self._config_path.exists():
            self._create_default_config()
        self._config.read(str(self._config_path), encoding="utf-8")
        self._load_zone_district_map()
        self._load_wbs_map()
        self._load_work_types()
        logger.info("Configuration loaded from %s", self._config_path)

    def _create_default_config(self) -> None:
        """Create config.ini with sensible defaults for first run."""
        try:
            tracker_name = get_tracker_filename()
        except Exception:
            tracker_name = TRACKER_FILENAME
        self._config["General"] = {
            "engineer_name": "",
            "output_dir": str(self._root_dir / DEFAULT_OUTPUT_DIR),
            "tracker_path": str(self._root_dir / tracker_name),
            "font_size": "11",
            "theme": "litera",
        }
        self._config["Database"] = {
            "db_path": str(self._root_dir / DB_FILENAME),
        }
        self._config["Paths"] = {
            "logs_dir": str(self._root_dir / LOGS_DIR),
            "backup_dir": str(self._root_dir / BACKUP_DIR),
            "recovery_dir": str(self._root_dir / RECOVERY_DIR),
        }
        self._config["Window"] = {
            "width": "1200",
            "height": "800",
            "x": "",
            "y": "",
        }
        with open(self._config_path, "w", encoding="utf-8") as f:
            self._config.write(f)
        try:
            os.chmod(self._config_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        except OSError:
            pass  # best-effort; may fail on some Windows configs
        logger.info("Created default config at %s", self._config_path)

    def reset_to_defaults(self) -> None:
        """Reset config.ini to factory defaults (preserves window geometry)."""
        # Preserve window geometry so user doesn't lose position
        geom = {}
        if self._config.has_section("Window"):
            geom = dict(self._config["Window"])
        self._create_default_config()
        if geom:
            if not self._config.has_section("Window"):
                self._config.add_section("Window")
            for k, v in geom.items():
                self._config.set("Window", k, v)
            with open(self._config_path, "w", encoding="utf-8") as f:
                self._config.write(f)
        logger.info("Config reset to defaults")

    def _load_json_config(self, filename: str) -> dict:
        """Load a JSON file from the config/ directory.

        For PyInstaller bundles, bundled config files live inside
        sys._MEIPASS while user-editable ones may sit next to the exe.
        We prefer the exe-side copy (user may have edited it) and
        fall back to the bundled copy.
        """
        import sys
        json_path = self._root_dir / "config" / filename
        if not json_path.exists() and getattr(sys, "frozen", False):
            # Try the bundled data directory
            bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
            json_path = bundle_dir / "config" / filename
        if not json_path.exists():
            logger.warning("Config file not found: %s", json_path)
            return {}
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_zone_district_map(self) -> None:
        data = self._load_json_config("zone_district_map.json")
        if data:
            self._zone_district_map = {k: v for k, v in data.items()}
        else:
            self._zone_district_map = dict(ZONE_DISTRICT_MAP)

    def _load_wbs_map(self) -> None:
        data = self._load_json_config("wbs_map.json")
        if data:
            self._wbs_map = data
        else:
            self._wbs_map = dict(WBS_MAP)

    def _load_work_types(self) -> None:
        self._work_types_config = self._load_json_config("work_types.json")

    # ------------------------------------------------------------------
    # Properties — typed access to config values
    # ------------------------------------------------------------------

    @property
    def root_dir(self) -> Path:
        return self._root_dir

    @property
    def engineer_name(self) -> str:
        return self._config.get("General", "engineer_name", fallback="")

    @engineer_name.setter
    def engineer_name(self, value: str) -> None:
        self._config.set("General", "engineer_name", value)
        self._save()

    @property
    def output_dir(self) -> Path:
        return Path(self._config.get("General", "output_dir", fallback=str(self._root_dir / DEFAULT_OUTPUT_DIR)))

    @output_dir.setter
    def output_dir(self, value: Path) -> None:
        self._config.set("General", "output_dir", str(value))
        self._save()

    @property
    def tracker_path(self) -> Path:
        return Path(self._config.get("General", "tracker_path", fallback=str(self._root_dir / TRACKER_FILENAME)))

    @property
    def db_path(self) -> Path:
        return Path(self._config.get("Database", "db_path", fallback=str(self._root_dir / DB_FILENAME)))

    @property
    def font_size(self) -> int:
        return self._config.getint("General", "font_size", fallback=11)

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._config.set("General", "font_size", str(max(9, min(14, value))))
        self._save()

    @property
    def theme(self) -> str:
        return self._config.get("General", "theme", fallback="litera")

    @property
    def logs_dir(self) -> Path:
        return Path(self._config.get("Paths", "logs_dir", fallback=str(self._root_dir / LOGS_DIR)))

    @property
    def backup_dir(self) -> Path:
        return Path(self._config.get("Paths", "backup_dir", fallback=str(self._root_dir / BACKUP_DIR)))

    @property
    def recovery_dir(self) -> Path:
        return Path(self._config.get("Paths", "recovery_dir", fallback=str(self._root_dir / RECOVERY_DIR)))

    @property
    def window_geometry(self) -> dict[str, str]:
        return {
            "width": self._config.get("Window", "width", fallback="1200"),
            "height": self._config.get("Window", "height", fallback="800"),
            "x": self._config.get("Window", "x", fallback=""),
            "y": self._config.get("Window", "y", fallback=""),
        }

    def save_window_geometry(self, width: int, height: int, x: int, y: int) -> None:
        self._config.set("Window", "width", str(width))
        self._config.set("Window", "height", str(height))
        self._config.set("Window", "x", str(x))
        self._config.set("Window", "y", str(y))
        self._save()

    # ------------------------------------------------------------------
    # Zone / District / WBS mappings
    # ------------------------------------------------------------------

    @property
    def zone_district_map(self) -> dict[str, list[int]]:
        return self._zone_district_map

    @property
    def wbs_map(self) -> dict[str, dict]:
        return self._wbs_map

    @property
    def work_types_config(self) -> dict:
        return self._work_types_config

    def get_district_for_zone(self, zone_code: int | str) -> Optional[str]:
        """Look up the district code for a given zone number.

        Returns district code string (e.g. 'NRL') or None if not found.
        """
        zone_num = int(zone_code)
        for district, zones in self._zone_district_map.items():
            if zone_num in zones:
                return district
        return None

    def get_wbs_for_district(self, district_code: str) -> Optional[str]:
        """Look up WBS number for a given district code.

        Returns WBS string (e.g. 'CE/N0000/00137') or None if not found.
        """
        for wbs_no, info in self._wbs_map.items():
            if district_code in info.get("districts", []):
                return wbs_no
        return None

    def save_zone_district_map(self, data: dict[str, list[int]]) -> None:
        """Save updated zone-district map to JSON config."""
        self._zone_district_map = data
        json_path = self._root_dir / "config" / "zone_district_map.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Zone-district map saved to %s", json_path)

    def save_wbs_map(self, data: dict[str, dict]) -> None:
        """Save updated WBS map to JSON config."""
        self._wbs_map = data
        json_path = self._root_dir / "config" / "wbs_map.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("WBS map saved to %s", json_path)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Write current config state to config.ini."""
        with open(self._config_path, "w", encoding="utf-8") as f:
            self._config.write(f)

    def save(self) -> None:
        """Public alias for _save — write config to disk."""
        self._save()

    def set(self, section: str, key: str, value: str) -> None:
        """Set a config value (creates section if needed)."""
        if not self._config.has_section(section):
            self._config.add_section(section)
        self._config.set(section, key, value)

    def get(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """Get a config value with optional fallback."""
        return self._config.get(section, key, fallback=fallback)

    def reload(self) -> None:
        """Reload all configuration from disk."""
        self._config = configparser.ConfigParser()
        self._load_config()

    @property
    def is_first_run(self) -> bool:
        """True if engineer_name is empty (setup wizard needed)."""
        return not self.engineer_name.strip()

    def get_path(self, key: str) -> Path:
        """Generic path getter for any config key."""
        _path_map: dict[str, Path] = {
            "output": self.output_dir,
            "tracker": self.tracker_path,
            "db": self.db_path,
            "logs": self.logs_dir,
            "backup": self.backup_dir,
            "recovery": self.recovery_dir,
            "root": self.root_dir,
        }
        return _path_map.get(key, self._root_dir)
