import unittest

from tools.registry import execute_tool


class RegistryTests(unittest.TestCase):
    def test_risky_tool_requires_confirmation(self):
        response = '{"tool": "create_file", "args": {"filename": "x.txt", "content": "hi"}}'
        self.assertIn("needs confirmation", execute_tool(response))

    def test_risky_tool_can_be_cancelled(self):
        response = '{"tool": "open_app", "args": {"app_name": "Calculator"}}'
        result = execute_tool(response, confirm_tool=lambda name, args, permission: False)
        self.assertIn("cancelled", result)

    def test_safe_tool_runs_without_confirmation(self):
        response = '{"tool": "get_time", "args": {}}'
        self.assertIn("executed successfully", execute_tool(response))


if __name__ == "__main__":
    unittest.main()
