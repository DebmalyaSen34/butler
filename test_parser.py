from utils.parser import extract_json

text = '{"tool": "search_web", "args": {"query": "latest news on AI"}}\n</start_of_turn>'
res = extract_json(text)
print("Result:", res)
