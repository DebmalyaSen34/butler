from __future__ import annotations

import logging

import requests

from config.settings import SEARXNG_URL

logger = logging.getLogger(__name__)


def search_searxng(query: str, num_results: int = 5) -> list[dict[str, str]]:
    try:
        response = requests.get(
            SEARXNG_URL,
            params={"q": query, "format": "json", "engines": "duckduckgo"},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        return [
            {
                "title": str(result.get("title", "")),
                "url": str(result.get("url", "")),
                "snippet": str(result.get("content", "")),
            }
            for result in data.get("results", [])[:num_results]
        ]
    except Exception as exc:
        logger.error("SearXNG search failed: %s", exc)
        return [{"error": f"Search failed: {exc}"}]
