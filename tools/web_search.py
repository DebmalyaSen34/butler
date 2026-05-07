import requests
import logging
from config.settings import SEARXNG_URL

logger = logging.getLogger(__name__)

def search_web(query: str, num_results: int = 3) -> str:
    """
    Search the web using SearxNG.
    """
    try:
        response = requests.get(
            SEARXNG_URL,
            params={
                "q": query,
                "format": "json",
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])[:num_results]
        
        if not results:
            return f"No search results found for '{query}'."

        formatted_results = []
        for i, res in enumerate(results):
            title = res.get("title", "No Title")
            content = res.get("content", "No Content")
            formatted_results.append(f"{i+1}. {title}: {content}")
            
        return "\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Failed to search web: {e}")
        return f"Error occurred during web search: {e}"
