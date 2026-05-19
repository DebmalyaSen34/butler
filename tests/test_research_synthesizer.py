import unittest

from tools.research.models import ResearchEvidence, ResearchPlan, ResearchSubquery
from tools.research.synthesizer import ResearchSynthesizer
from tools.search.models import EvidenceItem, EvidencePack, SearchPlan


def search_plan() -> SearchPlan:
    return SearchPlan(
        original_query="query",
        question_type="research",
        queries=["query"],
    )


def research_plan() -> ResearchPlan:
    return ResearchPlan(
        original_query="compare GDP forecasts",
        question_type="comparison",
        subqueries=[
            ResearchSubquery("one", "first"),
            ResearchSubquery("two", "second"),
            ResearchSubquery("three", "third", required=False),
        ],
        freshness_sensitive=True,
        preferred_source_types=["official statistics"],
        ambiguity_notes=["GDP can mean nominal, PPP, growth, or per capita."],
    )


def evidence_item(subquery: ResearchSubquery, claims: list[EvidenceItem]) -> ResearchEvidence:
    return ResearchEvidence(
        subquery=subquery,
        pack=EvidencePack(
            plan=search_plan(),
            claims=claims,
            confidence="medium",
        ),
    )


class TestResearchSynthesizer(unittest.TestCase):
    def test_synthesizer_dedupes_sources(self):
        plan = research_plan()
        evidence = [
            evidence_item(
                plan.subqueries[0],
                [
                    EvidenceItem("Claim one.", "https://example.com/one", "One", "fake"),
                    EvidenceItem("Claim duplicate source.", "https://example.com/one", "One", "fake"),
                ],
            ),
            evidence_item(
                plan.subqueries[1],
                [
                    EvidenceItem("Claim two.", "https://example.com/two", "Two", "fake"),
                ],
            ),
        ]

        report = ResearchSynthesizer().synthesize(plan, evidence)

        self.assertEqual(report.source_urls, ["https://example.com/one", "https://example.com/two"])

    def test_synthesizer_marks_forecasts_as_caveat(self):
        plan = research_plan()
        evidence = [
            evidence_item(
                plan.subqueries[0],
                [
                    EvidenceItem(
                        "The 2025 figure is a forecast, not final actual data.",
                        "https://www.imf.org/report",
                        "IMF report",
                        "fake",
                    )
                ],
            )
        ]

        report = ResearchSynthesizer().synthesize(plan, evidence)

        self.assertTrue(any("forecast" in caveat.casefold() for caveat in report.caveats))

    def test_synthesizer_renders_required_sections(self):
        plan = research_plan()
        evidence = [
            evidence_item(
                plan.subqueries[0],
                [
                    EvidenceItem(
                        "Official data gives a supported finding.",
                        "https://www.imf.org/report",
                        "IMF report",
                        "fake",
                    ),
                    EvidenceItem(
                        "A second source supports context.",
                        "https://www.reuters.com/markets/story",
                        "Reuters story",
                        "fake",
                    ),
                ],
            )
        ]

        report = ResearchSynthesizer().synthesize(plan, evidence)
        rendered = ResearchSynthesizer().render(report)

        self.assertIn("Short answer:", rendered)
        self.assertIn("Key findings:", rendered)
        self.assertIn("Details:", rendered)
        self.assertIn("Confidence:", rendered)
        self.assertIn("Caveats:", rendered)
        self.assertIn("Sources:", rendered)
        self.assertIn("https://www.imf.org/report", rendered)

    def test_synthesizer_low_confidence_without_sources(self):
        plan = research_plan()

        report = ResearchSynthesizer().synthesize(plan, [])

        self.assertEqual(report.confidence, "low")
        self.assertTrue(any("no source evidence" in caveat.casefold() for caveat in report.caveats))


if __name__ == "__main__":
    unittest.main()