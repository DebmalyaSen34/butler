from __future__ import annotations

import json
import logging

import core.llm
import tools.registry

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Jarvis, an advanced AI computing factual answers based on web evidence.
You are running locally. You run in a loop of Thought, Action, PAUSE, Observation.
Use Thought to describe your reasoning, then Action to execute ONE tool.
Your available tools are:
1. {"search_web": {"query": "web search query"}}
2. {"fetch_url": {"url": "https://example.com"}}
3. {"finish": {"answer": "final synthesized answer with citations to source URLs"}}

RULES:
- If you don't know the answer, use a tool.
- ONLY output a valid JSON Action block after your Thought.
- Proactive Searching: If a query is broad or ambiguous, formulate a general search query and execute it. NEVER ask the user what specific topic they want.
- Unknowns & Cutoffs: Always search for obscure terms, specific names, or recent events. If you feel the urge to say "as of my last update" or "I don't have real time info", STOP. Execute a search_web action immediately.
- Fact Extraction: When reviewing search results, extract hard facts (e.g., "Team X won 3-0"). Do NOT describe the articles (e.g., avoid "This article discusses...").
- Deep Reading: If search snippets hint at the answer but lack the specific facts needed, you MUST execute a fetch_url action to read the full article before using the finish action.
- GOOD Example:
  Thought: The user wants broad tech news. I shouldn't ask which field of tech. I will search for general tech news.
  Action: {"search_web": {"query": "latest technology news headlines today"}}
- BAD Example: 
  Thought: The user didn't specify which sports they like.
  Action: {"finish": {"answer": "Which sport are you interested in?"}}
- Example:
Thought: I need to search.
Action: {"search_web": {"query": "barcelona total goals"}}
"""


def extract_action(llm_output: str) -> dict:
    try:
        if "Action:" not in llm_output:
            return {}
        json_text = llm_output.split("Action:", 1)[1].strip()
        start = json_text.find("{")
        end = json_text.rfind("}") + 1
        if start == -1 or end == 0:
            return {}
        return json.loads(json_text[start:end])
    except json.JSONDecodeError:
        return {}


def _generate_text(prompt: str) -> str:
    response = core.llm.generate_response(prompt, print_metrics=False)
    if isinstance(response, str):
        return response
    return "".join(response)


def run_react_loop(query: str, max_iterations: int = 5) -> str:
    context = f"{SYSTEM_PROMPT}\n\nQuestion: {query}\n"
    last_observation: str | None = None

    for _ in range(max_iterations):
        response = _generate_text(context)
        context += f"{response}\n"

        action_dict = extract_action(response)
        if not action_dict:
            context += "Observation: Error: Invalid JSON Action format. Try again using exactly one tool in JSON.\n"
            continue

        if "finish" in action_dict:
            return tools.registry.execute_react_tool(action_dict)

        observation = tools.registry.execute_react_tool(action_dict)
        if last_observation:
            context = context.replace(
                f"Observation: {last_observation}\n",
                "Observation: [Observation dropped to save memory. Model already processed this.]\n",
            )
        context += f"Observation: {observation}\n"
        last_observation = observation

    return "Error: Maximum thinking iterations reached without final answer."
