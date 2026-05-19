from __future__ import annotations
import json
import re
from typing import Any
from tools.research.models import ResearchPlan, ResearchSubquery
from tools.research.planner_client import ResearchPlannerLLM

class ResearchPlannerValidationError(ValueError):
    pass

class ResearchPlanValidator:
    MIN_SUBQUERIES = 3
    MAX_SUBQUERIES = 6
    MAX_QUERY_CHARS = 180
    MAX_PURPOSE_CHARS = 160
    MAX_NOTE_CHARS = 220

    def validate(self, raw_plan: dict[str, Any], original_query: str, max_sources: int = 8) -> ResearchPlan:
        if not isinstance(raw_plan, dict):
            raise ResearchPlannerValidationError("Research plan must be a JSON object.")
        
        subqueries = self._subqueries(raw_plan.get("subqueries"))
        if len(subqueries) < self.MIN_SUBQUERIES:
            raise ResearchPlannerValidationError(f"At least {self.MIN_SUBQUERIES} subqueries are required.")
        
        return ResearchPlan(
            original_query=self._normalize(original_query),
            question_type=self._clean_label(raw_plan.get("question_type")) or "general_research",
            subqueries=subqueries[:self.MAX_SUBQUERIES],
            freshness_sensitive=bool(raw_plan.get("freshness_sensitive", False)),
            preferred_source_types=self._clean_source_types(raw_plan.get("preferred_source_types")),
            ambiguity_notes=self._clean_notes(raw_plan.get("ambiguity_notes")),
            max_sources=max_sources
        )
    
    def _subqueries(self, raw_subqueries: Any) -> list[ResearchSubquery]:
        if not isinstance(raw_subqueries, list):
            return []
        
        seen: set[str] = set()
        subqueries: list[ResearchSubquery] = []

        for item in raw_subqueries:
            if not isinstance(item, dict):
                continue

            query = self._clean_text(item.get("query"), self.MAX_QUERY_CHARS)
            purpose = self._clean_text(item.get("purpose"), self.MAX_PURPOSE_CHARS)

            if not query or not purpose:
                continue

            key = query.casefold()
            if key in seen:
                continue

            seen.add(key)
            subqueries.append(
                ResearchSubquery(
                    query=query,
                    purpose=purpose,
                    required=bool(item.get("required", True)),
                )
            )

        if subqueries and not any(subquery.required for subquery in subqueries):
            first = subqueries[0]
            subqueries[0] = ResearchSubquery(
                query=first.query,
                purpose=first.purpose,
                required=True
            )

        return subqueries
    
    def _clean_source_types(self, raw_values: Any) -> list[str]:
        if not isinstance(raw_values, list):
            return []
        
        cleaned: list[str] = []
        for value in raw_values:
            text = self._clean_text(value, 80).casefold()
            if not text:
                continue
            if self._contains_url(text):
                continue
            cleaned.append(text)

        return list(dict.fromkeys(cleaned))
    
    def _clean_notes(self, raw_value: Any) -> list[str]:
        if not isinstance(raw_value, list):
            return []
        
        cleaned: list[str] = []
        for value in raw_value:
            text = self._clean_text(value, self.MAX_NOTE_CHARS)
            if not text or self._contains_url(text):
                continue
            cleaned.append(text)

        return list(dict.fromkeys(cleaned))
    
    def _clean_label(self, raw_value: Any) -> str:
        text = self._clean_text(raw_value, 60).casefold()
        text = re.sub(r"[^a-z0-9_ -]+", "", text)
        text = text.replace("-", "_").replace(" ", "_")
        return text.strip("_")
    
    def _clean_text(self, value: Any, max_chars: int) -> str:
        if not isinstance(value, str):
            return ""
        return self._normalize(value)[:max_chars].strip()
    
    def _normalize(self, value: str) -> str:
        return " ".join(value.strip().split())
    
    def _contains_url(self, value: str) -> bool:
        return bool(
            re.search(
                r"https?://|www\.|(?:^|\s)[a-z0-9-]+\.[a-z]{2,}(?:/|\s|$)",
                value,
                re.IGNORECASE,
            )
        )
    

class FallbackResearchPlanner:
    def plan(self, query: str, max_sources: int = 8) -> ResearchPlan:
        normalized = " ".join(query.strip().split())

        return ResearchPlan(
            original_query=normalized,
            question_type="general_research",
            subqueries=[
                ResearchSubquery(
                    query=f"{normalized} official primary source",
                    purpose="Find primary or official evidence",
                ),
                ResearchSubquery(
                    query=f"{normalized} latest facts data",
                    purpose="Find current factual evidence",
                ),
                ResearchSubquery(
                    query=f"{normalized} analysis expert context",
                    purpose="Find analytical context",
                    required=False,
                ),
                ResearchSubquery(
                    query=f"{normalized} criticism caveats limitations",
                    purpose="Find caveats, disagreement, or limitations",
                    required=False,
                ),
            ],
            freshness_sensitive=self._freshness_sensitive(normalized),
            preferred_source_types=[
                "primary source",
                "official source",
                "reputable news",
                "expert analysis",
            ],
            max_sources=max_sources
        )
    
    def _freshness_sensitive(self, query: str) -> bool:
        fresh_terms = {"latest", "recent", "recently", "current", "today", "this year", "2025", "2026"}
        lowered = query.casefold()
        return any(term in lowered for term in fresh_terms)
    
class ResearchPlanner:
    def __init__(
            self,
            llm_client: ResearchPlannerLLM | None = None,
            validator: ResearchPlanValidator | None = None,
            fallback: FallbackResearchPlanner | None = None
    ) -> None:
        self.llm_client = llm_client or ResearchPlannerLLM()
        self.validator = validator or ResearchPlanValidator()
        self.fallback = fallback or FallbackResearchPlanner()

    def plan(self, query: str, max_sources: int = 8) -> ResearchPlan:
        normalized = " ".join(query.strip().split())
        if not normalized:
            return self.fallback.plan(query, max_sources)
        
        try:
            raw_text = self.llm_client.complete_plan(self._prompt(normalized, max_sources))
            raw_plan = self._parse_json(raw_text)
            return self.validator.validate(raw_plan, normalized, max_sources)
        except Exception:
            return self.fallback.plan(normalized, max_sources)
        
    def _parse_json(self, raw_text: str | dict[str, Any]):
        if isinstance(raw_text, dict):
            return raw_text
        
        if not isinstance(raw_text, str):
            raise ResearchPlannerValidationError("LLM response is not a string or JSON object.")
        
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()

        first = text.find("{")
        last = text.rfind("}")

        if first == -1 or last == -1 or last <= first:
            raise ResearchPlannerValidationError("No JSON object found in LLM response.")
        
        return json.loads(text[first:last+1])
    
    def _prompt(self, query: str, max_sources: int) -> str:
        return f"""
You are a research planning module. Create a search plan for the user question.

User question:
{query}

Rules:
- Output JSON only. No markdown.
- Do not answer the question.
- Do not include citations.
- Do not include source URLs.
- Produce 3 to 6 subqueries.
- Each subquery must be useful for search.
- Mark required=false for optional cross-checks or context.
- Use source TYPES, not domains.
- For numeric comparisons, separate metric ambiguity.
- For causal questions, include one subquery to verify the observed trend and separate subqueries for likely drivers.
- Preferred source types examples: official statistics, central bank, regulator, company filings, primary company source, peer-reviewed research, reputable financial news, expert analysis.

JSON schema:
{{
  "question_type": "comparison | causal_recent | policy_impact | market_analysis | literature_review | general_research",
  "freshness_sensitive": true,
  "preferred_source_types": ["official statistics", "reputable news"],
  "ambiguity_notes": ["short note if user wording is ambiguous"],
  "subqueries": [
    {{
      "query": "search query",
      "purpose": "why this search is needed",
      "required": true
    }}
  ]
}}

max_sources: {max_sources}
""".strip()