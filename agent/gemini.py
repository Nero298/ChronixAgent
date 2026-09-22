"""
Gemini client for Chronix Agent.

Responsibilities:
  - Build a system prompt that forces Gemini to emit ONLY a JSON action
    plan matching our schema (never free-form text that gets executed).
  - Call the Gemini API over HTTPS (no SDK dependency required - plain
    `requests`/`urllib` call, kept light for Windows 7 packaging).
  - Hand the raw text response to core.plan_parser for strict validation.

SECURITY NOTE: this module NEVER executes anything. It only produces an
unvalidated ActionPlan (or raises GeminiError). core.plan_parser and
core.security/guard are what stand between this output and the executor.
The Gemini API key lives only here on the Windows agent; it is never
sent to Android and never embedded in the APK.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Optional

from core.constants import SUPPORTED_ACTIONS, ALL_RISK_LEVELS

log = logging.getLogger("chronix.gemini")

DEFAULT_MODEL = "gemini-2.0-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT_SECONDS = 20


class GeminiError(Exception):
    """Raised when Gemini is unavailable or returns something unusable.

    Callers (planner) MUST catch this and report 'AI unavailable' rather
    than falling back to any kind of unrestricted execution.
    """


SYSTEM_PROMPT_TEMPLATE = """You are the planning module inside Chronix Agent, a Windows automation \
assistant. You do NOT execute anything yourself. Your ONLY job is to convert the user's \
natural-language request into a JSON action plan using EXACTLY this schema and nothing else:

{{
  "type": "action_plan",
  "actions": [
    {{"action": "<one of: {actions}>", "target": "<string or null>", "params": {{}}, "risk": "<low|medium|high>"}}
  ]
}}

Rules:
- Output ONLY the JSON object. No prose, no markdown fences, no explanation.
- "action" MUST be one of the supported action names listed above. If the request does not map to \
any supported action, return {{"type": "action_plan", "actions": []}}.
- "risk" MUST be exactly the risk level Chronix already assigns to that action; you are not the \
security authority, so use your best judgement but the agent will re-verify and override risk anyway.
- Never invent new action names.
- Never ask the user a follow-up question - if information is missing, choose the most reasonable \
interpretation or omit the action.
- Paths should be given as literally as the user implied; do not assume a path exists.
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(actions=", ".join(sorted(SUPPORTED_ACTIONS)))


class GeminiClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise GeminiError("Gemini API key is not configured")
        self.api_key = api_key
        self.model = model

    def _endpoint(self) -> str:
        return f"{API_BASE}/{self.model}:generateContent?key={self.api_key}"

    def generate_action_plan_text(self, user_message: str) -> str:
        """Call Gemini and return the raw text of its response.

        Raises GeminiError on any network/API failure. Does not parse or
        validate JSON - that is core.plan_parser's job.
        """
        body = {
            "systemInstruction": {"parts": [{"text": build_system_prompt()}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint(),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            log.error("Gemini HTTP error %s: %s", exc.code, detail[:300])
            raise GeminiError(f"Gemini API returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            log.error("Gemini network error: %s", exc.reason)
            raise GeminiError("Gemini API unreachable (network error)") from exc
        except TimeoutError as exc:
            log.error("Gemini request timed out")
            raise GeminiError("Gemini API request timed out") from exc

        try:
            envelope = json.loads(raw)
            text = envelope["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            log.error("Unexpected Gemini response shape: %s", raw[:300])
            raise GeminiError("Gemini API returned an unexpected response shape") from exc

        return text
