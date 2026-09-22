"""
Executor.

Dispatches a validated Action (already passed through plan_parser and
ChronixGuard, and - if high/medium+policy risk - already approved) to
the concrete skill implementation. This module assumes the action has
ALREADY been cleared; it does not re-run risk checks, but it does do
its own defensive error handling so a skill failure never crashes the
agent (spec section 30).

Only actions in core.constants.SUPPORTED_ACTIONS are dispatchable.
Anything else raises immediately - that should be unreachable if the
pipeline upstream is correct, so treat it as a bug, not user input.
"""
from __future__ import annotations

import logging

from core.constants import (
    ACTION_OPEN_APP, ACTION_OPEN_BROWSER, ACTION_OPEN_URL,
    ACTION_GET_SYSTEM_INFO, ACTION_LIST_FILES, ACTION_SEARCH_FILES,
    ACTION_GET_FILE_INFO, ACTION_CREATE_FILE, ACTION_EDIT_FILE,
    ACTION_CREATE_DIRECTORY, ACTION_MOVE_FILE, ACTION_COPY_FILE,
    ACTION_RENAME_FILE, ACTION_RUN_LIMITED_COMMAND, ACTION_DELETE_FILE,
    ACTION_DELETE_DIRECTORY, ACTION_CLEAR_CACHE, ACTION_CLEAR_APP_DATA,
    ACTION_SHUTDOWN, ACTION_RESTART, ACTION_TERMINATE_PROCESS,
    ACTION_MASS_FILE_OPERATION,
)
from core.models import Action, ActionResult

log = logging.getLogger("chronix.executor")


class UnimplementedAction(Exception):
    pass


def execute(action: Action, request_id: str) -> ActionResult:
    """Dispatch a single cleared Action. Never raises - always returns
    an ActionResult, converting any skill-level exception into a
    human-readable failure message."""
    try:
        handler = _DISPATCH.get(action.action)
        if handler is None:
            return ActionResult(request_id, False,
                                 f"Action '{action.action}' is not yet implemented on this build.")
        result = handler(action)
        return ActionResult(request_id, result.get("success", False),
                             result.get("message", ""), result.get("data", {}))
    except Exception as exc:  # noqa: BLE001 - last line of defense, spec section 30
        log.exception("Unhandled error executing action %s", action.action)
        return ActionResult(request_id, False,
                             f"'{action.action}' failed due to an internal error: {exc}")


# --- Handlers -----------------------------------------------------------
# Each handler takes an Action and returns {"success": bool, "message": str,
# optionally "data": dict}. Kept as thin adapters so skill modules stay
# independently testable.

def _open_app(action: Action) -> dict:
    from skills.apps.launcher import open_app
    return open_app(action.target or "")


def _open_browser(action: Action) -> dict:
    from skills.browser.browser import open_browser
    return open_browser(action.target)


def _open_url(action: Action) -> dict:
    from skills.browser.browser import open_url
    return open_url(action.target or "")


def _get_system_info(action: Action) -> dict:
    from skills.system.info import get_system_info
    return get_system_info()


def _list_files(action: Action) -> dict:
    from skills.files.fileops import list_files
    return list_files(action.target or ".")


def _search_files(action: Action) -> dict:
    from skills.files.fileops import search_files
    pattern = action.params.get("pattern", "*")
    return search_files(action.target or ".", pattern)


def _get_file_info(action: Action) -> dict:
    from skills.files.fileops import get_file_info
    return get_file_info(action.target or "")


def _create_file(action: Action) -> dict:
    from skills.files.fileops import create_file
    content = action.params.get("content", "")
    return create_file(action.target or "", content)


def _create_directory(action: Action) -> dict:
    from skills.files.fileops import create_directory
    return create_directory(action.target or "")


def _move_file(action: Action) -> dict:
    from skills.files.fileops import move_file
    dest = action.params.get("destination", "")
    return move_file(action.target or "", dest)


def _copy_file(action: Action) -> dict:
    from skills.files.fileops import copy_file
    dest = action.params.get("destination", "")
    return copy_file(action.target or "", dest)


def _rename_file(action: Action) -> dict:
    from skills.files.fileops import rename_file
    new_name = action.params.get("new_name", "")
    return rename_file(action.target or "", new_name)


def _delete_file(action: Action) -> dict:
    from skills.files.fileops import delete_file
    return delete_file(action.target or "")


def _delete_directory(action: Action) -> dict:
    from skills.files.fileops import delete_directory
    return delete_directory(action.target or "")


def _clear_cache(action: Action) -> dict:
    from skills.cleanup.cleanup import clear_cache
    return clear_cache(action.target or "")


def _shutdown(action: Action) -> dict:
    from skills.system.power import shutdown
    return shutdown()


def _restart(action: Action) -> dict:
    from skills.system.power import restart
    return restart()


def _terminate_process(action: Action) -> dict:
    from skills.system.power import terminate_process
    return terminate_process(action.target or "")


_DISPATCH = {
    ACTION_OPEN_APP: _open_app,
    ACTION_OPEN_BROWSER: _open_browser,
    ACTION_OPEN_URL: _open_url,
    ACTION_GET_SYSTEM_INFO: _get_system_info,
    ACTION_LIST_FILES: _list_files,
    ACTION_SEARCH_FILES: _search_files,
    ACTION_GET_FILE_INFO: _get_file_info,
    ACTION_CREATE_FILE: _create_file,
    ACTION_CREATE_DIRECTORY: _create_directory,
    ACTION_MOVE_FILE: _move_file,
    ACTION_COPY_FILE: _copy_file,
    ACTION_RENAME_FILE: _rename_file,
    ACTION_DELETE_FILE: _delete_file,
    ACTION_DELETE_DIRECTORY: _delete_directory,
    ACTION_CLEAR_CACHE: _clear_cache,
    ACTION_SHUTDOWN: _shutdown,
    ACTION_RESTART: _restart,
    ACTION_TERMINATE_PROCESS: _terminate_process,
    # ACTION_EDIT_FILE, ACTION_RUN_LIMITED_COMMAND, ACTION_CLEAR_APP_DATA,
    # ACTION_MASS_FILE_OPERATION intentionally not yet wired - see README
    # "Known limitations". They are recognized by the guard/parser but
    # return "not yet implemented" until scoped carefully (especially
    # run_limited_command, which needs a hard per-command whitelist
    # before it should ever execute anything).
}
