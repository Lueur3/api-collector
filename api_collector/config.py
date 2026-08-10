from pathlib import Path
import tomllib
from typing import Any


def read_config(config_path: Path) -> dict[str, dict[str, Any]]:
    api_urls: dict[str, dict[str, Any]] = {}
    with open(config_path, 'rb') as f:    
        config = tomllib.load(f)
        for item in config['API']:
            name = item['name']

            api_urls[name] = {'URL': item['URL'], 'timeout': item.get('timeout', 5)}
    return api_urls

