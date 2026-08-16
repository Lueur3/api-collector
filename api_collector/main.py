import json
from dataclasses import asdict
from pathlib import Path

from api_collector import exceptions, models
from api_collector.client import get_request
from api_collector.config import read_config
from api_collector.parsers import parse_source

MODULE_DIR = Path(__file__).parent
API_CONFIG = MODULE_DIR.parent / "config.toml"
RES_PATH = MODULE_DIR.parent / "results.json"


def get_api_responds(api_config: list[models.Source]) -> list[models.SourceResult]:
    parse_results: list[models.SourceResult] = []
    for source in api_config:
        try:
            res = get_request(source.url, source.timeout)
        except exceptions.NetworkError as e:
            sf = models.SourceFailure(
                name=source.name,
                items=[str(e), str(e.__cause__)],
                status_code=e.status_code,
                raw=e.raw,
            )
            parse_results.append(sf)

        else:
            sr = models.SourceResponse(
                name=source.name, response=res[0], status_code=res[1]
            )

            try:
                parse_result = parse_source(sr)
            except exceptions.RequestError as e:
                sf = models.SourceFailure(
                    name=sr.name,
                    status_code=e.status_code,
                    items=[e.message],
                    raw=e.raw,
                )
                parse_results.append(sf)
            else:
                parse_results.append(parse_result)

    return parse_results


def save_json_file(api_res: list[models.SourceResult], file_path: Path) -> None:
    data = [asdict(source) for source in api_res]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def show_api_results(api_results: list[models.SourceResult]) -> None:
    for source in api_results:
        print(source.name)
        for item in source.items:
            print(item)
            print()
        print()


def main() -> None:
    try:
        api_config: list[models.Source] = read_config(API_CONFIG)
        results = get_api_responds(api_config)
        show_api_results(results)
        save_json_file(results, RES_PATH)
    except exceptions.CollectorError as e:
        print(f"Error: {e}")
        print(f"Cause: {e.__cause__}")


if __name__ == "__main__":
    main()
