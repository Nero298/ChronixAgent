"""
File operation skills.

Every function here normalizes and checks paths via core.security
independently, even though Guard already checked delete-class actions
upstream - defense in depth (spec section 12/34). Never raises; always
returns a {"success", "message", "data"} dict.
"""
from __future__ import annotations

import glob
import os
import shutil

from core.security import normalize_path, is_protected_path


def _err(message: str) -> dict:
    return {"success": False, "message": message}


def _ok(message: str, **data) -> dict:
    return {"success": True, "message": message, "data": data}


def list_files(target: str) -> dict:
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No path was given.")
    if not os.path.isdir(path):
        return _err(f"'{path}' is not a directory or does not exist.")
    try:
        entries = os.listdir(path)
    except PermissionError:
        return _err(f"Permission denied reading '{path}'.")
    return _ok(f"{len(entries)} item(s) in '{path}'.", entries=entries[:500])


def search_files(target: str, pattern: str) -> dict:
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No path was given.")
    if not os.path.isdir(path):
        return _err(f"'{path}' is not a directory or does not exist.")
    matches = glob.glob(os.path.join(path, "**", pattern or "*"), recursive=True)
    return _ok(f"Found {len(matches)} match(es).", matches=matches[:500])


def get_file_info(target: str) -> dict:
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No path was given.")
    if not os.path.exists(path):
        return _err(f"'{path}' does not exist.")
    st = os.stat(path)
    return _ok(f"Info for '{path}'.", size=st.st_size, is_dir=os.path.isdir(path),
               modified=st.st_mtime)


def create_file(target: str, content: str) -> dict:
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No file path was given.")
    if is_protected_path(path):
        return _err(f"Refusing to write to protected location '{path}'.")
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")
    except OSError as exc:
        return _err(f"Could not create '{path}': {exc}")
    return _ok(f"Created file '{path}'.")


def create_directory(target: str) -> dict:
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No directory path was given.")
    if is_protected_path(path):
        return _err(f"Refusing to create a directory at protected location '{path}'.")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        return _err(f"Could not create directory '{path}': {exc}")
    return _ok(f"Created directory '{path}'.")


def move_file(target: str, destination: str) -> dict:
    try:
        src = normalize_path(target)
        dst = normalize_path(destination)
    except ValueError:
        return _err("Source or destination path was missing.")
    if is_protected_path(src) or is_protected_path(dst):
        return _err("Refusing to move to/from a protected system location.")
    if not os.path.exists(src):
        return _err(f"'{src}' does not exist.")
    try:
        shutil.move(src, dst)
    except OSError as exc:
        return _err(f"Could not move '{src}' to '{dst}': {exc}")
    return _ok(f"Moved '{src}' to '{dst}'.")


def copy_file(target: str, destination: str) -> dict:
    try:
        src = normalize_path(target)
        dst = normalize_path(destination)
    except ValueError:
        return _err("Source or destination path was missing.")
    if is_protected_path(dst):
        return _err("Refusing to copy into a protected system location.")
    if not os.path.exists(src):
        return _err(f"'{src}' does not exist.")
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    except OSError as exc:
        return _err(f"Could not copy '{src}' to '{dst}': {exc}")
    return _ok(f"Copied '{src}' to '{dst}'.")


def rename_file(target: str, new_name: str) -> dict:
    try:
        src = normalize_path(target)
    except ValueError:
        return _err("No path was given.")
    if not new_name or os.sep in new_name or "/" in new_name:
        return _err("New name must be a plain filename, not a path.")
    dst = os.path.join(os.path.dirname(src), new_name)
    if is_protected_path(src) or is_protected_path(dst):
        return _err("Refusing to rename in a protected system location.")
    if not os.path.exists(src):
        return _err(f"'{src}' does not exist.")
    try:
        os.rename(src, dst)
    except OSError as exc:
        return _err(f"Could not rename '{src}': {exc}")
    return _ok(f"Renamed '{src}' to '{dst}'.")


def delete_file(target: str) -> dict:
    """Called only after Guard + Android approval already cleared this."""
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No path was given.")
    if is_protected_path(path):
        return _err(f"Refusing to delete protected location '{path}'.")
    if not os.path.isfile(path):
        return _err(f"'{path}' is not a file or does not exist.")
    try:
        os.remove(path)
    except OSError as exc:
        return _err(f"Could not delete '{path}': {exc}")
    return _ok(f"Deleted file '{path}'.")


def delete_directory(target: str) -> dict:
    """Called only after Guard + Android approval already cleared this."""
    try:
        path = normalize_path(target)
    except ValueError:
        return _err("No path was given.")
    if is_protected_path(path):
        return _err(f"Refusing to delete protected location '{path}'.")
    if not os.path.isdir(path):
        return _err(f"'{path}' is not a directory or does not exist.")
    try:
        shutil.rmtree(path)
    except OSError as exc:
        return _err(f"Could not delete directory '{path}': {exc}")
    return _ok(f"Deleted directory '{path}'.")


def estimate_size(target: str) -> int:
    """Best-effort recursive size, used for approval-request previews."""
    try:
        path = normalize_path(target)
    except ValueError:
        return 0
    total = 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total
