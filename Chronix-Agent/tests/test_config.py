import json
import os
import tempfile
import unittest

from agent.config import ChronixConfig, GEMINI_KEY_ENV


class TestChronixConfig(unittest.TestCase):
    def test_defaults_when_no_file(self):
        cfg = ChronixConfig.load(path="/nonexistent/path/config.json")
        self.assertEqual(cfg.device_name, "Chronix-PC")
        self.assertEqual(cfg.server_port, 8765)
        self.assertTrue(cfg.show_pairing_window)

    def test_loads_from_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "device_name": "My-PC",
                "server_port": 9999,
                "show_pairing_window": False,
                "auto_start": True,
            }, f)
            path = f.name
        try:
            cfg = ChronixConfig.load(path=path)
            self.assertEqual(cfg.device_name, "My-PC")
            self.assertEqual(cfg.server_port, 9999)
            self.assertFalse(cfg.show_pairing_window)
            self.assertTrue(cfg.auto_start)
        finally:
            os.unlink(path)

    def test_env_var_overrides_file_key(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"gemini_api_key": "from-file"}, f)
            path = f.name
        try:
            os.environ[GEMINI_KEY_ENV] = "from-env"
            cfg = ChronixConfig.load(path=path)
            self.assertEqual(cfg.gemini_api_key, "from-env")
        finally:
            os.unlink(path)
            del os.environ[GEMINI_KEY_ENV]

    def test_redacted_dict_never_leaks_secrets(self):
        cfg = ChronixConfig(gemini_api_key="super-secret", pairing_token="also-secret")
        d = cfg.redacted_dict()
        self.assertNotIn("super-secret", str(d))
        self.assertNotIn("also-secret", str(d))
        self.assertEqual(d["gemini_api_key"], "***set***")
        self.assertEqual(d["pairing_token"], "***set***")

    def test_redacted_dict_shows_unset(self):
        cfg = ChronixConfig(gemini_api_key="", pairing_token="")
        d = cfg.redacted_dict()
        self.assertEqual(d["gemini_api_key"], "***unset***")


if __name__ == "__main__":
    unittest.main()
