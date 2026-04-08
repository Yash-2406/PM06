"""Lightweight update checker — queries GitHub Releases API on startup.

Non-blocking: runs in a background thread.  If a newer release exists,
shows a one-time toast / info-bar in the UI.  Never downloads or modifies
anything automatically.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.request
import urllib.error
from typing import Callable, Optional

from app import __version__

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com/repos/Yash-2406/PM06/releases/latest"
_TIMEOUT = 5  # seconds


def _parse_version(tag: str) -> tuple[int, ...]:
    """Convert 'v1.2.3' or '1.2.3' to (1, 2, 3)."""
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def check_for_update(callback: Callable[[str, str], None]) -> None:
    """Check GitHub for a newer release in a background thread.

    Args:
        callback: Called on the *calling* thread with (latest_version, download_url)
                  only when a newer version exists.  Not called otherwise.
    """

    def _worker() -> None:
        try:
            req = urllib.request.Request(
                _GITHUB_API,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
            tag = data.get("tag_name", "")
            if not tag:
                return
            latest = _parse_version(tag)
            current = _parse_version(__version__)
            if latest > current:
                url = data.get("html_url", "")
                logger.info("Update available: %s (current: %s)", tag, __version__)
                callback(tag, url)
            else:
                logger.debug("Up to date: %s", __version__)
        except (urllib.error.URLError, ValueError, OSError) as exc:
            logger.debug("Update check skipped: %s", exc)

    t = threading.Thread(target=_worker, daemon=True, name="update-checker")
    t.start()
