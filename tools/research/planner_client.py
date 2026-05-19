from __future__ import annotations
import json
from typing import Any
import requests
from config.settings import LLAMA_CPP_URL

class ResearchPlannerLLM:
    def __init__(self, url: str = LLAMA_CPP_URL, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout

    def complete_plan(self, prompt: str) -> str:
        payload = {
            "prompt": prompt,
            "stream": False,
            "temperature": 0.1,
            "stop": ["<end_of_turn>", "<start_of_turn>", "User:", "Current User:"],
        }

        response = requests.post(
            self.url,
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()

        data: dict[str, Any] = response.json()

        if isinstance(data.get("content"), str):
            return data["content"]
        
        if isinstance(data.get("response"), str):
            return data["response"]
        
        if isinstance(data.get("choices"), list) and data["choices"]:
            choice = data["choices"][0]
            if isinstance(choice.get("text"), dict):
                return str(choice.get("text") or choice.get("message", {}).get("content", "") or "")
        
        return json.dumps(data)