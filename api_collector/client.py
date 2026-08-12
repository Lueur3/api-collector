import requests
from typing import Any


def get_request(api_url: str, api_timeout: float) -> tuple[Any, int]:
    r = requests.get(api_url, timeout=api_timeout)
    return (r.json(), r.status_code)

    
