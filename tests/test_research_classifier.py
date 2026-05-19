import unittest
from tools.research.classifier import ResearchClassifier

class TestResearchClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = ResearchClassifier()

    def test_comparison_query_needs_research(self):
        self.assertTrue(self.classifier.needs_research("compare India and China GDP in 2025"))

    def test_recent_causal_query_needs_research(self):
        self.assertTrue(self.classifier.needs_research("Why is Indian Rupee falling recently?"))

    def test_detailed_report_needs_research(self):
        self.assertTrue(self.classifier.needs_research("give me a detailed report on oil prices this year"))

    def test_simple_lookup_does_not_need_research(self):
        self.assertFalse(self.classifier.needs_research("who is the CEO of Microsoft"))

if __name__ == "__main__":
    unittest.main()