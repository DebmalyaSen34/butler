from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tools.memory_ops import remember_fact, retrieve_facts
from tools.system_ops import open_app, get_time
from tools.file_ops import create_file
from tools.web_search import search_web
from utils.parser import extract_json


@dataclass(frozen=True)
class ToolDefinition:
    function: Callable[..., Any]
    description: str
    permission: str = "safe"


AVAILABLE_TOOLS = {
    "create_file": ToolDefinition(create_file, "Creates or overwrites a file in the current project.", "risky"),
    "search_web": ToolDefinition(search_web, "Searches the web using DuckDuckGo and fetches page content.", "safe"),
    "remember_fact": ToolDefinition(remember_fact, "Saves a user fact or preference into long-term memory.", "safe"),
    "retrieve_facts": ToolDefinition(retrieve_facts, "Retrieves saved facts and preferences.", "safe"),
    "open_app": ToolDefinition(open_app, "Opens a macOS application.", "risky"),
    "get_time": ToolDefinition(get_time, "Returns the current system time.", "safe"),
}

TOOL_PROMPT = """
You have access to the following tools:
1. create_file(filename: str, content: str) - Creates or overwrites a file. Permission: risky, user confirmation required.
2. search_web(query: str, num_results: int = 3) - Searches the web using DuckDuckGo and dynamically scrapes target page content. Permission: safe.
3. remember_fact(fact: str, category: str = "facts" | "preferences") - Saves a user fact or preference into long-term memory. Permission: safe.
4. retrieve_facts(category: str = "facts" | "preferences") - Retrieves saved facts and preferences. Permission: safe.
5. open_app(app_name: str) - Opens a macOS application (e.g., 'Safari', 'Calculator'). Permission: risky, user confirmation required.
6. get_time() - Returns the current system time. Permission: safe.

If you need to use a tool, you MUST respond in the exact JSON format. 
Example (create_file):
{"tool": "create_file", "args": {"filename": "hello.cpp", "content": "#include <iostream>\\nint main() {\\n    std::cout << \\"Hello\\" << std::endl;\\n    return 0;\\n}"}}
Example (open_app):
{"tool": "open_app", "args": {"app_name": "Preview"}}

CRITICAL RULES FOR JSON:
- The entire JSON object MUST be on a single line.
- Do NOT use raw newlines inside the content string. Use the literal characters \\n.
- You MUST escape all double quotes inside the content string with \\".

If you do not need a tool, just respond with conversational text.
"""

def execute_tool(
    llm_response: str,
    confirm_tool: Callable[[str, dict[str, Any], str], bool] | None = None,
) -> str | None:
    # call_data = extract_json(llm_response)
    call_data = extract_json(llm_response)

    if not isinstance(call_data, dict) or "tool" not in call_data:
        return None

    tool_name = call_data.get("tool")
    args = call_data.get("args", {})

    if tool_name in AVAILABLE_TOOLS:
        try:
            tool = AVAILABLE_TOOLS[tool_name]
            if tool.permission == "risky":
                if confirm_tool is None:
                    return f"Tool '{tool_name}' needs confirmation before it can run."
                if not confirm_tool(tool_name, args, tool.permission):
                    return f"Tool '{tool_name}' was cancelled by the user."

            result = tool.function(**args)
            return f"Tool '{tool_name}' executed successfully. Result: {result}"
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    return f"Tool '{tool_name}' is not available."
