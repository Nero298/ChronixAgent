import unittest

from core.security import ChronixGuard, is_protected_path
from core.models import Action
from core.constants import ACTION_DELETE_FILE, ACTION_OPEN_APP, RISK_HIGH, RISK_LOW, RISK_MEDIUM


class TestProtectedPaths(unittest.TestCase):
    def test_protected_path_windows_dir(self):
        self.assertTrue(is_protected_path("C:\\Windows\\System32\\config"))

    def test_protected_path_root_of_drive(self):
        self.assertTrue(is_protected_path("C:\\"))

    def test_protected_path_program_files(self):
        self.assertTrue(is_protected_path("C:\\Program Files\\SomeApp"))

    def test_unprotected_user_path(self):
        self.assertFalse(is_protected_path("C:\\Users\\User\\Downloads\\old.zip"))

    def test_path_traversal_rejected(self):
        self.assertTrue(is_protected_path("C:\\Users\\User\\Downloads\\..\\..\\Windows"))


class TestChronixGuard(unittest.TestCase):
    def test_guard_blocks_delete_of_protected_path(self):
        guard = ChronixGuard()
        action = Action(action=ACTION_DELETE_FILE, target="C:\\Windows\\notepad.exe", risk=RISK_HIGH)
        verdict = guard.evaluate(action)
        self.assertFalse(verdict.allowed)

    def test_guard_requires_approval_for_safe_delete(self):
        guard = ChronixGuard()
        action = Action(action=ACTION_DELETE_FILE, target="C:\\Users\\User\\Downloads\\old.zip",
                         risk=RISK_HIGH)
        verdict = guard.evaluate(action)
        self.assertTrue(verdict.allowed)
        self.assertTrue(verdict.requires_approval)

    def test_guard_auto_allows_low_risk(self):
        guard = ChronixGuard()
        action = Action(action=ACTION_OPEN_APP, target="chrome", risk=RISK_LOW)
        verdict = guard.evaluate(action)
        self.assertTrue(verdict.allowed)
        self.assertFalse(verdict.requires_approval)

    def test_guard_medium_policy_toggle(self):
        action = Action(action="create_file", target="a.txt", risk=RISK_MEDIUM)
        guard_lenient = ChronixGuard(require_approval_for_medium=False)
        self.assertFalse(guard_lenient.evaluate(action).requires_approval)

        guard_strict = ChronixGuard(require_approval_for_medium=True)
        self.assertTrue(guard_strict.evaluate(action).requires_approval)


if __name__ == "__main__":
    unittest.main()
