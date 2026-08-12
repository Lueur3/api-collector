import json
from pathlib import Path
from dataclasses import asdict
import api_collector.models as models
from api_collector.config import read_config
from api_collector.parsers import parse_source
from api_collector.client import get_request
from typing import Any

MODULE_DIR = Path(__file__).parent
API_CONFIG = MODULE_DIR.parent / 'config.toml'
RES_PATH = MODULE_DIR.parent / 'results.json'

def get_api_responds(api_config:  list[models.Source]) -> list[models.SourcesResults]:
    responds: list[models.SourceResponse] = []
    for source in api_config:
        res = get_request(source.url, source.timeout)
        sr = models.SourceResponse(
            name=source.name,
            response=res[0],
            status_code=res[1]
        )

        responds.append(sr)

    return parse_source(responds)


def save_json_file(api_res: list[models.SourcesResults], file_path: Path) -> None:
    data = [asdict(source) for source in api_res]
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def show_api_results(api_results: list[models.SourcesResults]) -> None:
    for source in api_results:
        print(source.name)
        print(*source.items)
        print()

def main() -> None:
    api_config: list[models.Source] = read_config(API_CONFIG)
    results = get_api_responds(api_config)
    show_api_results(results)
    save_json_file(results, RES_PATH)


if __name__ == "__main__":
    main()