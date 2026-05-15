import unittest
from unittest.mock import MagicMock, patch

from tools.search.hybrid_fetch import fetch_url_content_mvp


class HybridFetchTests(unittest.TestCase):
    def test_fetch_url_content_success(self):
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Test paragraph content.</p></body></html>"
        mock_response.raise_for_status.return_value = None

        with patch("requests.get", return_value=mock_response):
            text = fetch_url_content_mvp("http://example.com")

        self.assertIn("Test paragraph content.", text)

    def test_fetch_url_content_failure(self):
        with patch("requests.get", side_effect=Exception("Timeout")):
            text = fetch_url_content_mvp("http://example.com")
        self.assertIn("Failed to fetch content", text)


if __name__ == "__main__":
    unittest.main()
