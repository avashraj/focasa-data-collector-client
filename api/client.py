from datetime import datetime

import requests

from config import BASE_URL


def register(api_key: str, user_id: str, device_name: str, os_name: str) -> dict:
    url = f"{BASE_URL}/v1/users/register"
    headers = {"x-api-key": api_key}
    payload = {
        "user_id": user_id,
        "device_name": device_name,
        "os": os_name,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def start_task(api_key: str, task_id: str, user_id: str, name: str, start: datetime) -> dict:
    url = f"{BASE_URL}/v1/tasks/{task_id}/start"
    headers = {"x-api-key": api_key}
    payload = {"user_id": user_id, "name": name, "start": start.isoformat()}
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()
