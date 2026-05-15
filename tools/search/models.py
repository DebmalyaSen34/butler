from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchPlan:
    original_query: str
    question_type: str
    queries: list[str]
    freshness_sensitive: bool = False
    target_team: str | None = None
    competition: str | None = None
    requested_count: int | None = None


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    rank: int
    query: str


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str
    text: str
    source_result: SearchResult
    ok: bool = True
    error: str | None = None


@dataclass(frozen=True)
class EvidenceItem:
    claim: str
    url: str
    title: str
    source: str
    score: float = 0.0


@dataclass(frozen=True)
class MatchEvidence:
    date: str | None
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    competition: str | None
    url: str
    title: str
    source: str
    score: float = 0.0

    def goals_for(self, team: str) -> int | None:
        normalized = team.casefold()
        if self.home_team.casefold() == normalized:
            return self.home_goals
        if self.away_team.casefold() == normalized:
            return self.away_goals
        return None


@dataclass(frozen=True)
class EvidencePack:
    plan: SearchPlan
    results: list[SearchResult] = field(default_factory=list)
    pages: list[FetchedPage] = field(default_factory=list)
    matches: list[MatchEvidence] = field(default_factory=list)
    claims: list[EvidenceItem] = field(default_factory=list)
    provider_errors: list[str] = field(default_factory=list)
    fetch_errors: list[str] = field(default_factory=list)
    answer: str | None = None
    confidence: str = "low"
    caveats: list[str] = field(default_factory=list)
