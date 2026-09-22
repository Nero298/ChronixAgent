"""
Windows auto-start via Scheduled Task (spec section 24).

Chosen over the Startup folder / registry Run key because schtasks.exe
has been present since Windows XP, works reliably on Windows 7, and
supports "run whether user is logged on or not" more cleanly than a
Startup-folder shortcut.

This module never silently creates duplicate tasks: it always checks
current status first via `schtasks /query` before creating anything.
"""
from __future__ import annotations

import logging
import subprocess
import sys

from core.constants import PRODUCT_NAME

log = logging.getLogger("chronix.startup")

TASK_NAME = "ChronixAgentAutoStart"


class AutoStartError(Exception):
    pass


def _run_schtasks(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["schtasks.exe", *args],
        capture_output=True, text=True, check=False,
    )


def is_configured() -> bool:
    """Return True if the auto-start task already exists (avoids duplicates)."""
    result = _run_schtasks(["/query", "/tn", TASK_NAME])
    return result.returncode == 0


def enable_auto_start(exe_path: str) -> None:
    """Create the scheduled task if it doesn't already exist.

    Raises AutoStartError on failure (e.g. insufficient permissions).
    Never creates a second task if one is already configured - callers
    can call this unconditionally on every startup without risk of
    duplicate/looping task creation.
    """
    if is_configured():
        log.info("Auto-start already configured (task '%s' exists); skipping.", TASK_NAME)
        return

    result = _run_schtasks([
        "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{exe_path}"',
        "/sc", "onlogon",
        "/rl", "limited",   # do not require elevated privileges to run
        "/f",               # overwrite is safe here since is_configured() already
                             # confirmed nothing exists; kept only to avoid an
                             # interactive confirmation prompt from schtasks itself
    ])
    if result.returncode != 0:
        raise AutoStartError(
            f"Could not configure auto-start (schtasks exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    log.info("Auto-start configured: %s will launch on logon.", PRODUCT_NAME)


def disable_auto_start() -> None:
    """Remove the scheduled task. Safe to call even if not configured."""
    if not is_configured():
        log.info("Auto-start was not configured; nothing to remove.")
        return
    result = _run_schtasks(["/delete", "/tn", TASK_NAME, "/f"])
    if result.returncode != 0:
        raise AutoStartError(
            f"Could not remove auto-start task (schtasks exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )
    log.info("Auto-start removed.")


def setup_from_cli() -> int:
    """Entry point for `python -m agent.startup` / a packaged helper command."""
    logging.basicConfig(level=logging.INFO)
    exe_path = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
    try:
        enable_auto_start(exe_path)
    except AutoStartError as exc:
        log.error(str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(setup_from_cli())
