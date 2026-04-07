"""Backup manager — creates timestamped zip backups of DB and docs."""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path

from app.infrastructure.file_utils import ensure_directory
from app.infrastructure.logger import get_logger

logger = get_logger(__name__)


class BackupManager:
    """Creates timestamped zip backups of the database and generated documents."""

    def __init__(self, db_path: Path, output_dir: Path, backup_dir: Path) -> None:
        self._db_path = db_path
        self._output_dir = output_dir
        self._backup_dir = backup_dir

    def create_backup(self) -> Path:
        """Create a full backup zip and return its path.

        Includes:
        - SQLite database file
        - All generated .docx files in the output directory
        """
        ensure_directory(self._backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"backup_{timestamp}.zip"
        zip_path = self._backup_dir / zip_name

        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            # Backup database
            if self._db_path.exists():
                zf.write(str(self._db_path), f"db/{self._db_path.name}")
                logger.info("Backed up database: %s", self._db_path.name)

            # Backup generated documents
            if self._output_dir.exists():
                for doc_file in self._output_dir.glob("*.docx"):
                    zf.write(str(doc_file), f"output/{doc_file.name}")

            # Backup tracker Excel if present in output dir
            for xlsx in self._output_dir.parent.glob("New_Connection_FY26.xlsx"):
                zf.write(str(xlsx), f"tracker/{xlsx.name}")

        logger.info("Backup created: %s", zip_path)
        return zip_path

    def list_backups(self) -> list[Path]:
        """Return all backup zip files sorted by date (newest first)."""
        if not self._backup_dir.exists():
            return []
        return sorted(self._backup_dir.glob("backup_*.zip"), reverse=True)
