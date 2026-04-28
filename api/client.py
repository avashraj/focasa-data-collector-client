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
