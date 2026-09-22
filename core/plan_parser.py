"""
Structured action-plan parser and validator.

This is THE security boundary between "text Gemini produced" and
"actions the executor is allowed to run". Nothing from Gemini reaches
the executor without passing every check in here.

Rules enforced (see project spec section 8 & 34):
  - Gemini output must be valid JSON matching the action_plan schema.
  - Every action name must be in the supported-action whitelist.
  - Parameter types must match expectations (strings where strings are
    expected, no nested surprises).
  - risk is ALWAYS recomputed from our own ACTION_RISK table - Gemini's
    stated risk is advisory only and is never trusted.
  - Unknown actions are dropped, not executed and not silently upgraded.
  - Malformed plans raise PlanValidationError; callers must treat this
    as "could not understand the request", never as "run it anyway".
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.constants import SUPPORTED_ACTIONS, ACTION_RISK, ACTION_TARGET_FIELD
from core.models import Action, ActionPlan, new_request_id

log = logging.getLogger("chronix.plan_parser")


class PlanValidationError(Exception):
    """Raised when Gemini's output cannot be safely turned into a plan."""


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        # remove ```json ... ``` or ``` ... ``` wrapping defensively,
        # even though the API is asked for responseMimeType=json.
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    return t.strip()


def _validate_single_action(raw: dict, index: int) -> Action | None:
    if not isinstance(raw, dict):
        log.warning("Dropping non-object action at index %d", index)
        return None

    name = raw.get("action")
    if not isinstance(name, str) or name not in SUPPORTED_ACTIONS:
        log.warning("Dropping unsupported/unknown action %r at index %d", name, index)
        return None

    target = raw.get("target")
    expected_target_field = ACTION_TARGET_FIELD.get(name)
    if expected_target_field is not None:
        if target is not None and not isinstance(target, str):
            log.warning("Dropping action %r: target must be a string", name)
            return None
    else:
        # Action takes no target (e.g. shutdown) - ignore any provided value.
        target = None

    params = raw.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        log.warning("Dropping action %r: params must be an object", name)
        return None
    # Only allow flat, JSON-primitive param values - no nested objects/arrays
    # that could smuggle additional instructions through to a skill.
    safe_params = {}
    for k, v in params.items():
        if not isinstance(k, str):
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe_params[k] = v
        else:
            log.warning("Dropping non-primitive param %r for action %r", k, name)

    # Risk is ALWAYS taken from our own table - never from Gemini's output.
    risk = ACTION_RISK[name]

    return Action(action=name, target=target, params=safe_params, risk=risk)


def parse_action_plan(raw_text: str, request_id: str | None = None) -> ActionPlan:
    """Parse and validate raw Gemini text into an ActionPlan.

    Never raises anything except PlanValidationError. Actions that are
    individually invalid are dropped (logged) rather than aborting the
    whole plan, so one bad entry doesn't block the rest of a valid plan -
    but a plan that fails to parse as JSON at all is rejected outright.
    """
    request_id = request_id or new_request_id()
    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise PlanValidationError(f"Gemini output was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise PlanValidationError("Gemini output must be a JSON object")

    if data.get("type") != "action_plan":
        raise PlanValidationError("Gemini output missing type=action_plan")

    raw_actions = data.get("actions")
    if raw_actions is None:
        raw_actions = []
    if not isinstance(raw_actions, list):
        raise PlanValidationError("'actions' must be a JSON array")

    validated: list[Action] = []
    for i, raw_action in enumerate(raw_actions):
        action = _validate_single_action(raw_action, i)
        if action is not None:
            validated.append(action)

    return ActionPlan(request_id=request_id, actions=validated, raw_source=raw_text)
