import datetime as dt
import unittest

from tools.search.models import EvidencePack, FetchedPage, SearchResult
from tools.search.pipeline import SearchPipeline


class FakeProviderRunner:
    def search(self, queries, limit):
        return [
            SearchResult("Barcelona results", "https://example.com/barca", "snippet", "searxng", 1, queries[0])
        ], []


class FakeFetcher:
    def fetch(self, results):
        text = "\n".join(
            [
                "2026-05-10 | Barcelona | 2-0 | Real Madrid",
                "2026-05-03 | Girona | 1-3 | Barcelona",
                "2026-04-27 | Barcelona | 4-1 | Valencia",
                "2026-04-20 | Sevilla | 0-2 | Barcelona",
                "2026-04-13 | Barcelona | 1-1 | Betis",
            ]
        )
        return [FetchedPage(results[0].url, results[0].title, text, results[0])]


class EmptyProviderRunner:
    def search(self, queries, limit):
        return [], ["provider unavailable"]


class EmptyFetcher:
    def fetch(self, results):
        return []


class SearchPipelineTests(unittest.TestCase):
    def test_collect_returns_structured_evidence_pack(self):
        pipeline = SearchPipeline(
            provider_runner=FakeProviderRunner(),
            fetcher=FakeFetcher(),
            today=dt.date(2026, 5, 12),
        )

        pack = pipeline.collect(
            "how many goals have Barcelona scored in their last 5 matches in La Liga?",
            num_results=5,
        )

        self.assertIsInstance(pack, EvidencePack)
        self.assertEqual(pack.plan.question_type, "sports_recent_results")
        self.assertEqual(pack.confidence, "high")
        self.assertIsNone(pack.answer)
        self.assertEqual(len(pack.results), 1)
        self.assertEqual(len(pack.pages), 1)
        self.assertGreaterEqual(len(pack.matches), 5)
        self.assertEqual(pack.provider_errors, [])
        self.assertEqual(pack.fetch_errors, [])

    def test_search_formats_evidence_without_domain_specific_answer(self):
        pipeline = SearchPipeline(
            provider_runner=FakeProviderRunner(),
            fetcher=FakeFetcher(),
            today=dt.date(2026, 5, 12),
        )

        output = pipeline.search(
            "how many goals have Barcelona scored in their last 5 matches in La Liga?",
            num_results=5,
        )

        self.assertIn("Question type: sports_recent_results", output)
        self.assertIn("Confidence: high", output)
        self.assertNotIn("Computed answer:", output)
        self.assertIn("2026-05-10: Barcelona 2-0 Real Madrid", output)
        self.assertIn("Sources:", output)
        self.assertIn("https://example.com/barca", output)

    def test_collect_reports_empty_provider_result(self):
        pipeline = SearchPipeline(
            provider_runner=EmptyProviderRunner(),
            fetcher=EmptyFetcher(),
            today=dt.date(2026, 5, 12),
        )

        pack = pipeline.collect("latest AI regulation", num_results=5)

        self.assertEqual(pack.confidence, "low")
        self.assertIn("No search results were available", pack.caveats[0])
        self.assertEqual(pack.provider_errors, ["provider unavailable"])


if __name__ == "__main__":
    unittest.main()