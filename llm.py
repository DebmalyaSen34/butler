import requests
import logging
from config.settings import LLAMA_CPP_URL, PROMPT_TEMPLATE
from tools.registry import TOOL_PROMPT, execute_tool

logger = logging.getLogger(__name__)

def generate_response(prompt: str) -> str:
    print(f"\n[Thinking...] Gemma is processing: '{prompt}'")

    combined_prompt = f"{TOOL_PROMPT}\n\n{prompt}"
    formatted_prompt = PROMPT_TEMPLATE.format(prompt=combined_prompt)

    payload = {
        "prompt": formatted_prompt,
        # "n_predict": -1,
        "temperature": 0.3,
        "stop": ["<end_of_turn>", "<start_of_turn>", "User:"]
    }

    try:
        response = requests.post(LLAMA_CPP_URL, json=payload)
        response.raise_for_status()


        reply = response.json().get("content", "").strip()

        tool_result = execute_tool(reply)
        if tool_result:
            logger.info(f"Tool execution result: {tool_result}")
            return f"I have executed a tool for you. {tool_result}"
        print(f"\b[Gemma]: {reply}")

        return reply
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return "I am having trouble connecting to my brain."

if __name__ == "__main__":
    # test_prompt = "Write an optimized cpp code to solve house robber problem in a file name house_robber_optimized.cpp"
    test_prompt = "Write a html file with name website.html that contains a clock in the center that shows the current time in analog. The theme of the website is Dracula theme."
    print(generate_response(test_prompt))
