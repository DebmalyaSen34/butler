from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None


BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "config" / "settings.toml"


DEFAULT_SETTINGS: dict[str, Any] = {
    "services": {
        "llama_cpp_url": "http://127.0.0.1:8080/completion",
        "ollama_url": "http://127.0.0.1:11434/api/generate",
        "ollama_model": "gemma4:e2b",
        "searxng_url": "http://127.0.0.1:8080/search",
        "health_timeout_seconds": 1.5,
    },
    "wake_word": {
        "models": ["jarvis"],
        "threshold": 0.35,
        "smoothing_window": 4,
        "required_hits": 2,
        "cooldown_seconds": 1.2,
        "sample_rate": 16000,
        "frame_size": 1280,
        "debug": True,
        "push_to_talk": True,
        "push_to_talk_key": "enter",
        "calibration_seconds": 1.5,
        "microphone_device_index": -1,
    },
    "speech": {
        "whisper_model": "mlx-community/whisper-small-mlx",
        "initial_prompt": "Jarvis voice assistant commands. Transcribe concise spoken user requests accurately.",
        "sample_rate": 16000,
        "timeout_seconds": 8,
        "phrase_time_limit_seconds": 30,
        "follow_up_timeout_seconds": 6,
        "retry_attempts": 1,
        "ambient_noise_seconds": 0.5,
        "energy_threshold": 300,
        "dynamic_energy_threshold": True,
        "pause_threshold": 0.75,
    },
    "assistant": {
        "tts_voice": "af_heart",
        "follow_up_mode": True,
        "confirm_risky_tools": True,
        "command_history_limit": 25,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_settings(path: Path = SETTINGS_FILE) -> dict[str, Any]:
    if not path.exists() or tomllib is None:
        return DEFAULT_SETTINGS

    with path.open("rb") as settings_file:
        user_settings = tomllib.load(settings_file)

    return _deep_merge(DEFAULT_SETTINGS, user_settings)


SETTINGS = load_settings()

LLAMA_CPP_URL = SETTINGS["services"]["llama_cpp_url"]
OLLAMA_URL = SETTINGS["services"]["ollama_url"]
OLLAMA_MODEL = SETTINGS["services"]["ollama_model"]

SEARXNG_URL = SETTINGS["services"]["searxng_url"]
PROMPT_TEMPLATE = "<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"

WAKE_WORD_SETTINGS = SETTINGS["wake_word"]
SPEECH_SETTINGS = SETTINGS["speech"]
ASSISTANT_SETTINGS = SETTINGS["assistant"]
MEMORY_FILE = BASE_DIR / "memory.json"
COMMAND_HISTORY_FILE = BASE_DIR / "command_history.json"
