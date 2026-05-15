from __future__ import annotations

import datetime as dt

from config.settings import SEARXNG_URL
from tools.search.builder import AnswerContextBuilder
from tools.search.extractor import EvidenceExtractor
from tools.search.fetcher import ContentFetcher
from tools.search.models import EvidencePack, FetchedPage
from tools.search.planner import SearchPlanner
from tools.search.providers import DdgsProvider, ProviderRunner, SearxngProvider
from tools.search.ranker import EvidenceRanker


class SearchPipeline:
    def __init__(
        self,
        provider_runner: ProviderRunner | None = None,
        fetcher: ContentFetcher | None = None,
        today: dt.date | None = None,
    ) -> None:
        self.today = today or dt.date.today()
        self.planner = SearchPlanner(today=self.today)
        self.provider_runner = provider_runner or ProviderRunner(
            [SearxngProvider(SEARXNG_URL), DdgsProvider()],
            min_results=2,
        )
        self.fetcher = fetcher or ContentFetcher()
        self.extractor = EvidenceExtractor(today=self.today)
        self.ranker = EvidenceRanker()
        self.builder = AnswerContextBuilder()

    def search(self, query: str, num_results: int = 5) -> str:
        plan = self.planner.plan(query)
        results, provider_errors = self.provider_runner.search(plan.queries, limit=num_results)
        pages = self.fetcher.fetch(results)
        fetch_errors = [f"{page.url}: {page.error}" for page in pages if not page.ok and page.error]
        matches, claims = self.extractor.extract(plan, pages)
        ranked_matches, ranked_claims = self.ranker.rank(plan, matches, claims)
        answer, confidence, caveats = self._answer(plan, ranked_matches, ranked_claims, pages)
        pack = EvidencePack(
            plan=plan,
            results=results,
            pages=pages,
            matches=ranked_matches,
            claims=ranked_claims,
            provider_errors=provider_errors,
            fetch_errors=fetch_errors,
            answer=answer,
            confidence=confidence,
            caveats=caveats,
        )
        return self.builder.build(pack)

    def _answer(self, plan, matches, claims, pages: list[FetchedPage]) -> tuple[str | None, str, list[str]]:
        if plan.question_type == "sports_recent_results":
            requested = plan.requested_count or 5
            usable = matches[:requested]
            caveats: list[str] = []
            if len(usable) < requested:
                caveats.append(f"Only found {len(usable)} of {requested} requested matches.")
            if not usable or not plan.target_team:
                return None, "low", caveats or ["No direct match-result evidence was found."]
            total = sum(match.goals_for(plan.target_team) or 0 for match in usable)
            confidence = "high" if len(usable) >= requested else "low"
            return (
                f"{plan.target_team} scored {total} goals across the {len(usable)} verified matches.",
                confidence,
                caveats,
            )

        if claims:
            return None, "medium", []

        if not pages:
            return None, "low", ["No search results were available from the configured providers."]

        return None, "low", ["Search results were found, but no concise evidence could be extracted."]


def search_web(query: str, num_results: int = 5) -> str:
    return SearchPipeline().search(query, num_results=num_results)
