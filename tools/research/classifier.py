import re

COMPARISON_TERMS = {"compare", "versus", "vs", "difference", "better", "larger"}
CAUSAL_TERMS={"why", "cause", "caused", "reason", "reasons", "driver", "drivers", "falling", "rising"}
ANALYSIS_TERMS={"analysis", "report", "breakdown", "impact", "effects", "outlook", "trend"}
FRESH_TERMS={"latest", "recent", "recently", "current", "today", "this year", "2025", "2026"}
DOMAIN_TERMS={
    "gdp", "inflation", "currency", "rupee", "dollar", "exchange rate",
    "stock", "market", "oil", "trade", "deficit", "rbi", "fed",
    "policy", "election", "regulation", "war", "tariff"
}

class ResearchClassifier:
    def _has_term(self, text: str, terms: set[str]) -> bool:
        pattern = r'\b(' + '|'.join(re.escape(t) for t in terms) + r')\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def needs_research(self, query: str) -> bool:
        if self._has_term(query, COMPARISON_TERMS):
            return True
        if self._has_term(query, CAUSAL_TERMS):
            return True
        if self._has_term(query, ANALYSIS_TERMS):
            return True
        if self._has_term(query, FRESH_TERMS) and self._has_term(query, DOMAIN_TERMS):
            return True
        return False