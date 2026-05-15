import unittest
from unittest.mock import patch

from core.orchestrator import extract_action, run_react_loop


class OrchestratorTests(unittest.TestCase):
    def test_extract_action_reads_json_after_action_marker(self):
        action = extract_action('Thought: I know this.\nAction: {"finish": {"answer": "42"}}')

        self.assertEqual(action, {"finish": {"answer": "42"}})

    @patch("core.llm.generate_response")
    @patch("tools.registry.execute_react_tool")
    def test_run_react_loop_finish(self, mock_execute, mock_generate):
        mock_generate.return_value = iter(["Thought: I know this.\nAction: {\"finish\": {\"answer\": \"42\"}}"])
        mock_execute.return_value = "42"

        answer = run_react_loop("What is the meaning of life?", max_iterations=2)

        self.assertIn("42", answer)


if __name__ == "__main__":
    unittest.main()
