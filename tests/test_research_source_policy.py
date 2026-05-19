import unittest

from tools.research.source_policy import SourcePolicy


class TestSourcePolicy(unittest.TestCase):
    def setUp(self):
        self.policy = SourcePolicy()

    def test_official_source_scores_above_generic_blog_when_official_preferred(self):
        preferred = ["official statistics", "international organization"]

        official_score = self.policy.score_url("https://www.imf.org/en/Publications/WEO", preferred)
        generic_score = self.policy.score_url("https://example-blog.com/gdp-forecast", preferred)

        self.assertGreater(official_score, generic_score)
        self.assertEqual(self.policy.source_label("https://www.imf.org/en/Publications/WEO"), "official")

    def test_financial_news_scores_above_generic_when_market_news_preferred(self):
        preferred = ["reputable financial news", "market analysis"]

        news_score = self.policy.score_url("https://www.reuters.com/markets/currencies/story", preferred)
        generic_score = self.policy.score_url("https://random-site.example/market-story", preferred)

        self.assertGreater(news_score, generic_score)
        self.assertEqual(self.policy.source_label("https://www.reuters.com/markets/currencies/story"), "financial news")

    def test_company_source_scores_when_company_filings_preferred(self):
        preferred = ["company filings", "primary company source"]

        company_score = self.policy.score_url("https://investor.microsoft.com/news-releases", preferred)
        generic_score = self.policy.score_url("https://example.com/microsoft-ai", preferred)

        self.assertGreater(company_score, generic_score)
        self.assertEqual(
            self.policy.source_label("https://investor.microsoft.com/news-releases"),
            "primary company source",
        )

    def test_low_quality_source_is_penalized(self):
        preferred = ["expert analysis"]

        low_score = self.policy.score_url("https://random.medium.com/opinion", preferred)
        generic_score = self.policy.score_url("https://example.com/article", preferred)

        self.assertLess(low_score, generic_score)


if __name__ == "__main__":
    unittest.main()