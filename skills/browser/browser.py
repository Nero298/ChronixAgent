"""
Browser skills: open default browser, open a specific known browser, open a URL.

Kept intentionally simple per spec section 15 - no browser automation.
"""
from __future__ import annotations

import shutil
import subprocess
import webbrowser

# Minimal known-site shorthand resolution, e.g. "youtube" -> full URL.
# This is NOT exhaustive; it just avoids failing on very common asks.
KNOWN_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "facebook": "https://www.facebook.com",
    "github": "https://www.github.com",
}


def _resolve_url(text: str) -> str:
    t = (text or "").strip()
    lower = t.lower()
    if lower in KNOWN_SITES:
        return KNOWN_SITES[lower]
    if t.startswith("http://") or t.startswith("https://"):
        return t
    if "." in t and " " not in t:
        return f"https://{t}"
    # Fall back to a web search for anything we can't resolve confidently.
    return f"https://www.google.com/search?q={t.replace(' ', '+')}"


def open_url(target: str) -> dict:
    if not target:
        return {"success": False, "message": "No URL or site name was given."}
    url = _resolve_url(target)
    try:
        opened = webbrowser.open(url)
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "message": f"Could not open browser: {exc}"}
    if not opened:
        return {"success": False, "message": "No browser is available to open the URL."}
    return {"success": True, "message": f"Opening {url}."}


def open_browser(target: str | None) -> dict:
    """Open a specific browser by name, or the system default if none given."""
    if not target:
        try:
            webbrowser.open("about:blank")
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "message": f"Could not open the default browser: {exc}"}
        return {"success": True, "message": "Opening default browser."}

    known_exes = {
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "msedge": "msedge.exe",
        "firefox": "firefox.exe",
    }
    exe = known_exes.get(target.lower())
    if not exe:
        return {"success": False, "message": f"'{target}' is not a recognized browser."}

    resolved = shutil.which(exe)
    try:
        subprocess.Popen(resolved or exe, shell=False)
    except FileNotFoundError:
        return {"success": False,
                "message": f"'{target}' could not be opened because it was not found on this PC."}
    except OSError as exc:
        return {"success": False, "message": f"Failed to open '{target}': {exc}"}
    return {"success": True, "message": f"Opening {target}."}
