from pathlib import Path
from typing import Any
from api_collector.config import read_config 
from api_collector.client import get_request 

MODULE_DIR = Path(__file__).parent
API_CONFIG = MODULE_DIR.parent / 'config.toml'

def get_api_item(api_config: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    data = {}
    for api_name, api_data in api_config.items():
        res = get_request(api_data['URL'], api_data['timeout'])
        data[api_name] = res

    return data


def show_api_results(api_results: dict[str, dict[str, Any]]) -> None:
    for api_name, api_result in api_results.items():
        print(api_name)
        print(api_result)
        print()

def main() -> None:
    api_config = read_config(API_CONFIG)
    api_results = get_api_item(api_config)
    show_api_results(api_results)
    

if __name__ == "__main__":
    main()