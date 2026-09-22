"""
Approval manager.

Tracks pending ApprovalRequest objects awaiting an Android decision.
Enforces (spec section 11):
  - decisions must match an exact, still-pending request_id
  - a generic "approve" with no/mismatched request_id does nothing
  - expired requests can no longer be approved
  - a request can only be resolved once (no double execution from
    duplicate network messages)
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

from core.constants import APPROVAL_TIMEOUT_SECONDS, APPROVAL_DECISION_APPROVE
from core.models import ApprovalRequest, Action

log = logging.getLogger("chronix.permissions")


class ApprovalManager:
    def __init__(self, timeout_seconds: int = APPROVAL_TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds
        self._pending: dict[str, ApprovalRequest] = {}
        self._lock = threading.Lock()

    def create(self, action: Action, description: str,
               estimated_size: Optional[int] = None,
               request_id: Optional[str] = None) -> ApprovalRequest:
        from core.models import new_request_id
        rid = request_id or new_request_id()
        now = time.time()
        req = ApprovalRequest(
            request_id=rid,
            action=action,
            description=description,
            estimated_size=estimated_size,
            created_at=now,
            expires_at=now + self.timeout_seconds,
        )
        with self._lock:
            self._pending[rid] = req
        log.info("Approval request %s created for action=%s target=%s",
                  rid, action.action, action.target)
        return req

    def resolve(self, request_id: str, decision: str) -> tuple[bool, str]:
        """Apply an Android decision to a pending request.

        Returns (ok, message). ok=False covers: unknown request_id,
        already-resolved request, or expired request. Only ever mutates
        state for an exact, still-pending, non-expired match.
        """
        with self._lock:
            req = self._pending.get(request_id)
            if req is None:
                log.warning("Approval response for unknown request_id=%s ignored", request_id)
                return False, "unknown or already-completed request_id"

            if req.resolved:
                log.warning("Duplicate approval response for request_id=%s ignored", request_id)
                return False, "request already resolved"

            if req.is_expired():
                req.resolved = True
                req.decision = "expired"
                log.info("Approval request %s expired before decision arrived", request_id)
                return False, "request expired"

            req.resolved = True
            req.decision = decision
            log.info("Approval request %s resolved: %s", request_id, decision)
            return True, "ok"

    def get(self, request_id: str) -> Optional[ApprovalRequest]:
        with self._lock:
            return self._pending.get(request_id)

    def sweep_expired(self) -> list[str]:
        """Mark timed-out requests as expired/cancelled. Call periodically."""
        expired_ids = []
        with self._lock:
            for rid, req in self._pending.items():
                if not req.resolved and req.is_expired():
                    req.resolved = True
                    req.decision = "expired"
                    expired_ids.append(rid)
        for rid in expired_ids:
            log.info("Approval request %s expired (timeout)", rid)
        return expired_ids

    def is_approved(self, request_id: str) -> bool:
        req = self.get(request_id)
        return bool(req and req.resolved and req.decision == APPROVAL_DECISION_APPROVE
                    and not req.is_expired())
