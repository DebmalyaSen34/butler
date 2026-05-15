from __future__ import annotations

from typing import Protocol

import requests
from ddgs import DDGS

from tools.search.models import SearchResult


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[SearchResult]:
        raise NotImplementedError


class SearxngProvider:
    name = "searxng"

    def __init__(self, search_url: str, timeout: float = 5.0) -> None:
        self.search_url = search_url
        self.timeout = timeout

    def search(self, query: str, limit: int) -> list[SearchResult]:
        response = requests.get(
            self.search_url,
            params={"q": query, "format": "json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        raw_results = payload.get("results", [])
        return [
            SearchResult(
                title=str(item.get("title") or "No Title"),
                url=str(item.get("url") or ""),
                snippet=str(item.get("content") or ""),
                provider=self.name,
                rank=index,
                query=query,
            )
            for index, item in enumerate(raw_results[:limit], start=1)
            if item.get("url")
        ]


class DdgsProvider:
    name = "ddgs"

    def search(self, query: str, limit: int) -> list[SearchResult]:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=limit))
        return [
            SearchResult(
                title=str(item.get("title") or "No Title"),
                url=str(item.get("href") or ""),
                snippet=str(item.get("body") or ""),
                provider=self.name,
                rank=index,
                query=query,
            )
            for index, item in enumerate(raw_results[:limit], start=1)
            if item.get("href")
        ]


class ProviderRunner:
    def __init__(self, providers: list[SearchProvider], min_results: int = 2) -> None:
        self.providers = providers
        self.min_results = min_results

    def search(self, queries: list[str], limit: int) -> tuple[list[SearchResult], list[str]]:
        all_results: list[SearchResult] = []
        errors: list[str] = []
        seen_urls: set[str] = set()

        for query in queries:
            query_results: list[SearchResult] = []
            for provider in self.providers:
                try:
                    provider_results = provider.search(query, limit)
                except Exception as exc:
                    errors.append(f"{provider.name} failed for '{query}': {exc}")
                    continue

                for result in provider_results:
                    if result.url in seen_urls:
                        continue
                    seen_urls.add(result.url)
                    query_results.append(result)
                    all_results.append(result)

                if len(query_results) >= self.min_results:
                    break

        return all_results[: max(limit, len(queries))], errors
