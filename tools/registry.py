from tools.file_ops import create_file
from tools.web_search import search_web
from utils.parser import extract_json

AVAILABLE_TOOLS = {
    "create_file": create_file,
    "search_web": search_web
}

TOOL_PROMPT = """
You have access to the following tools:
1. create_file(filename: str, content: str) - Creates a file.
2. search_web(query: str, num_results: int = 3) - Searches the web using SearxNG.

If you need to use a tool, you MUST respond in the exact JSON format. 
Example (create_file):
{"tool": "create_file", "args": {"filename": "hello.cpp", "content": "#include <iostream>\\nint main() {\\n    std::cout << \\"Hello\\" << std::endl;\\n    return 0;\\n}"}}
Example (search_web):
{"tool": "search_web", "args": {"query": "weather in London", "num_results": 3}}

CRITICAL RULES FOR JSON:
- The entire JSON object MUST be on a single line.
- Do NOT use raw newlines inside the content string. Use the literal characters \\n.
- You MUST escape all double quotes inside the content string with \\".

If you do not need a tool, just respond with conversational text.
"""

def execute_tool(llm_response: str) -> str | None:
    # call_data = extract_json(llm_response)
    call_data = extract_json(llm_response)

    if not isinstance(call_data, dict) or "tool" not in call_data:
        return None

    tool_name = call_data.get("tool")
    args = call_data.get("args", {})

    if tool_name in AVAILABLE_TOOLS:
        try:
            result = AVAILABLE_TOOLS[tool_name](**args)
            return f"Tool '{tool_name}' executed successfully. Result: {result}"
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    return f"Tool '{tool_name}' is not available."
