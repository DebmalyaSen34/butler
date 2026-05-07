import requests
import logging
from config.settings import LLAMA_CPP_URL, PROMPT_TEMPLATE
from tools.registry import TOOL_PROMPT, execute_tool
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

conversation_history = []
MAX_HISTORY = 10

def generate_response(prompt: str) -> str:
    global conversation_history
    console.print(f"\n[dim italic]\\[Thinking...] Gemma is processing: '{prompt}'[/dim italic]")

    history_text = "\n".join(conversation_history)
    if history_text:
        combined_prompt = f"{TOOL_PROMPT}\n\nPrevious Conversation:\n{history_text}\n\nCurrent User: {prompt}"
    else:
        combined_prompt = f"{TOOL_PROMPT}\n\nCurrent User: {prompt}"

    formatted_prompt = PROMPT_TEMPLATE.format(prompt=combined_prompt)

    payload = {
        "prompt": formatted_prompt,
        # "n_predict": -1,
        "temperature": 0.3,
        "stop": ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:"]
    }

    try:
        response = requests.post(LLAMA_CPP_URL, json=payload)
        response.raise_for_status()


        reply = response.json().get("content", "").strip()

        tool_result = execute_tool(reply)
        if tool_result:
            logger.info(f"Tool execution result: {tool_result}")
            console.print(f"[dim italic]\\[Tool Result]: Executed successfully. Summarizing...[/dim italic]")
            # Feed tool result back to the LLM to get a human-friendly summary
            follow_up_prompt = f"The tool returned the following information:\n\n{tool_result}\n\nPlease summarize this context concisely for the user."
            follow_up_payload = {
                "prompt": PROMPT_TEMPLATE.format(prompt=follow_up_prompt),
                "temperature": 0.3,
                "stop": ["<end_of_turn>", "<start_of_turn>", "User:"]
            }
            
            follow_up_response = requests.post(LLAMA_CPP_URL, json=follow_up_payload)
            follow_up_response.raise_for_status()
            final_reply = follow_up_response.json().get("content", "").strip()
            
            console.print(f"[bold cyan]\\[Gemma]:[/bold cyan] {final_reply}")
            
            conversation_history.append(f"User: {prompt}")
            conversation_history.append(f"Assistant (used tool, result: {str(tool_result)[:100]}...): {final_reply}")
            conversation_history = conversation_history[-MAX_HISTORY:]

            return final_reply
        
        console.print(f"[bold cyan]\\[Gemma]:[/bold cyan] {reply}")

        conversation_history.append(f"User: {prompt}")
        conversation_history.append(f"Assistant: {reply}")
        conversation_history = conversation_history[-MAX_HISTORY:]

        return reply
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return "I am having trouble connecting to my brain."
