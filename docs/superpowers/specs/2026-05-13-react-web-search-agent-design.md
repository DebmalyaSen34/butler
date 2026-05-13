# Local ReAct Web Search Agent Design

**Date:** 2026-05-13
**Status:** Pending User Review

## 1. High-Level Architecture & Tech Stack

**Core Philosophy:** 
A pure ReAct (Reason + Act) loop driven by a single local unified LLM. The model iteratively decides between searching the web, rendering URLs to extract content, and synthesizing the final answer to the user.

**Target Engine Constraints:**
- **Inference Backend:** `llama.cpp` + `llama-cpp-python` (OpenAI API compliant server wrapper running on `http://127.0.0.1:3000/completion`).
- **Model:** `gemma-4-E2B` (served locally via the llama.cpp server).
- **Search Backend:** SearXNG (Self-hosted at `http://127.0.0.1:8080/search`) with DuckDuckGo fallback.
- **Fetching:** Hybrid system (Trafilatura for static HTML, Playwright for SPA/JavaScript rendering).

**High-Level Flow Diagram:**
```text
[User Query] -> (Whisper STT) -> Orchestrator (ReAct Loop)
                                      |
                                      v
   +-------------------------------------------------------------+
   |  Loop Iteration:                                            |
   |  1. Prompt LLM with core history + available tools.         |
   |  2. LLM generates "Thought" and "Action" (JSON).            |
   |  3. Execute Tool (e.g., search_web, fetch_url).             |
   |  4. Return "Observation" to LLM context.                    |
   |  *If action is 'finish', exit loop and return answer.       |
   +-------------------------------------------------------------+
                                      |
                            (Kokoro TTS Engine)
                                      |
                                [Audio Output]
```

## 2. Retrieval Pipeline & Components

### 2.1 ReAct Orchestrator
Defined in `core/orchestrator.py` (to be created/integrated into `core/llm.py`), it manages the execution loop and strict context bounding.
- **Async Execution:** Heavy IO-bound tools are wrapped in `asyncio` to prevent blocking the Jarvis main thread.
- **Tools Provided to LLM:**
  - `search_web(query)`: Executes SearXNG search.
  - `fetch_url(url)`: Fetches a rendered HTML to Markdown representation.
  - `finish(answer)`: Ends the loop with a synthesized response and citations.

### 2.2 Hybrid Content Fetching
Defined in `tools/search/hybrid_fetch.py`.
- **Primary:** `Trafilatura`/`aiohttp` for lightning-fast text extraction.
- **Fallback:** If `Trafilatura` yields < 200 characters or detects JS-wall footprints (like `<div id="root"></div>`), it routes to a managed, headless `Playwright` instance to render the DOM before extraction.

## 3. Context-Window Optimization (The "Amnesia" Strategy)

Local models like `gemma-4-E2B` have strict context bounds (typically 8k) and deteriorate when flooded with massive scraped pages.
- **Core Scratchpad:** Retains the original question, prior `Thought`s, and `Action` tracking.
- **Ephemeral Observation:** When `fetch_url` brings back 3,000 tokens of Markdown, it is fed to the LLM. However, on the *next* iteration, the orchestrator replaces that massive block with `[Observation dropped to save memory. Model already processed this.]`. This forces the LLM to extract meaning into its `Thought` block immediately and keeps the rolling context pristine.

## 4. Prompts & Multi-Hop Reasoning

**System Prompt:**
```text
You are Jarvis, an advanced AI computing factual answers based on web evidence.
You are running locally. You run in a loop of Thought, Action, PAUSE, Observation.
Use Thought to describe your reasoning, then Action to execute ONE tool.
Your available tools are:
1. search_web: {"query": "web search query"}
2. fetch_url: {"url": "https://example.com"}
3. finish: {"answer": "final synthesized answer with citations to source URLs"}

RULES:
- Always use the tools to find information if you are not 100% certain.
- If you read a URL and it doesn't contain the answer, Thought about why, then Action: search_web with a DIFFERENT, modified query (e.g., add the year).
- You MUST cite your source URLs in your finish action.
- ONLY output a valid JSON Action block after your Thought. Do not answer directly until you choose the 'finish' action.
```

## 5. Concurrency, Caching & Resilience

- **URL Cache:** In-memory synchronous dictionary inside the orchestrator session. Duplicate URL fetches return immediately.
- **Fail-Safes:** Network errors (403, 500, Timeouts) are caught and returned as the `Observation` (e.g., `Error: 403 Forbidden. Target blocked scraping.`). The LLM reads this and naturally recovers by choosing a different URL from its previous search results.
- **SearXNG Rate Limits:** Hosted via Docker mapping random ports, with a configured list of rotating User-Agents to prevent search engines from blocking the instance permanently.

## 6. Project Folder Structure Additions

```text
jarvis/
  core/
    orchestrator.py      # Main ReAct loop engine
  tools/
    search/
      searxng.py         # SearXNG local client integration
      hybrid_fetch.py    # Trafilatura + Playwright logic
```

## 7. Incremental Implementation Roadmap

1. **MVP (Phase 1):**
   - Rig up the ReAct `while` loop within `core/llm.py` or new `core/orchestrator.py`.
   - Use simple `requests` + `BeautifulSoup` for `fetch_url`.
   - Connect the SearXNG endpoint based on `settings.py`.
   - Verify multi-hop works linearly without context overflow.

2. **Intermediate (Phase 2) - Robustness:**
   - Integrate `Trafilatura` and `Playwright` for hybrid fetching.
   - Introduce full `asyncio` loop wrapping to handle timeout conditions reliably.
   - Implement the "Amnesia" context truncation.

3. **Advanced (Phase 3) - Scale:**
   - Evolve toward State Graph (Node-based) execution if ReAct hallucination loops persist natively in `gemma-4-E2B`.
   - Connect Redis for cross-session URL caching.
   - Add local cross-encoder re-ranking internally inside `hybrid_fetch` to extract exact matching paragraphs instead of naive truncation.
