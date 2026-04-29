import json
from typing import Optional

from config import CONFIG_PATH


def _load_raw() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r") as f:
        return json.load(f)


def _save_raw(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w") as f:
        json.dump(data, f, indent=2)


def load_config() -> Optional[dict]:
    data = _load_raw()
    if "api_key" not in data or "user_id" not in data:
        return None
    return data


def save_config(api_key: str, user_id: str) -> None:
    data = _load_raw()
    data["api_key"] = api_key
    data["user_id"] = user_id
    _save_raw(data)


def save_active_task(task_id: str, name: str, start: str) -> None:
    data = _load_raw()
    data["active_task"] = {"task_id": task_id, "name": name, "start": start}
    _save_raw(data)


def load_active_task() -> Optional[dict]:
    data = _load_raw()
    return data.get("active_task")


def clear_active_task() -> None:
    data = _load_raw()
    data.pop("active_task", None)
    _save_raw(data)
