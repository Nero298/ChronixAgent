"""
Data models for Chronix Agent.

Plain dataclasses (no pydantic dependency) to keep the runtime light
enough for Windows 7 / 2 GB RAM targets.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from core.constants import ALL_RISK_LEVELS


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Action:
    """A single validated action to execute."""
    action: str
    target: Optional[str] = None
    params: dict = field(default_factory=dict)
    risk: str = "low"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActionPlan:
    """A parsed, not-yet-validated action plan from Gemini."""
    request_id: str
    actions: list[Action]
    raw_source: str = ""  # original Gemini text, for logging/debugging only

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class ApprovalRequest:
    """A pending high-risk action awaiting Android approval."""
    request_id: str
    action: Action
    description: str
    estimated_size: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    resolved: bool = False
    decision: Optional[str] = None  # "approve" | "reject" | None

    def is_expired(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        return now >= self.expires_at

    def to_wire_dict(self) -> dict:
        """Shape sent to Android (see protocol.py MSG_APPROVAL_REQUEST)."""
        return {
            "request_id": self.request_id,
            "action": self.action.action,
            "target": self.action.target,
            "risk": self.action.risk,
            "description": self.description,
            "estimated_size": self.estimated_size,
        }


@dataclass
class ActionResult:
    request_id: str
    success: bool
    message: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def validate_risk(risk: str) -> str:
    if risk not in ALL_RISK_LEVELS:
        raise ValueError(f"Invalid risk level: {risk!r}")
    return risk
