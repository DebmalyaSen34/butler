import requests
import logging
import time
import json
from datetime import datetime
from collections.abc import Callable
from typing import Any
from config.settings import PROMPT_TEMPLATE, OLLAMA_MODEL, OLLAMA_URL, LLAMA_CPP_URL
from tools.registry import TOOL_PROMPT, execute_tool
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

conversation_history = []
MAX_HISTORY = 10

def clean_token(token: str) -> str:
    tags = ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:", "[Gemma]:", "model\n"]
    for tag in tags:
        token = token.replace(tag, "")
    return token

def generate_response(
    prompt: str,
    confirm_tool: Callable[[str, dict[str, Any], str], bool] | None = None,
    on_state: Callable[[str], None] | None = None,
):
    global conversation_history

    start_time = time.time()
    think_end = None
    token_count = 0
    tools_used = []

    # if not hasattr(generate_response, "_mode"):
    #     # We can just skip console prints that are redundant, or let them be but remove the tags that break text.
    #     pass
        
    # console.print(f"\n[dim italic]\\[Thinking...] Gemma is processing: '{prompt}'[/dim italic]")
    if on_state:
        on_state("Thinking")

    now = datetime.now().strftime("%B %d, %Y")

    history_text = "\n".join(conversation_history)

    if history_text:
        combined_prompt = f"{TOOL_PROMPT}\n\nToday's Date: {now}\n\nPrevious Conversation:\n{history_text}\n\nCurrent User: {prompt}"
    else:
        combined_prompt = f"{TOOL_PROMPT}\n\nToday's Date: {now}\n\nCurrent User: {prompt}"

    formatted_prompt = PROMPT_TEMPLATE.format(prompt=combined_prompt)

    payload = {
        # "model": OLLAMA_MODEL,
        "prompt": formatted_prompt,
        "stream": True,
        "temperature": 0.3,
        "stop": ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:"]
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
                            yield current_sentence.strip()
                            current_sentence = ""

                    except json.JSONDecodeError:
                        continue

        if current_sentence.strip() and not is_tool_call:
            yield current_sentence.strip()

        reply = full_reply.strip()

        if is_tool_call:
            if on_state:
                on_state("Using tool")

            try:
                tool_data = json.loads(reply)
                tools_used.append(tool_data.get("tool", "unknown"))
            except json.JSONDecodeError:
                pass

            tool_result = execute_tool(reply, confirm_tool=confirm_tool)
            if tool_result:
                logger.info(f"Tool execution result: {tool_result}")
                # console.print(f"[dim italic]\\[Tool Result]: Executed successfully. Summarizing...[/dim italic]")
                
                follow_up_prompt = f"The user asked: '{prompt}'.\n\nThe previous tool returned this result:\n{tool_result}\n\nBased on the tool result, answer the user's question clearly and concisely. Do not explain what tool you used. Do not repeat my prompt. Just give the answer."
                follow_up_payload = {
                    # "model": OLLAMA_MODEL,
                    "prompt": PROMPT_TEMPLATE.format(prompt=follow_up_prompt),
                    "stream": True,
                    "temperature": 0.3,
                    "stop": ["<end_of_turn>", "<start_of_turn>", "User:"]
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
                                    yield follow_up_sentence.strip()
                                    follow_up_sentence = ""

                            except json.JSONDecodeError:
                                continue
                
                if follow_up_sentence.strip():
                    yield follow_up_sentence.strip()
                
                # Suppress the redundant whole-message print since `text` mode chunks it out and `voice` uses audio
                # console.print(f"[bold cyan]\\[Gemma]:[/bold cyan] {final_reply.strip()}")
                
                conversation_history.append(f"User: {prompt}")
                conversation_history.append(f"Assistant (used tool, result: {str(tool_result)[:100]}...): {final_reply.strip()}")
                reply = final_reply.strip()
        else:
            conversation_history.append(f"User: {prompt}")
            conversation_history.append(f"Assistant: {reply}")
        if len(conversation_history) > MAX_HISTORY:
                conversation_history = conversation_history[-MAX_HISTORY:]
        
        # if not is_tool_call:
        #     # Suppress the redundant whole-message print
        #     # console.print(f"[bold cyan]\\[Gemma]:[/bold cyan] {reply}")

        #     conversation_history.append(f"User: {prompt}")
        #     conversation_history.append(f"Assistant: {reply}")
        #     if len(conversation_history) > MAX_HISTORY:
        #         conversation_history = conversation_history[-MAX_HISTORY:]

        # Metrics
        end_time = time.time()
        think_time = (think_end - start_time) if think_end else 0
        gen_time = (end_time - start_time) - think_time if think_time else 1
        total_time = end_time - start_time
        tps = token_count / gen_time if gen_time > 0 else 0

        tools_str = ", ".join(tools_used) if tools_used else "None"

        metrics = f"\n\n[bold dim]Run Metrics:[/bold dim] Total Time: {total_time:.2f}s | Think Time: {think_time:.2f}s | Gen Time: {gen_time:.2f}s | Tokens: {token_count} | TPS: {tps:.2f} | Tools Used: {tools_str}"
        console.print(metrics)
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        yield "I am having trouble connecting to my brain."
