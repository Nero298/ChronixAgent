"""
Planner - the orchestration hub.

Flow (spec section 1 / 34):
    natural language (from Android)
        -> Gemini (agent.gemini)
        -> structured plan (core.plan_parser)
        -> per-action Guard evaluation (core.security)
        -> low risk / allowed medium risk -> execute immediately
        -> requires approval -> create ApprovalRequest, return it to caller
           (caller/server.py sends it to Android and waits)
    Once Android approves (core.permissions.ApprovalManager.resolve):
        -> execute immediately
    Once Android rejects or it expires:
        -> never execute, report cancellation

This module never executes an action Guard didn't clear, and never
executes a high-risk action without ApprovalManager confirming it was
actually approved (not just "not yet rejected").
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Union

from agent.gemini import GeminiClient, GeminiError
from core.executor import execute
from core.models import Action, ActionResult, ApprovalRequest, new_request_id
from core.permissions import ApprovalManager
from core.plan_parser import parse_action_plan, PlanValidationError
from core.security import ChronixGuard

log = logging.getLogger("chronix.planner")


@dataclass
class PlannerOutcome:
    """What the caller (server.py) should do next."""
    request_id: str
    chat_message: str
    results: list[ActionResult]
    pending_approvals: list[ApprovalRequest]


class Planner:
    def __init__(self, gemini_client: Optional[GeminiClient], guard: ChronixGuard,
                 approvals: ApprovalManager):
        self.gemini_client = gemini_client
        self.guard = guard
        self.approvals = approvals

    def handle_chat(self, user_message: str, request_id: Optional[str] = None) -> PlannerOutcome:
        request_id = request_id or new_request_id()

        if self.gemini_client is None:
            return PlannerOutcome(
                request_id,
                "AI is unavailable right now (Gemini API is not configured). "
                "Basic actions still work if you name them directly.",
                [], [],
            )

        try:
            raw_text = self.gemini_client.generate_action_plan_text(user_message)
        except GeminiError as exc:
            log.warning("Gemini unavailable: %s", exc)
            return PlannerOutcome(request_id, f"AI is unavailable right now: {exc}", [], [])

        try:
            plan = parse_action_plan(raw_text, request_id=request_id)
        except PlanValidationError as exc:
            log.warning("Plan validation failed: %s", exc)
            return PlannerOutcome(
                request_id,
                "I couldn't turn that into a safe action plan, so nothing was executed.",
                [], [],
            )

        if not plan.actions:
            return PlannerOutcome(request_id, "I didn't find anything actionable in that request.",
                                   [], [])

        return self._process_actions(plan.actions, request_id)

    def _process_actions(self, actions: list[Action], request_id: str) -> PlannerOutcome:
        results: list[ActionResult] = []
        pending: list[ApprovalRequest] = []

        for action in actions:
            verdict = self.guard.evaluate(action)
            if not verdict.allowed:
                results.append(ActionResult(request_id, False, f"Blocked: {verdict.reason}"))
                continue

            if verdict.requires_approval:
                description = self._describe(action)
                estimated_size = self._estimate_size_if_relevant(action)
                approval = self.approvals.create(
                    action, description, estimated_size=estimated_size, request_id=None,
                )
                pending.append(approval)
                continue

            results.append(execute(action, request_id))

        summary = self._summarize(results, pending)
        return PlannerOutcome(request_id, summary, results, pending)

    def execute_after_approval(self, approval_request_id: str) -> Optional[ActionResult]:
        """Call after ApprovalManager.resolve() confirms an approval.

        Returns None if the request isn't actually in an approved state -
        callers must treat None as "do not execute".
        """
        if not self.approvals.is_approved(approval_request_id):
            log.warning("Refusing to execute %s: not in approved state", approval_request_id)
            return None
        req = self.approvals.get(approval_request_id)
        if req is None:
            return None
        return execute(req.action, approval_request_id)

    @staticmethod
    def _describe(action: Action) -> str:
        return f"{action.action.replace('_', ' ').title()}: {action.target or '(no target)'}"

    @staticmethod
    def _estimate_size_if_relevant(action: Action) -> Optional[int]:
        from core.constants import ACTION_DELETE_FILE, ACTION_DELETE_DIRECTORY, ACTION_CLEAR_CACHE
        if action.action in (ACTION_DELETE_FILE, ACTION_DELETE_DIRECTORY):
            from skills.files.fileops import estimate_size
            return estimate_size(action.target or "")
        if action.action == ACTION_CLEAR_CACHE:
            from skills.cleanup.cleanup import preview_cache
            preview = preview_cache(action.target or "")
            return preview.get("data", {}).get("estimated_size")
        return None

    @staticmethod
    def _summarize(results: list[ActionResult], pending: list[ApprovalRequest]) -> str:
        parts = []
        for r in results:
            parts.append(r.message)
        for p in pending:
            parts.append(f"Approval required: {p.description}")
        return " ".join(parts) if parts else "Nothing to do."
