import unittest

from agent import protocol
from core.constants import MSG_CHAT


class TestProtocol(unittest.TestCase):
    def test_decode_valid_chat_message(self):
        raw = '{"type": "chat", "request_id": "abc123", "message": "Open Chrome"}'
        env = protocol.decode(raw)
        self.assertEqual(env.type, MSG_CHAT)
        self.assertEqual(env.request_id, "abc123")
        self.assertEqual(env.payload["message"], "Open Chrome")

    def test_decode_rejects_bad_json(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.decode("{not json")

    def test_decode_rejects_unknown_type(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.decode('{"type": "hack_the_planet"}')

    def test_decode_rejects_non_object(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.decode('["just", "a", "list"]')

    def test_encode_roundtrip(self):
        env = protocol.make_chat_response("rid1", "Opening Chrome.")
        raw = env.to_json()
        decoded = protocol.decode(raw)
        self.assertEqual(decoded.payload["message"], "Opening Chrome.")


if __name__ == "__main__":
    unittest.main()
