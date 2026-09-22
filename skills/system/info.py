"""
Lightweight system-info skill. Avoids heavy dependencies (no psutil
requirement forced) - falls back gracefully if it's not installed.
"""
from __future__ import annotations

import platform


def get_system_info() -> dict:
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    try:
        import psutil  # optional dependency
        info["ram_total_mb"] = round(psutil.virtual_memory().total / (1024 * 1024))
        info["ram_available_mb"] = round(psutil.virtual_memory().available / (1024 * 1024))
        info["cpu_percent"] = psutil.cpu_percent(interval=0.2)
    except ImportError:
        pass
    return {"success": True, "message": "System info retrieved.", "data": info}
