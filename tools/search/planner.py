from __future__ import annotations

import datetime as dt
import re

from tools.search.models import SearchPlan


class SearchPlanner:
    def __init__(self, today: dt.date | None = None) -> None:
        self.today = today or dt.date.today()

    def plan(self, query: str) -> SearchPlan:
        normalized = " ".join(query.strip().split())
        lowered = normalized.casefold()
        requested_count = self._requested_count(lowered)
        target_team = self._target_team(normalized)
        competition = self._competition(normalized)

        if self._is_sports_recent_results(lowered, target_team, requested_count):
            return SearchPlan(
                original_query=normalized,
                question_type="sports_recent_results",
                queries=self._sports_queries(normalized, target_team, competition),
                freshness_sensitive=True,
                target_team=target_team,
                competition=competition,
                requested_count=requested_count,
            )

        if self._is_fresh_fact(lowered):
            return SearchPlan(
                original_query=normalized,
                question_type="fresh_fact",
                queries=[f"{normalized} {self._month_year()}"],
                freshness_sensitive=True,
            )

        return SearchPlan(
            original_query=normalized,
            question_type="research",
            queries=[normalized],
            freshness_sensitive=False,
        )

    def _requested_count(self, lowered: str) -> int | None:
        match = re.search(r"\blast\s+(\d+)\b", lowered)
        return int(match.group(1)) if match else None

    def _target_team(self, query: str) -> str | None:
        known_teams = ["Barcelona"]
        lowered = query.casefold()
        for team in known_teams:
            if team.casefold() in lowered:
                return team
        return None

    def _competition(self, query: str) -> str | None:
        if re.search(r"\bla\s*liga\b", query, flags=re.IGNORECASE):
            return "La Liga"
        return None

    def _is_sports_recent_results(
        self,
        lowered: str,
        target_team: str | None,
        requested_count: int | None,
    ) -> bool:
        sports_terms = ["goal", "goals", "match", "matches", "score", "fixture", "fixtures", "la liga"]
        return bool(target_team and requested_count and any(term in lowered for term in sports_terms))

    def _is_fresh_fact(self, lowered: str) -> bool:
        fresh_terms = ["latest", "today", "current", "recent", "price", "release date", "who is"]
        return any(term in lowered for term in fresh_terms)

    def _sports_queries(
        self,
        original_query: str,
        target_team: str | None,
        competition: str | None,
    ) -> list[str]:
        month_year = self._month_year()
        team = target_team or original_query
        league = competition or ""
        season = f"{self.today.year - 1}-{self.today.year}"
        queries = [
            f"site:espn.com {team} fixtures results {league} {month_year}".strip(),
            f"site:worldfootball.net {team} results {league} {season}".strip(),
            f"{team} last 5 {league} results {month_year}".strip(),
            f"{original_query} {month_year}".strip(),
        ]
        return list(dict.fromkeys(queries))

    def _month_year(self) -> str:
        return self.today.strftime("%B %Y")
