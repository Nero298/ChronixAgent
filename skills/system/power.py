"""
Power and process control skills. These are all HIGH risk actions -
by the time this module is called, Guard + Android approval have
already cleared the request. This module does not re-check approval;
it trusts its caller (core.executor), which is only ever invoked after
the planner confirms approval for high-risk actions.
"""
from __future__ import annotations

import subprocess


def shutdown() -> dict:
    try:
        subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
    except FileNotFoundError:
        return {"success": False, "message": "'shutdown' command not found on this system."}
    except subprocess.CalledProcessError as exc:
        return {"success": False, "message": f"Shutdown command failed: {exc}"}
    return {"success": True, "message": "Shutting down in 5 seconds."}


def restart() -> dict:
    try:
        subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
    except FileNotFoundError:
        return {"success": False, "message": "'shutdown' command not found on this system."}
    except subprocess.CalledProcessError as exc:
        return {"success": False, "message": f"Restart command failed: {exc}"}
    return {"success": True, "message": "Restarting in 5 seconds."}


def terminate_process(target: str) -> dict:
    if not target:
        return {"success": False, "message": "No process name or PID was given."}
    args = ["taskkill", "/PID", target, "/F"] if target.isdigit() else ["taskkill", "/IM", target, "/F"]
    try:
        subprocess.run(args, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        return {"success": False, "message": "'taskkill' command not found on this system."}
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        return {"success": False, "message": f"Could not terminate '{target}': {stderr or exc}"}
    return {"success": True, "message": f"Terminated '{target}'."}
