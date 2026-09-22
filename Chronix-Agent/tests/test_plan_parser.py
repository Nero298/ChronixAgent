import unittest

from core.plan_parser import parse_action_plan, PlanValidationError
from core.constants import ACTION_OPEN_APP, RISK_LOW, ACTION_DELETE_FILE, RISK_HIGH


class TestPlanParser(unittest.TestCase):
    def test_valid_plan_parses(self):
        raw = '{"type": "action_plan", "actions": [{"action": "open_app", "target": "chrome", "risk": "low"}]}'
        plan = parse_action_plan(raw)
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action, ACTION_OPEN_APP)
        self.assertEqual(plan.actions[0].risk, RISK_LOW)  # from our table, not Gemini's

    def test_gemini_cannot_downgrade_risk(self):
        # Gemini claims "low" for a delete - parser must override with our table's "high".
        raw = ('{"type": "action_plan", "actions": '
               '[{"action": "delete_file", "target": "C:\\\\x.txt", "risk": "low"}]}')
        plan = parse_action_plan(raw)
        self.assertEqual(plan.actions[0].risk, RISK_HIGH)

    def test_unknown_action_dropped_not_raised(self):
        raw = '{"type": "action_plan", "actions": [{"action": "format_disk", "target": "C:"}]}'
        plan = parse_action_plan(raw)
        self.assertEqual(plan.actions, [])

    def test_malformed_json_raises(self):
        with self.assertRaises(PlanValidationError):
            parse_action_plan("not json at all")

    def test_missing_type_field_raises(self):
        with self.assertRaises(PlanValidationError):
            parse_action_plan('{"actions": []}')

    def test_code_fence_stripped(self):
        raw = '```json\n{"type": "action_plan", "actions": []}\n```'
        plan = parse_action_plan(raw)
        self.assertEqual(plan.actions, [])

    def test_nested_param_object_dropped(self):
        raw = ('{"type": "action_plan", "actions": [{"action": "create_file", "target": "a.txt", '
               '"params": {"content": "hi", "evil": {"nested": "object"}}}]}')
        plan = parse_action_plan(raw)
        self.assertNotIn("evil", plan.actions[0].params)
        self.assertEqual(plan.actions[0].params["content"], "hi")


if __name__ == "__main__":
    unittest.main()
