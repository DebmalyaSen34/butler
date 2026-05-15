from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_url_content_mvp(url: str, max_chars: int = 3000) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=8,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.extract()

        elements = soup.find_all(["p", "h1", "h2", "h3", "li"])
        text = " ".join(element.get_text().strip() for element in elements if element.get_text().strip())
        text = " ".join(text.split())

        if not text:
            return "Error: Page contained no readable text (might require JavaScript)."
        if len(text) > max_chars:
            return text[:max_chars] + "... [TRUNCATED]"
        return text
    except Exception as exc:
        logger.debug("Failed to fetch content from %s: %s", url, exc)
        return f"Error: Failed to fetch content: {exc}"
