import unittest
from core.orchestrator import extract_action

class TestOrchestratorResearch(unittest.TestCase):
    def test_extract_action_parses_research_query(self):
        llm_out = """Thought: Need deep macro report.
Action: {"research_query": {"query": "compare India and China GDP in 2025", "max_sources": 8}}"""
        
        action = extract_action(llm_out)
        
        self.assertIn("research_query", action)
        self.assertEqual(action["research_query"]["query"], "compare India and China GDP in 2025")
        self.assertEqual(action["research_query"]["max_sources"], 8)

if __name__ == "__main__":
    unittest.main()