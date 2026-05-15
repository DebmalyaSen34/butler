from __future__ import annotations

from dataclasses import replace

from tools.search.models import EvidenceItem, MatchEvidence, SearchPlan


class EvidenceRanker:
    def rank(
        self,
        plan: SearchPlan,
        matches: list[MatchEvidence],
        claims: list[EvidenceItem],
    ) -> tuple[list[MatchEvidence], list[EvidenceItem]]:
        ranked_matches = [replace(match, score=self._match_score(plan, match)) for match in matches]
        ranked_claims = [replace(claim, score=self._claim_score(plan, claim)) for claim in claims]
        ranked_matches.sort(key=lambda item: (item.date or "", item.score), reverse=True)
        ranked_claims.sort(key=lambda item: item.score, reverse=True)
        return ranked_matches, ranked_claims

    def _match_score(self, plan: SearchPlan, match: MatchEvidence) -> float:
        score = 1.0
        if plan.target_team and match.goals_for(plan.target_team) is not None:
            score += 1.0
        if plan.competition and match.competition == plan.competition:
            score += 0.5
        if match.date:
            score += 0.5
        if match.source == "searxng":
            score += 0.2
        return score

    def _claim_score(self, plan: SearchPlan, claim: EvidenceItem) -> float:
        score = 0.5
        terms = {term for term in plan.original_query.casefold().split() if len(term) > 3}
        claim_text = claim.claim.casefold()
        score += sum(0.1 for term in terms if term in claim_text)
        if claim.source == "searxng":
            score += 0.2
        return score
