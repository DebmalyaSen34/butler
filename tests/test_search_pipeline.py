import datetime as dt
import unittest

from tools.search.models import FetchedPage, SearchResult
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


class SearchPipelineTests(unittest.TestCase):
    def test_pipeline_builds_computed_sports_evidence_pack(self):
        pipeline = SearchPipeline(
            provider_runner=FakeProviderRunner(),
            fetcher=FakeFetcher(),
            today=dt.date(2026, 5, 12),
        )

        output = pipeline.search("how many goals have Barcelona scored in their last 5 matches in La Liga?", num_results=5)

        self.assertIn("Question type: sports_recent_results", output)
        self.assertIn("Computed answer: Barcelona scored 12 goals", output)
        self.assertIn("Confidence: high", output)
        self.assertIn("2026-05-10: Barcelona 2-0 Real Madrid", output)
        self.assertIn("Sources:", output)
        self.assertIn("https://example.com/barca", output)

    def test_pipeline_reports_partial_sports_evidence(self):
        class PartialFetcher:
            def fetch(self, results):
                text = "2026-05-10 | Barcelona | 2-0 | Real Madrid"
                return [FetchedPage(results[0].url, results[0].title, text, results[0])]

        pipeline = SearchPipeline(
            provider_runner=FakeProviderRunner(),
            fetcher=PartialFetcher(),
            today=dt.date(2026, 5, 12),
        )

        output = pipeline.search("Barcelona last 5 La Liga goals", num_results=5)

        self.assertIn("Confidence: low", output)
        self.assertIn("Only found 1 of 5 requested matches.", output)


if __name__ == "__main__":
    unittest.main()
