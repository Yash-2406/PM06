#!/usr/bin/env python3
"""Entry point for the TPDDL PM06 Executive Summary Generator and Tracker.

Checks Python version (requires 3.9+) before launching.
"""

import sys


def _check_python_version() -> None:
    if sys.version_info < (3, 9):
        print(
            f"ERROR: Python 3.9 or later is required (found {sys.version}).\n"
            "Please upgrade Python and try again.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    _check_python_version()
    from app.main import main

    main()