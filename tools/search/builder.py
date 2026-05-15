from __future__ import annotations

from tools.search.models import EvidenceItem, EvidencePack, MatchEvidence, SearchPlan


class AnswerContextBuilder:
    def build(self, pack: EvidencePack) -> str:
        lines = [
            f"Question type: {pack.plan.question_type}",
            f"Original question: {pack.plan.original_query}",
            f"Confidence: {pack.confidence}",
        ]
        if pack.answer:
            lines.append(f"Computed answer: {pack.answer}")
        if pack.caveats:
            lines.append("Caveats:")
            lines.extend(f"- {caveat}" for caveat in pack.caveats)

        if pack.matches:
            lines.append("Evidence:")
            lines.extend(self._match_lines(pack.plan, pack.matches))
        elif pack.claims:
            lines.append("Evidence:")
            lines.extend(self._claim_lines(pack.claims))

        source_lines = self._sources(pack.matches, pack.claims)
        if source_lines:
            lines.append("Sources:")
            lines.extend(source_lines)

        if pack.provider_errors or pack.fetch_errors:
            lines.append("Diagnostics:")
            lines.extend(f"- {error}" for error in [*pack.provider_errors, *pack.fetch_errors][:5])

        return "\n".join(lines)

    def _match_lines(self, plan: SearchPlan, matches: list[MatchEvidence]) -> list[str]:
        lines: list[str] = []
        for match in matches:
            goals = match.goals_for(plan.target_team or "")
            date = match.date or "unknown date"
            lines.append(
                f"- {date}: {match.home_team} {match.home_goals}-{match.away_goals} "
                f"{match.away_team}; {plan.target_team} goals: {goals}; source: {match.url}"
            )
        return lines

    def _claim_lines(self, claims: list[EvidenceItem]) -> list[str]:
        return [f"- {claim.claim} source: {claim.url}" for claim in claims[:5]]

    def _sources(self, matches: list[MatchEvidence], claims: list[EvidenceItem]) -> list[str]:
        seen: set[str] = set()
        lines: list[str] = []
        for item in [*matches, *claims]:
            if item.url in seen:
                continue
            seen.add(item.url)
            lines.append(f"- {item.title}: {item.url}")
        return lines
