import datetime as dt
import unittest

from tools.search.planner import SearchPlanner


class SearchPlannerTests(unittest.TestCase):
    def test_sports_last_five_query_is_freshness_sensitive(self):
        planner = SearchPlanner(today=dt.date(2026, 5, 12))

        plan = planner.plan("how many goals have Barcelona scored in their last 5 matches in La Liga?")

        self.assertEqual(plan.question_type, "sports_recent_results")
        self.assertTrue(plan.freshness_sensitive)
        self.assertEqual(plan.target_team, "Barcelona")
        self.assertEqual(plan.competition, "La Liga")
        self.assertEqual(plan.requested_count, 5)
        self.assertGreaterEqual(len(plan.queries), 3)
        self.assertIn("May 2026", " ".join(plan.queries))
        self.assertTrue(any("site:espn.com" in query for query in plan.queries))

    def test_current_fact_query_is_freshness_sensitive(self):
        planner = SearchPlanner(today=dt.date(2026, 5, 12))

        plan = planner.plan("who is the current CEO of OpenAI?")

        self.assertEqual(plan.question_type, "fresh_fact")
        self.assertTrue(plan.freshness_sensitive)
        self.assertIn("May 2026", plan.queries[0])

    def test_general_research_query_keeps_original_query_first(self):
        planner = SearchPlanner(today=dt.date(2026, 5, 12))

        plan = planner.plan("explain how transformer attention works")

        self.assertEqual(plan.question_type, "research")
        self.assertFalse(plan.freshness_sensitive)
        self.assertEqual(plan.queries[0], "explain how transformer attention works")
        self.assertLessEqual(len(plan.queries), 2)


if __name__ == "__main__":
    unittest.main()
