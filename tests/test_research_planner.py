import json
import unittest

from tools.research.planner import ResearchPlanner, ResearchPlanValidator


class FakePlannerLLM:
    def __init__(self, output):
        self.output = output

    def complete_plan(self, prompt: str) -> str:
        if isinstance(self.output, str):
            return self.output
        return json.dumps(self.output)


class TestResearchPlanner(unittest.TestCase):
    def test_llm_planner_builds_valid_plan_from_json(self):
        llm = FakePlannerLLM(
            {
                "question_type": "comparison",
                "freshness_sensitive": True,
                "preferred_source_types": ["official statistics", "international organization"],
                "ambiguity_notes": ["GDP can mean nominal, PPP, growth, or per capita."],
                "subqueries": [
                    {
                        "query": "India GDP 2025 nominal current US dollars official forecast",
                        "purpose": "Find India estimate",
                        "required": True,
                    },
                    {
                        "query": "China GDP 2025 nominal current US dollars official forecast",
                        "purpose": "Find China estimate",
                        "required": True,
                    },
                    {
                        "query": "India China GDP 2025 international organization comparison",
                        "purpose": "Cross-check figures",
                        "required": False,
                    },
                ],
            }
        )

        plan = ResearchPlanner(llm_client=llm).plan("compare India and China GDP in 2025")

        self.assertEqual(plan.question_type, "comparison")
        self.assertTrue(plan.freshness_sensitive)
        self.assertEqual(len(plan.subqueries), 3)
        self.assertIn("official statistics", plan.preferred_source_types)
        self.assertTrue(any("nominal" in note.casefold() for note in plan.ambiguity_notes))

    def test_planner_falls_back_when_llm_returns_invalid_json(self):
        llm = FakePlannerLLM("not json")

        plan = ResearchPlanner(llm_client=llm).plan("Compare Apple and Microsoft AI strategy this year")

        self.assertEqual(plan.question_type, "general_research")
        self.assertGreaterEqual(len(plan.subqueries), 3)
        self.assertTrue(any("official primary source" in subquery.query for subquery in plan.subqueries))

    def test_validator_rejects_source_urls_in_source_types(self):
        raw_plan = {
            "question_type": "comparison",
            "freshness_sensitive": True,
            "preferred_source_types": ["https://example.com", "official statistics"],
            "subqueries": [
                {"query": "one", "purpose": "one"},
                {"query": "two", "purpose": "two"},
                {"query": "three", "purpose": "three"},
            ],
        }

        plan = ResearchPlanValidator().validate(raw_plan, "question")

        self.assertEqual(plan.preferred_source_types, ["official statistics"])

    def test_validator_dedupes_and_limits_subqueries(self):
        raw_plan = {
            "question_type": "market_analysis",
            "freshness_sensitive": True,
            "subqueries": [
                {"query": "same", "purpose": "first"},
                {"query": "same", "purpose": "duplicate"},
                {"query": "two", "purpose": "second"},
                {"query": "three", "purpose": "third"},
                {"query": "four", "purpose": "fourth"},
                {"query": "five", "purpose": "fifth"},
                {"query": "six", "purpose": "sixth"},
                {"query": "seven", "purpose": "seventh"},
            ],
        }

        plan = ResearchPlanValidator().validate(raw_plan, "question")

        self.assertEqual(len(plan.subqueries), 6)
        self.assertEqual(plan.subqueries[0].query, "same")
        self.assertTrue(plan.subqueries[0].required)


if __name__ == "__main__":
    unittest.main()