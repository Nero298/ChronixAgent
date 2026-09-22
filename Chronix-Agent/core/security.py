"""
Chronix Guard - the risk/permission enforcement layer.

Nothing in the executor runs without first passing through
Guard.evaluate(). This module never trusts:
  - Gemini's stated risk level (plan_parser already recomputed it, but
    Guard re-derives path-based risk escalation independently anyway)
  - the absence of a path traversal attempt just because the string
    "looks fine"

Design principle (spec section 34): defense in depth. Even if
plan_parser had a bug, Guard is a second independent check.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from core.constants import (
    RISK_LOW, RISK_MEDIUM, RISK_HIGH,
    ACTION_DELETE_FILE, ACTION_DELETE_DIRECTORY, ACTION_MASS_FILE_OPERATION,
    PROTECTED_PATH_FRAGMENTS,
)
from core.models import Action

log = logging.getLogger("chronix.guard")


class GuardDenied(Exception):
    """Raised when Guard permanently blocks an action (not just 'needs approval')."""


@dataclass
class GuardVerdict:
    allowed: bool
    requires_approval: bool
    reason: str = ""


def _is_root_of_drive(path: PureWindowsPath) -> bool:
    # e.g. "C:\\" or "C:/" - anchor with nothing else beneath it.
    return path.drive != "" and str(path) == path.anchor


def is_protected_path(raw_path: str) -> bool:
    """Return True if raw_path touches a critical OS location.

    Uses PureWindowsPath so this logic is testable on non-Windows CI
    runners too, independent of the host OS running this code.
    """
    if not raw_path:
        return False

    try:
        normalized = PureWindowsPath(raw_path)
    except Exception:
        # Unparseable path is treated as suspicious -> protected.
        return True

    if _is_root_of_drive(normalized):
        return True

    lower = str(normalized).lower()

    # Reject path-traversal attempts outright.
    if ".." in Path(raw_path).parts:
        return True

    for fragment in PROTECTED_PATH_FRAGMENTS:
        if fragment in lower:
            return True

    return False


def normalize_path(raw_path: str) -> str:
    """Resolve to an absolute, normalized path string without touching disk.

    Raises ValueError for empty/invalid input. Callers should catch this
    and reject the action with a clear message rather than propagating
    a raw exception to Android.
    """
    if not raw_path or not raw_path.strip():
        raise ValueError("empty path")
    p = PureWindowsPath(os.path.normpath(raw_path))
    return str(p)


class ChronixGuard:
    """Evaluates a validated Action and decides: allow / require approval / deny."""

    def __init__(self, require_approval_for_medium: bool = False):
        self.require_approval_for_medium = require_approval_for_medium

    def evaluate(self, action: Action) -> GuardVerdict:
        # 1. Path safety, independent of risk level, for any action with a target
        #    that looks like a filesystem path.
        if action.target and action.action in (
            ACTION_DELETE_FILE, ACTION_DELETE_DIRECTORY, ACTION_MASS_FILE_OPERATION,
        ):
            try:
                normalized = normalize_path(action.target)
            except ValueError:
                return GuardVerdict(False, False, "invalid or empty path")

            if is_protected_path(normalized):
                return GuardVerdict(
                    False, False,
                    f"refused: '{normalized}' is a protected system location",
                )
            action.target = normalized  # write back normalized form

        # 2. Risk-based policy.
        if action.risk == RISK_LOW:
            return GuardVerdict(True, False, "low risk - auto-approved")

        if action.risk == RISK_MEDIUM:
            if self.require_approval_for_medium:
                return GuardVerdict(True, True, "medium risk - approval required by policy")
            return GuardVerdict(True, False, "medium risk - allowed by policy")

        if action.risk == RISK_HIGH:
            return GuardVerdict(True, True, "high risk - approval always required")

        # Unknown risk value should never happen (ACTION_RISK table is authoritative)
        # but fail closed if it somehow does.
        return GuardVerdict(False, False, f"unrecognized risk level {action.risk!r}")
