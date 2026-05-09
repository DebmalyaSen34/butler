import logging
import concurrent.futures
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

logger = logging.getLogger(__name__)

def fetch_url_content(url: str, timeout: int = 5) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text from paragraphs
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        text = " ".join(text.split())  # Clean up whitespace
        
        # Truncate to reasonable length to avoid blowing up context window
        return text[:1500] + ("..." if len(text) > 1500 else "")
    except Exception as e:
        logger.debug(f"Failed to fetch content from {url}: {e}")
        return ""

def search_web(query: str, num_results: int = 3) -> str:
    """
    Search the web using DuckDuckGo and intelligently scrape target URLs for content.
    """
    try:
        with DDGS() as ddgs:
            # fetch results
            ddgs_results = list(ddgs.text(query, max_results=num_results))
        
        if not ddgs_results:
            return f"No search results found for '{query}'."

        urls = [res.get('href') for res in ddgs_results if res.get('href')]
        scraped_contents = {}
        
        if urls:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as executor:
                future_to_url = {executor.submit(fetch_url_content, url): url for url in urls}
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    scraped_contents[url] = future.result()

        formatted_results = []
        for i, res in enumerate(ddgs_results):
            title = res.get('title', 'No Title')
            url = res.get('href', 'No URL')
            snippet = res.get('body', '')
            content = scraped_contents.get(url, '')
            
            res_text = f"Result {i+1}:\nTitle: {title}\nURL: {url}\nSnippet: {snippet}"
            if content:
                res_text += f"\nDeep Content: {content}"
            formatted_results.append(res_text)
            
        return "\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Failed to search web: {e}")
        return f"Error occurred during web search: {e}"
