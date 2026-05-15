import unittest
from unittest.mock import MagicMock, patch

from tools.search.searxng import search_searxng


class SearxngToolTests(unittest.TestCase):
    def test_search_searxng_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"title": "Test 1", "url": "http://test1.com", "content": "Snippet 1"},
                {"title": "Test 2", "url": "http://test2.com", "content": "Snippet 2"},
            ]
        }
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response) as mock_get:
            results = search_searxng("test query", num_results=2)

        mock_get.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], {"title": "Test 1", "url": "http://test1.com", "snippet": "Snippet 1"})

    def test_search_searxng_failure(self):
        with patch("requests.get", side_effect=Exception("API Down")):
            results = search_searxng("test query")
        self.assertEqual(results, [{"error": "Search failed: API Down"}])


if __name__ == "__main__":
    unittest.main()
