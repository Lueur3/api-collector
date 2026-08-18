from collections.abc import Callable
from dataclasses import fields
from datetime import datetime
from typing import Any

from api_collector import exceptions, models


def extract_fields(
    raw_data: dict[str, Any], target_cls: type, flatten: bool = False
) -> dict[str, Any]:
    data_fields = {f.name for f in fields(target_cls)}
    result = {k: v for k, v in raw_data.items() if k in data_fields}

    if flatten:
        for v in raw_data.values():
            if isinstance(v, dict):
                result.update(
                    {k_c: v_c for k_c, v_c in v.items() if k_c in data_fields}
                )

    return result


def parse_date(value: str, *formats: str) -> str:
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    return value


def parse_joke_api(data: models.SourceResponse) -> list[models.ParsedItem]:
    if data.response.get("error"):
        raise exceptions.RequestError(status_code=data.status_code, raw=data.response)

    return [models.JokeApi(**extract_fields(data.response, models.JokeApi))]


def parse_noozra(data: models.SourceResponse) -> list[models.ParsedItem]:
    items = [
        extract_fields(article, models.Noozra) for article in data.response["articles"]
    ]
    for item in items:
        item["published_at"] = parse_date(
            item["published_at"], "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"
        )

    return [models.Noozra(**item) for item in items]


def parse_bored_api(data: models.SourceResponse) -> list[models.ParsedItem]:
    return [models.BoredApi(**extract_fields(data.response, models.BoredApi))]


def parse_open_meteo(data: models.SourceResponse) -> list[models.ParsedItem]:
    item = extract_fields(data.response, models.OpenMeteo, flatten=True)
    item["time"] = parse_date(item["time"], "%Y-%m-%dT%H:%M")

    return [models.OpenMeteo(**item)]


def parse_exchangerate(data: models.SourceResponse) -> list[models.ParsedItem]:
    if "error-type" in data.response:
        raise exceptions.RequestError(status_code=data.status_code, raw=data.response)

    item = extract_fields(data.response, models.Exchangerate)
    item["time_last_update_utc"] = parse_date(
        item["time_last_update_utc"], "%a, %d %b %Y %H:%M:%S %z"
    )

    return [models.Exchangerate(**item)]


PARSE_SOURCES: dict[str, Callable[[models.SourceResponse], list[models.ParsedItem]]] = {
    "JokeApi": parse_joke_api,
    "Noozra": parse_noozra,
    "BoredApi": parse_bored_api,
    "OpenMeteo": parse_open_meteo,
    "Exchangerate": parse_exchangerate,
}


def parse_source(api_source: models.SourceResponse) -> models.SourcesResults:
    parse_functon = PARSE_SOURCES[api_source.name]

    parsed_items = parse_functon(api_source)
    return models.SourcesResults(name=api_source.name, data=parsed_items)
