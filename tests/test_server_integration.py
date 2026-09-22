"""
Integration test: spins up the real ChronixHTTPServer on a local port and
exercises it over actual HTTP, proving the wire format matches what the
Android client (network/ChronixApiClient.kt) expects to parse.
"""
import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from agent.config import ChronixConfig
from agent.server import ChronixHTTPServer
from core.models import Action

TEST_PORT = 18777


class TestServerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = ChronixConfig(
            device_name="Test-PC", server_port=TEST_PORT, gemini_api_key="",
            require_approval_for_medium=False, pairing_token="",
        )
        cls.server = ChronixHTTPServer(cfg)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    @staticmethod
    def post(body):
        req = urllib.request.Request(
            f"http://127.0.0.1:{TEST_PORT}/",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def test_chat_without_gemini_reports_unavailable(self):
        status, body = self.post({"type": "chat", "request_id": "r1", "message": "open chrome"})
        self.assertEqual(status, 200)
        self.assertIn("unavailable", body["message"].lower())

    def test_ping_pong(self):
        status, body = self.post({"type": "ping", "request_id": "r2"})
        self.assertEqual(status, 200)
        self.assertEqual(body["type"], "pong")

    def test_unknown_type_rejected(self):
        status, body = self.post({"type": "not_a_real_type"})
        self.assertEqual(status, 400)
        self.assertEqual(body["type"], "error")

    def test_pending_approvals_roundtrip(self):
        status, body = self.post({"type": "pending_approvals_request", "request_id": "r3"})
        self.assertEqual(status, 200)
        self.assertEqual(body["approvals"], [])

        action = Action(action="delete_file", target="C:\\Users\\User\\old.zip", risk="high")
        req = self.server.approvals.create(action, "Delete old.zip", estimated_size=524288000)
        self.server.pending_approvals_out.append(req)

        status, body = self.post({"type": "pending_approvals_request", "request_id": "r4"})
        self.assertEqual(status, 200)
        self.assertEqual(len(body["approvals"]), 1)
        entry = body["approvals"][0]
        # Exact keys the Android client's fetchPendingApprovals() parses.
        for key in ("request_id", "action", "target", "risk", "description", "estimated_size"):
            self.assertIn(key, entry)
        self.assertEqual(entry["request_id"], req.request_id)
        self.assertEqual(entry["estimated_size"], 524288000)

        # Resolve it and confirm it drops out of the pending queue.
        status, body = self.post({
            "type": "approval_response", "request_id": req.request_id, "decision": "reject",
        })
        self.assertEqual(status, 200)

        status, body = self.post({"type": "pending_approvals_request", "request_id": "r5"})
        self.assertEqual(body["approvals"], [])


if __name__ == "__main__":
    unittest.main()
