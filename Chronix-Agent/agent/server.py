"""
Chronix Agent LAN server.

Uses Python's stdlib http.server rather than Flask/FastAPI to minimize
dependencies and memory footprint for Windows 7 / 2 GB RAM targets.
Event-driven per request (no polling loop for chat) - the only polling
in the process is the lightweight periodic sweep for expired approvals
and the discovery beacon, both on long intervals.

Endpoints (all POST, JSON body/response, see agent.protocol):
    /chat              -> MSG_CHAT
    /approval_response -> MSG_APPROVAL_RESPONSE
    /pair              -> MSG_PAIR_REQUEST
    /ping              -> MSG_PING
"""
from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import logging
import secrets
import socketserver
import threading
from typing import Optional

from agent import protocol
from agent.config import ChronixConfig
from agent.gemini import GeminiClient
from core.constants import (
    APPROVAL_DECISION_APPROVE, APPROVAL_DECISION_REJECT,
    MSG_CHAT, MSG_APPROVAL_RESPONSE, MSG_PAIR_REQUEST, MSG_PING,
    MSG_PENDING_APPROVALS_REQUEST,
)
from core.permissions import ApprovalManager
from core.planner import Planner
from core.security import ChronixGuard

log = logging.getLogger("chronix.server")


def _constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


class ChronixRequestHandler(http.server.BaseHTTPRequestHandler):
    # Injected by ChronixHTTPServer at construction time.
    server: "ChronixHTTPServer"

    def log_message(self, fmt, *args):  # silence default stderr logging; we use our own
        log.debug("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, envelope: protocol.Envelope) -> None:
        body = envelope.to_json().encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8") if length else "{}"

    def _authenticated(self, env: protocol.Envelope) -> bool:
        if not self.server.config.pairing_token:
            return True  # not yet paired / pairing disabled - dev mode only
        token = env.payload.get("token", "")
        return isinstance(token, str) and _constant_time_eq(token, self.server.config.pairing_token)

    def do_POST(self):  # noqa: N802 - stdlib naming convention
        raw = self._read_body()
        try:
            env = protocol.decode(raw)
        except protocol.ProtocolError as exc:
            self._send_json(400, protocol.make_error(None, str(exc)))
            return

        if env.type == MSG_PAIR_REQUEST:
            self._handle_pair(env)
            return

        if not self._authenticated(env):
            self._send_json(401, protocol.make_error(env.request_id, "unauthenticated"))
            return

        if env.type == MSG_CHAT:
            self._handle_chat(env)
        elif env.type == MSG_APPROVAL_RESPONSE:
            self._handle_approval_response(env)
        elif env.type == MSG_PENDING_APPROVALS_REQUEST:
            self._handle_pending_approvals(env)
        elif env.type == MSG_PING:
            self._send_json(200, protocol.make_pong(env.request_id))
        else:
            self._send_json(400, protocol.make_error(env.request_id, f"unsupported type: {env.type}"))

    def _handle_pending_approvals(self, env: protocol.Envelope) -> None:
        """Android polls this after a chat response mentions 'Approval
        required' to fetch full ApprovalRequest details for the dialog.
        Already-resolved or expired requests are not re-sent."""
        srv = self.server
        still_pending = [a for a in srv.pending_approvals_out
                          if not a.resolved and not a.is_expired()]
        srv.pending_approvals_out = still_pending
        self._send_json(200, protocol.make_pending_approvals_response(still_pending))

    def _handle_pair(self, env: protocol.Envelope) -> None:
        submitted_code = env.payload.get("pairing_code", "")
        srv = self.server
        if not srv.pending_pairing_code or not _constant_time_eq(
                str(submitted_code), srv.pending_pairing_code):
            self._send_json(200, protocol.make_pair_response(
                env.request_id, accepted=False, reason="invalid pairing code"))
            return
        token = secrets.token_hex(24)
        srv.config.pairing_token = token
        srv.pending_pairing_code = None  # one-time use
        log.info("Device paired successfully.")
        self._send_json(200, protocol.make_pair_response(env.request_id, accepted=True, token=token))

    def _handle_chat(self, env: protocol.Envelope) -> None:
        message = env.payload.get("message", "")
        if not isinstance(message, str) or not message.strip():
            self._send_json(400, protocol.make_error(env.request_id, "empty message"))
            return

        outcome = self.server.planner.handle_chat(message, request_id=env.request_id)
        self._send_json(200, protocol.make_chat_response(outcome.request_id, outcome.chat_message))

        # Any pending approvals are pushed as separate messages. In this
        # stdlib-server design without a persistent socket, Android is
        # expected to poll a lightweight /pending endpoint or use the
        # WebSocket variant (see README "Known limitations").
        for approval in outcome.pending_approvals:
            self.server.pending_approvals_out.append(approval)

    def _handle_approval_response(self, env: protocol.Envelope) -> None:
        request_id = env.payload.get("request_id") or env.request_id
        decision = env.payload.get("decision")
        if decision not in (APPROVAL_DECISION_APPROVE, APPROVAL_DECISION_REJECT):
            self._send_json(400, protocol.make_error(request_id, "decision must be approve/reject"))
            return
        if not request_id:
            self._send_json(400, protocol.make_error(None, "missing request_id"))
            return

        ok, message = self.server.approvals.resolve(request_id, decision)
        if not ok:
            self._send_json(409, protocol.make_error(request_id, message))
            return

        result = None
        if decision == APPROVAL_DECISION_APPROVE:
            result = self.server.planner.execute_after_approval(request_id)

        if result is not None:
            self._send_json(200, protocol.make_action_result(result))
        else:
            from core.models import ActionResult
            outcome_msg = "Action rejected." if decision == APPROVAL_DECISION_REJECT else "Action cancelled."
            self._send_json(200, protocol.make_action_result(
                ActionResult(request_id, False, outcome_msg)))


class ChronixHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

    def __init__(self, config: ChronixConfig):
        super().__init__(("0.0.0.0", config.server_port), ChronixRequestHandler)
        self.config = config
        self.approvals = ApprovalManager()
        self.guard = ChronixGuard(require_approval_for_medium=config.require_approval_for_medium)
        gemini_client: Optional[GeminiClient] = None
        if config.gemini_api_key:
            gemini_client = GeminiClient(config.gemini_api_key, model=config.gemini_model)
        else:
            log.warning("No Gemini API key configured - chat will report AI unavailable.")
        self.planner = Planner(gemini_client, self.guard, self.approvals)
        self.pending_pairing_code: Optional[str] = None
        self.pending_approvals_out: list = []

    def generate_pairing_code(self) -> str:
        code = f"{secrets.randbelow(1_000_000):06d}"
        self.pending_pairing_code = code
        return code


def run_server(config: ChronixConfig) -> ChronixHTTPServer:
    server = ChronixHTTPServer(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="chronix-http")
    thread.start()
    log.info("Chronix Agent server listening on port %d", config.server_port)
    return server
