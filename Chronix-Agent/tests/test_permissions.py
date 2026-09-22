import time
import unittest

from core.permissions import ApprovalManager
from core.models import Action
from core.constants import (
    ACTION_DELETE_FILE, RISK_HIGH, APPROVAL_DECISION_APPROVE, APPROVAL_DECISION_REJECT,
)


def make_action():
    return Action(action=ACTION_DELETE_FILE, target="C:\\Users\\User\\Downloads\\old.zip", risk=RISK_HIGH)


class TestApprovalManager(unittest.TestCase):
    def test_approve_matches_exact_request_id(self):
        mgr = ApprovalManager()
        req = mgr.create(make_action(), "Delete old.zip")
        ok, _ = mgr.resolve(req.request_id, APPROVAL_DECISION_APPROVE)
        self.assertTrue(ok)
        self.assertTrue(mgr.is_approved(req.request_id))

    def test_mismatched_request_id_ignored(self):
        mgr = ApprovalManager()
        mgr.create(make_action(), "Delete old.zip")
        ok, _ = mgr.resolve("nonexistent-id", APPROVAL_DECISION_APPROVE)
        self.assertFalse(ok)

    def test_duplicate_response_ignored(self):
        mgr = ApprovalManager()
        req = mgr.create(make_action(), "Delete old.zip")
        ok1, _ = mgr.resolve(req.request_id, APPROVAL_DECISION_APPROVE)
        ok2, _ = mgr.resolve(req.request_id, APPROVAL_DECISION_APPROVE)
        self.assertTrue(ok1)
        self.assertFalse(ok2)  # second call must not re-trigger anything

    def test_expired_request_cannot_be_approved(self):
        mgr = ApprovalManager(timeout_seconds=0)
        req = mgr.create(make_action(), "Delete old.zip")
        time.sleep(0.01)
        ok, _ = mgr.resolve(req.request_id, APPROVAL_DECISION_APPROVE)
        self.assertFalse(ok)
        self.assertFalse(mgr.is_approved(req.request_id))

    def test_reject_never_marks_approved(self):
        mgr = ApprovalManager()
        req = mgr.create(make_action(), "Delete old.zip")
        mgr.resolve(req.request_id, APPROVAL_DECISION_REJECT)
        self.assertFalse(mgr.is_approved(req.request_id))


if __name__ == "__main__":
    unittest.main()
