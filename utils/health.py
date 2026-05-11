from __future__ import annotations

from dataclasses import dataclass

import requests
import speech_recognition as sr

from config.settings import OLLAMA_URL, OLLAMA_MODEL, SEARXNG_URL, SETTINGS, LLAMA_CPP_URL

@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str


def run_startup_health_checks() -> list[HealthCheck]:
    timeout = float(SETTINGS["services"].get("health_timeout_seconds", 1.5))
    checks = [_check_microphone()]
    checks.append(_check_http_service("llama.cpp", LLAMA_CPP_URL, timeout, method="post"))
    checks.append(_check_http_service("SearxNG", SEARXNG_URL, timeout, method="get"))
    return checks


def _check_microphone() -> HealthCheck:
    try:
        names = sr.Microphone.list_microphone_names()
    except Exception as exc:
        return HealthCheck("Microphone", False, str(exc))

    if not names:
        return HealthCheck("Microphone", False, "No microphone devices reported by SpeechRecognition.")

    return HealthCheck("Microphone", True, f"{len(names)} input device(s) visible.")


def _check_http_service(name: str, url: str, timeout: float, *, method: str) -> HealthCheck:
    try:
        if method == "post":
            response = requests.post(url, json={"prompt": "", "n_predict": 1}, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)
    except Exception as exc:
        return HealthCheck(name, False, f"Unavailable at {url}: {exc}")

    if response.status_code >= 500:
        return HealthCheck(name, False, f"{url} returned HTTP {response.status_code}.")
    return HealthCheck(name, True, f"Reachable at {url}.")
