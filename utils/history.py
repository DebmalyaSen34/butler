from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config.settings import ASSISTANT_SETTINGS, COMMAND_HISTORY_FILE


def _load_history(path: Path = COMMAND_HISTORY_FILE) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as history_file:
        data = json.load(history_file)
    return data if isinstance(data, list) else []


def record_command(text: str, path: Path = COMMAND_HISTORY_FILE) -> None:
    history = _load_history(path)
    history.append(
        {
            "heard_at": datetime.now().isoformat(timespec="seconds"),
            "text": text,
        }
    )
    limit = int(ASSISTANT_SETTINGS.get("command_history_limit", 25))
    with path.open("w", encoding="utf-8") as history_file:
        json.dump(history[-limit:], history_file, indent=2)


def last_heard(path: Path = COMMAND_HISTORY_FILE) -> str | None:
    history = _load_history(path)
    if not history:
        return None
    return str(history[-1].get("text", "")).strip() or None
