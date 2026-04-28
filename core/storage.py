import json
from typing import Optional

from config import CONFIG_PATH


def load_config() -> Optional[dict]:
    if not CONFIG_PATH.exists():
        return None
    with CONFIG_PATH.open("r") as f:
        return json.load(f)


def save_config(api_key: str, user_id: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w") as f:
        json.dump({"api_key": api_key, "user_id": user_id}, f, indent=2)
