import requests
import logging
import time
import json
from datetime import datetime
from collections.abc import Callable
from typing import Any
from config.settings import ASSISTANT_PERSONA, PROMPT_TEMPLATE, LLAMA_CPP_URL
from tools.registry import TOOL_PROMPT, execute_tool
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

conversation_history = []
MAX_HISTORY = 10

def clean_token(token: str) -> str:
    tags = ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:", "[Gemma]:", "model\n", "</start_of_turn>", "</end_of_turn>"]
    for tag in tags:
        token = token.replace(tag, "")
    return token

def generate_response(
    prompt: str,
    confirm_tool: Callable[[str, dict[str, Any], str], bool] | None = None,
    on_state: Callable[[str], None] | None = None,
    on_metrics: Callable[[dict[str, Any]], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    print_metrics: bool = True,
):
    global conversation_history

    start_time = time.time()
    think_end = None
    token_count = 0
    tools_used = []

    if on_state:
        on_state("Thinking")

    now = datetime.now().strftime("%B %d, %Y")

    history_text = "\n".join(conversation_history)

    if history_text:
        combined_prompt = (
            f"{ASSISTANT_PERSONA}\n\n"
            f"{TOOL_PROMPT}\n\n"
            f"Today's Date: {now}\n\n"
            f"Previous Conversation:\n{history_text}\n\n"
            f"Current User: {prompt}"
        )
    else:
        combined_prompt = (
            f"{ASSISTANT_PERSONA}\n\n"
            f"{TOOL_PROMPT}\n\n"
            f"Today's Date: {now}\n\n"
            f"Current User: {prompt}"
        )

    formatted_prompt = PROMPT_TEMPLATE.format(prompt=combined_prompt)

    payload = {
        "prompt": formatted_prompt,
        "stream": True,
        "temperature": 0.3,
        "stop": ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:", "</start_of_turn>", "</end_of_turn>"]
    }

    try:
        response = requests.post(LLAMA_CPP_URL, json=payload, stream=True)

        response.raise_for_status()

        full_reply = ""
        current_sentence = ""
        is_tool_call = False

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        token = data.get("content", "")

                        if think_end is None and token:
                            think_end = time.time()
                        token_count+=1

                        token = clean_token(token)
                        full_reply += token
                        current_sentence += token
                        
                        if full_reply.strip() and full_reply.strip()[0] == "{":
                            is_tool_call = True

                        if not is_tool_call and any(p in token for p in [".", "?", "!"]):
                            # Simple sentence split
                            yield clean_token(current_sentence.strip())
                            current_sentence = ""

                    except json.JSONDecodeError:
                        continue

        if current_sentence.strip() and not is_tool_call:
            yield clean_token(current_sentence.strip())

        reply = full_reply.strip()

        if is_tool_call:
            if on_state:
                on_state("Using tool")

            tool_name = "unknown"
            try:
                tool_data = json.loads(reply)
                tool_name = tool_data.get("tool", "unknown")
                tools_used.append(tool_name)
            except json.JSONDecodeError:
                pass

            tool_result = execute_tool(reply, confirm_tool=confirm_tool)
            if tool_result:
                if on_tool_result:
                    on_tool_result(tool_name, tool_result)
                
                follow_up_prompt = (
                    f"{ASSISTANT_PERSONA}\n\n"
                    f"The user asked: '{prompt}'.\n\n"
                    f"The previous tool returned this result:\n{tool_result}\n\n"
                    "Based on the tool result, extract the hard facts and answer the user directly. "
                    "Do NOT summarize the search result descriptions (e.g., avoid 'This article talks about...'). "
                    "If the search result does not contain the answer, say so. "
                    "Be clear and concise. Do not explain what tool you used. "
                    "Do not repeat my prompt. Just give the answer."
                )
                follow_up_payload = {
                    "prompt": PROMPT_TEMPLATE.format(prompt=follow_up_prompt),
                    "stream": True,
                    "temperature": 0.3,
                    "stop": ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:", "</start_of_turn>", "</end_of_turn>"]
                }
                
                follow_up_response = requests.post(LLAMA_CPP_URL, json=follow_up_payload, stream=True)
                follow_up_response.raise_for_status()
                
                final_reply = ""
                follow_up_sentence = ""
                for line in follow_up_response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                token = data.get("content", "")
                                token_count+=1
                                token = clean_token(token)
                                final_reply += token
                                follow_up_sentence += token
                                if any(p in token for p in [".", "?", "!"]):
                                    yield clean_token(follow_up_sentence.strip())
                                    follow_up_sentence = ""

                            except json.JSONDecodeError:
                                continue
                
                if follow_up_sentence.strip():
                    yield clean_token(follow_up_sentence.strip())
                
                conversation_history.append(f"User: {prompt}")
                reply = clean_token(final_reply.strip())
                conversation_history.append(f"Assistant: {reply}")
        else:
            conversation_history.append(f"User: {prompt}")
            conversation_history.append(f"Assistant: {reply}")
        if len(conversation_history) > MAX_HISTORY:
                conversation_history = conversation_history[-MAX_HISTORY:]
        
        end_time = time.time()
        think_time = (think_end - start_time) if think_end else 0
        gen_time = (end_time - start_time) - think_time if think_time else 1
        total_time = end_time - start_time
        tps = token_count / gen_time if gen_time > 0 else 0

        tools_str = ", ".join(tools_used) if tools_used else "None"

        metrics_data = {
            "total_time": total_time,
            "think_time": think_time,
            "gen_time": gen_time,
            "tokens": token_count,
            "tps": tps,
            "tools_used": tools_str,
        }
        if on_metrics:
            on_metrics(metrics_data)
        if print_metrics:
            metrics = f"\n\n[bold dim]Run Metrics:[/bold dim] Total Time: {total_time:.2f}s | Think Time: {think_time:.2f}s | Gen Time: {gen_time:.2f}s | Tokens: {token_count} | TPS: {tps:.2f} | Tools Used: {tools_str}"
            console.print(metrics)
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        yield "I am having trouble connecting to my brain."
