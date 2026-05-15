import unittest
from unittest.mock import Mock, patch

from tools.search.models import SearchResult
from tools.search.providers import DdgsProvider, ProviderRunner, SearxngProvider


class SearchProviderTests(unittest.TestCase):
    def test_searxng_provider_normalizes_json_results(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "results": [
                {"title": "Barcelona results", "url": "https://example.com/a", "content": "A snippet"},
                {"title": "Other result", "url": "https://example.com/b", "content": "B snippet"},
            ]
        }

        with patch("tools.search.providers.requests.get", return_value=response):
            results = SearxngProvider("http://localhost:8080/search").search("barcelona", limit=2)

        self.assertEqual(len(results), 2)
        self.assertEqual(
            results[0],
            SearchResult("Barcelona results", "https://example.com/a", "A snippet", "searxng", 1, "barcelona"),
        )

    def test_ddgs_provider_normalizes_text_results(self):
        fake_ddgs = Mock()
        fake_ddgs.text.return_value = [
            {"title": "Barcelona fixtures", "href": "https://example.com/c", "body": "C snippet"}
        ]
        fake_context = Mock()
        fake_context.__enter__ = Mock(return_value=fake_ddgs)
        fake_context.__exit__ = Mock(return_value=None)

        with patch("tools.search.providers.DDGS", return_value=fake_context):
            results = DdgsProvider().search("barcelona", limit=1)

        self.assertEqual(
            results[0],
            SearchResult("Barcelona fixtures", "https://example.com/c", "C snippet", "ddgs", 1, "barcelona"),
        )

    def test_runner_falls_back_when_first_provider_fails(self):
        failing_provider = Mock()
        failing_provider.name = "searxng"
        failing_provider.search.side_effect = RuntimeError("connection refused")
        working_provider = Mock()
        working_provider.name = "ddgs"
        working_provider.search.return_value = [
            SearchResult("Title", "https://example.com", "Snippet", "ddgs", 1, "query")
        ]

        runner = ProviderRunner([failing_provider, working_provider], min_results=1)
        results, errors = runner.search(["query"], limit=3)

        self.assertEqual(len(results), 1)
        self.assertEqual(errors, ["searxng failed for 'query': connection refused"])


if __name__ == "__main__":
    unittest.main()
