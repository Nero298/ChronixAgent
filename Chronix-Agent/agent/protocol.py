"""
Chronix Agent communication protocol.

Defines the JSON message envelope shared between Android and the Windows
agent, and encode/decode helpers. All message "type" strings come from
core.constants - never hardcode them elsewhere.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from core.constants import (
    MSG_CHAT, MSG_CHAT_RESPONSE, MSG_APPROVAL_REQUEST, MSG_APPROVAL_RESPONSE,
    MSG_ACTION_RESULT, MSG_PAIR_REQUEST, MSG_PAIR_RESPONSE, MSG_PING, MSG_PONG,
    MSG_ERROR, VERSION, MSG_PENDING_APPROVALS_REQUEST, MSG_PENDING_APPROVALS_RESPONSE,
)

KNOWN_MESSAGE_TYPES = frozenset({
    MSG_CHAT, MSG_CHAT_RESPONSE, MSG_APPROVAL_REQUEST, MSG_APPROVAL_RESPONSE,
    MSG_ACTION_RESULT, MSG_PAIR_REQUEST, MSG_PAIR_RESPONSE, MSG_PING, MSG_PONG,
    MSG_ERROR, MSG_PENDING_APPROVALS_REQUEST, MSG_PENDING_APPROVALS_RESPONSE,
})


class ProtocolError(Exception):
    """Raised on malformed or unrecognized protocol messages."""


@dataclass
class Envelope:
    type: str
    request_id: Optional[str]
    payload: dict

    def to_json(self) -> str:
        body = {"type": self.type, "request_id": self.request_id}
        body.update(self.payload)
        return json.dumps(body, ensure_ascii=False)


def decode(raw: str) -> Envelope:
    """Parse and minimally validate a raw JSON protocol message.

    Raises ProtocolError on anything malformed. Never raises a bare
    exception up to the caller - callers should catch ProtocolError and
    respond with MSG_ERROR rather than crashing the connection handler.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProtocolError("message must be a JSON object")

    msg_type = data.get("type")
    if not isinstance(msg_type, str) or msg_type not in KNOWN_MESSAGE_TYPES:
        raise ProtocolError(f"unknown or missing message type: {msg_type!r}")

    request_id = data.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise ProtocolError("request_id must be a string or null")

    payload = {k: v for k, v in data.items() if k not in ("type", "request_id")}
    return Envelope(type=msg_type, request_id=request_id, payload=payload)


def make_chat_response(request_id: str, message: str) -> Envelope:
    return Envelope(MSG_CHAT_RESPONSE, request_id, {"message": message})


def make_approval_request(approval) -> Envelope:
    """approval: core.models.ApprovalRequest"""
    return Envelope(MSG_APPROVAL_REQUEST, approval.request_id, approval.to_wire_dict())


def make_action_result(result) -> Envelope:
    """result: core.models.ActionResult"""
    return Envelope(MSG_ACTION_RESULT, result.request_id, {
        "success": result.success,
        "message": result.message,
        "data": result.data,
    })


def make_error(request_id: Optional[str], message: str) -> Envelope:
    return Envelope(MSG_ERROR, request_id, {"message": message})


def make_pong(request_id: Optional[str]) -> Envelope:
    return Envelope(MSG_PONG, request_id, {"version": VERSION})


def make_pair_response(request_id: Optional[str], accepted: bool, token: Optional[str] = None,
                        reason: str = "") -> Envelope:
    payload: dict[str, Any] = {"accepted": accepted}
    if token:
        payload["token"] = token
    if reason:
        payload["reason"] = reason
    return Envelope(MSG_PAIR_RESPONSE, request_id, payload)


def make_pending_approvals_response(approvals: list) -> Envelope:
    """approvals: list[core.models.ApprovalRequest]"""
    return Envelope(MSG_PENDING_APPROVALS_RESPONSE, None, {
        "approvals": [a.to_wire_dict() for a in approvals],
    })
