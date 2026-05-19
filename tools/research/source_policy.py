from __future__ import annotations

from urllib.parse import urlparse


OFFICIAL_DOMAIN_HINTS = {
    ".gov",
    ".gov.in",
    ".gov.uk",
    ".europa.eu",
    "who.int",
    "imf.org",
    "worldbank.org",
    "oecd.org",
    "bis.org",
    "wto.org",
    "un.org",
    "ecb.europa.eu",
    "federalreserve.gov",
    "rbi.org.in",
    "sec.gov",
    "data.gov",
}

ACADEMIC_DOMAIN_HINTS = {
    ".edu",
    "arxiv.org",
    "ssrn.com",
    "nature.com",
    "science.org",
    "springer.com",
    "sciencedirect.com",
    "jstor.org",
    "pubmed.ncbi.nlm.nih.gov",
}

REPUTABLE_NEWS_DOMAIN_HINTS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "ft.com",
    "wsj.com",
    "economist.com",
    "bloomberg.com",
    "cnbc.com",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
}

FINANCIAL_NEWS_DOMAIN_HINTS = {
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "cnbc.com",
    "marketwatch.com",
    "moneycontrol.com",
    "business-standard.com",
    "livemint.com",
}

COMPANY_SOURCE_HINTS = {
    "investor.",
    "investors.",
    "ir.",
    "/investor-relations",
    "/newsroom",
    "/press",
    "/press-release",
    "/annual-report",
}

LOW_QUALITY_HINTS = {
    "pinterest.",
    "quora.com",
    "reddit.com",
    "medium.com",
    "blogspot.",
    "wordpress.",
    "fandom.com",
    "answers.com",
}


class SourcePolicy:
    def score_url(self, url: str, preferred_source_types: list[str] | None = None) -> float:
        domain = self.domain(url)
        lowered_url = url.casefold()
        preferred = {source_type.casefold() for source_type in (preferred_source_types or [])}

        score = 0.0

        if self._matches_any(domain, OFFICIAL_DOMAIN_HINTS):
            score += 1.5
        if self._matches_any(domain, ACADEMIC_DOMAIN_HINTS):
            score += 1.25
        if self._matches_any(domain, REPUTABLE_NEWS_DOMAIN_HINTS):
            score += 1.0
        if self._matches_any(domain, FINANCIAL_NEWS_DOMAIN_HINTS):
            score += 1.0
        if self._has_any(lowered_url, COMPANY_SOURCE_HINTS):
            score += 1.25
        if self._matches_any(domain, LOW_QUALITY_HINTS):
            score -= 1.0

        if self._prefers_official(preferred) and self._matches_any(domain, OFFICIAL_DOMAIN_HINTS):
            score += 2.0
        if self._prefers_academic(preferred) and self._matches_any(domain, ACADEMIC_DOMAIN_HINTS):
            score += 2.0
        if self._prefers_news(preferred) and self._matches_any(domain, REPUTABLE_NEWS_DOMAIN_HINTS):
            score += 1.5
        if self._prefers_financial(preferred) and self._matches_any(domain, FINANCIAL_NEWS_DOMAIN_HINTS):
            score += 1.5
        if self._prefers_company(preferred) and self._has_any(lowered_url, COMPANY_SOURCE_HINTS):
            score += 2.0

        return score

    def source_label(self, url: str) -> str:
        domain = self.domain(url)
        lowered_url = url.casefold()

        if self._matches_any(domain, OFFICIAL_DOMAIN_HINTS):
            return "official"
        if self._has_any(lowered_url, COMPANY_SOURCE_HINTS):
            return "primary company source"
        if self._matches_any(domain, ACADEMIC_DOMAIN_HINTS):
            return "academic"
        if self._matches_any(domain, FINANCIAL_NEWS_DOMAIN_HINTS):
            return "financial news"
        if self._matches_any(domain, REPUTABLE_NEWS_DOMAIN_HINTS):
            return "reputable news"
        if self._matches_any(domain, LOW_QUALITY_HINTS):
            return "low quality"
        return "unknown"

    def domain(self, url: str) -> str:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc.casefold().removeprefix("www.")

    def _matches_any(self, domain: str, hints: set[str]) -> bool:
        return any(domain == hint or domain.endswith(hint) for hint in hints)

    def _has_any(self, text: str, hints: set[str]) -> bool:
        return any(hint in text for hint in hints)

    def _prefers_official(self, preferred: set[str]) -> bool:
        return any(
            term in source_type
            for source_type in preferred
            for term in ("official", "statistics", "central bank", "regulator", "government", "international organization")
        )

    def _prefers_academic(self, preferred: set[str]) -> bool:
        return any(
            term in source_type
            for source_type in preferred
            for term in ("academic", "peer-reviewed", "research paper", "scholarly")
        )

    def _prefers_news(self, preferred: set[str]) -> bool:
        return any(
            term in source_type
            for source_type in preferred
            for term in ("news", "reputable news", "journalism")
        )

    def _prefers_financial(self, preferred: set[str]) -> bool:
        return any(
            term in source_type
            for source_type in preferred
            for term in ("financial", "market", "business news")
        )

    def _prefers_company(self, preferred: set[str]) -> bool:
        return any(
            term in source_type
            for source_type in preferred
            for term in ("company", "filing", "investor", "primary company")
        )