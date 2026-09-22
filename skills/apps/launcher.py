"""
Application launching skill (action: open_app).

Adapted from Zisu_AI-main/core/app_helper.py - the Start Menu scan +
rapidfuzz matching logic is reused almost unchanged since it already
worked well and has no Windows-7-incompatible dependencies.

Renamed "match_app" usage into a clean skill interface that returns a
result dict instead of a bare tuple, and added actual subprocess launch
+ graceful "not found" handling (spec section 14/30), which the
original helper did not include.
"""
from __future__ import annotations

import logging
import os
import subprocess

try:
    from rapidfuzz import process, fuzz
    _HAVE_RAPIDFUZZ = True
except ImportError:  # pragma: no cover - exercised only if dependency missing
    _HAVE_RAPIDFUZZ = False

log = logging.getLogger("chronix.skills.apps")

STANDARD_APPS = {
    "notepad": "notepad.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "control panel": "control.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "chrome": "chrome.exe",
    "msedge": "msedge.exe",
    "edge": "msedge.exe",
    "discord": "discord.exe",
}

_STRIP_WORDS = ("mở", "bật", "chạy", "khởi động", "open", "run", "launch", "start", "ứng dụng", "app")


def get_installed_apps() -> dict:
    """Scan Start Menu shortcuts (per-user + all-users) plus standard exes."""
    apps: dict[str, dict] = {}

    program_data = os.environ.get("ProgramData", "C:\\ProgramData")
    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))

    scan_dirs = [
        os.path.join(program_data, "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(user_profile, "AppData", "Roaming", "Microsoft", "Windows",
                      "Start Menu", "Programs"),
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for root, _dirs, files in os.walk(scan_dir):
            for fname in files:
                if fname.lower().endswith(".lnk"):
                    app_name = fname[:-4]
                    apps[app_name.lower()] = {
                        "name": app_name,
                        "path": os.path.join(root, fname),
                    }

    for key, path in STANDARD_APPS.items():
        apps.setdefault(key, {"name": key, "path": path})

    return apps


def match_app(query_text: str) -> tuple[str | None, str | None]:
    apps = get_installed_apps()
    if not apps:
        return None, None

    clean = query_text.lower()
    for verb in _STRIP_WORDS:
        clean = clean.replace(verb, " ")
    clean = " ".join(clean.split()).strip() or query_text.lower().strip()

    if not _HAVE_RAPIDFUZZ:
        # Fallback: exact / substring match only.
        if clean in apps:
            return apps[clean]["name"], apps[clean]["path"]
        for key, info in apps.items():
            if clean in key or key in clean:
                return info["name"], info["path"]
        return None, None

    match = process.extractOne(clean, list(apps.keys()), scorer=fuzz.WRatio)
    if match:
        matched_key, score, _ = match
        if score >= 50:
            return apps[matched_key]["name"], apps[matched_key]["path"]
    return None, None


def open_app(query_text: str) -> dict:
    """Launch an application by fuzzy name match. Returns a result dict.

    Never raises - subprocess/OS errors are caught and turned into a
    human-readable failure message per spec section 30.
    """
    name, path = match_app(query_text)
    if not path:
        return {
            "success": False,
            "message": f"Could not find an application matching '{query_text}'.",
        }

    try:
        if path.lower().endswith(".lnk"):
            os.startfile(path)  # noqa: S606 - Windows-only, intentional
        else:
            subprocess.Popen(path, shell=False)
    except FileNotFoundError:
        return {
            "success": False,
            "message": f"'{name}' could not be opened because the executable could not be found.",
        }
    except OSError as exc:
        log.warning("Failed to launch %s (%s): %s", name, path, exc)
        return {"success": False, "message": f"Failed to open '{name}': {exc}"}

    return {"success": True, "message": f"Opening {name}."}
