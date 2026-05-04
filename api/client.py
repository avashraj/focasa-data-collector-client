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


def start_task(
    api_key: str, task_id: str, user_id: str, name: str, start: datetime
) -> dict:
    url = f"{BASE_URL}/v1/tasks/{task_id}/start"
    headers = {"x-api-key": api_key}
    payload = {"user_id": user_id, "name": name, "start": start.isoformat()}
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def end_task(api_key: str, task_id: str, user_id: str, end: datetime) -> None:
    url = f"{BASE_URL}/v1/tasks/{task_id}/end"
    headers = {"x-api-key": api_key}
    payload = {"user_id": user_id, "end": end.isoformat()}
    response = requests.patch(url, json=payload, headers=headers, timeout=10)
    response.raise_for_status()


def upload_screenshot(
    api_key: str, user_id: str, task_id: str, timestamp: datetime, b64_image: str
) -> None:
    url = f"{BASE_URL}/v1/ingest/upload"
    payload = {
        "user_id": user_id,
        "task_id": task_id,
        "timestamp": timestamp.isoformat(),
        "screenshot": b64_image,
    }
    response = requests.post(url, json=payload, headers={"x-api-key": api_key}, timeout=10)
    response.raise_for_status()
