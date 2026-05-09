from __future__ import annotations

import json
from pathlib import Path

from config.settings import MEMORY_FILE


DEFAULT_MEMORY = {
    "facts": [],
    "preferences": [],
}


def _load_memory(path: Path | None = None) -> dict[str, list[str]]:
    path = path or MEMORY_FILE
    if not path.exists():
        return {"facts": [], "preferences": []}

    with path.open("r", encoding="utf-8") as memory_file:
        data = json.load(memory_file)

    if isinstance(data, list):
        return {"facts": data, "preferences": []}

    memory = DEFAULT_MEMORY.copy()
    memory["facts"] = list(data.get("facts", []))
    memory["preferences"] = list(data.get("preferences", []))
    return memory


def _save_memory(memory: dict[str, list[str]], path: Path | None = None) -> None:
    path = path or MEMORY_FILE
    with path.open("w", encoding="utf-8") as memory_file:
        json.dump(memory, memory_file, indent=2)


def _infer_category(fact: str, category: str | None) -> str:
    if category in {"facts", "preferences"}:
        return category

    lower_fact = fact.lower()
    preference_markers = ("prefer", "preference", "like", "dislike", "favorite", "favourite")
    if any(marker in lower_fact for marker in preference_markers):
        return "preferences"
    return "facts"


def remember_fact(fact: str, category: str | None = None) -> str:
    """Saves a fact or preference into structured long-term memory."""
    memory = _load_memory()
    target_category = _infer_category(fact, category)

    if fact not in memory[target_category]:
        memory[target_category].append(fact)
        _save_memory(memory)

    return f"Remembered {target_category[:-1]}: {fact}"


def retrieve_facts(category: str | None = None) -> str:
    """Retrieves saved long-term memories."""
    memory = _load_memory()

    if category in {"facts", "preferences"}:
        values = memory.get(category, [])
        return f"Saved {category}: " + ", ".join(values) if values else f"No saved {category} yet."

    parts = []
    if memory["facts"]:
        parts.append("Facts: " + ", ".join(memory["facts"]))
    if memory["preferences"]:
        parts.append("Preferences: " + ", ".join(memory["preferences"]))
    return " | ".join(parts) if parts else "No memories saved yet."
