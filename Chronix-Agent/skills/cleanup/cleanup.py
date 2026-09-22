"""
Cleanup skill. Per spec section 13: "clear cache" must never silently
become "delete all application data". This module only ever targets
known, narrowly-scoped cache directories - never a whole app-data root.
"""
from __future__ import annotations

import os
import shutil

from skills.files.fileops import estimate_size

# Explicit, narrow cache paths only - never an app's entire data directory.
KNOWN_CACHE_PATHS = {
    "chrome": [
        r"AppData\Local\Google\Chrome\User Data\Default\Cache",
        r"AppData\Local\Google\Chrome\User Data\Default\Code Cache",
    ],
    "edge": [
        r"AppData\Local\Microsoft\Edge\User Data\Default\Cache",
    ],
    "temp": [],  # resolved dynamically below
}


def _user_home() -> str:
    return os.environ.get("USERPROFILE", os.path.expanduser("~"))


def resolve_cache_targets(app_name: str) -> list[str]:
    key = (app_name or "").strip().lower()
    if key == "temp" or key == "temporary files":
        import tempfile
        return [tempfile.gettempdir()]
    rel_paths = KNOWN_CACHE_PATHS.get(key)
    if rel_paths is None:
        return []
    return [os.path.join(_user_home(), rel) for rel in rel_paths]


def preview_cache(app_name: str) -> dict:
    """Non-destructive: report what WOULD be cleared and its size, for
    building the Android approval-request description."""
    targets = resolve_cache_targets(app_name)
    existing = [t for t in targets if os.path.isdir(t)]
    if not existing:
        return {"success": False, "message": f"No known cache location found for '{app_name}'."}
    total = sum(estimate_size(t) for t in existing)
    return {
        "success": True,
        "message": f"Found cache for '{app_name}'.",
        "data": {"paths": existing, "estimated_size": total},
    }


def clear_cache(app_name: str) -> dict:
    """Actually deletes contents of known cache dirs only. Called after
    Guard + Android approval already cleared this HIGH risk action."""
    targets = resolve_cache_targets(app_name)
    existing = [t for t in targets if os.path.isdir(t)]
    if not existing:
        return {"success": False, "message": f"No known cache location found for '{app_name}'."}

    cleared_bytes = 0
    errors = []
    for path in existing:
        cleared_bytes += estimate_size(path)
        for entry in os.listdir(path):
            full = os.path.join(path, entry)
            try:
                if os.path.isdir(full):
                    shutil.rmtree(full)
                else:
                    os.remove(full)
            except OSError as exc:
                errors.append(str(exc))

    if errors and not cleared_bytes:
        return {"success": False, "message": f"Could not clear cache for '{app_name}': {errors[0]}"}

    mb = round(cleared_bytes / (1024 * 1024), 1)
    msg = f"Cleared ~{mb} MB of {app_name} cache."
    if errors:
        msg += f" ({len(errors)} item(s) could not be removed, likely in use.)"
    return {"success": True, "message": msg}
