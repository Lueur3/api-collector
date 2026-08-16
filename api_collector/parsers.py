from collections.abc import Callable
from dataclasses import fields
from datetime import datetime

from api_collector import exceptions, models


def parse_joke_api(data: models.SourceResponse) -> list[models.ParsedItem]:
    api_response = {}

    if data.response.get("error"):
        raise exceptions.RequestError(status_code=data.status_code, raw=data.response)

    data_fields = {f.name for f in fields(models.JokeApi)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v

    return [models.JokeApi(**api_response)]


def parse_noozra(data: models.SourceResponse) -> list[models.ParsedItem]:
    res: list[models.ParsedItem] = []
    data_fields = {f.name for f in fields(models.Noozra)}
    for article in data.response["articles"]:
        api_response = {}
        for k, v in article.items():
            if k in data_fields:
                api_response[k] = v

        if "published_at" in api_response:
            try:
                dt = datetime.strptime(
                    api_response["published_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
            except ValueError:
                dt = datetime.strptime(
                    api_response["published_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                )
            api_response["published_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")

        res.append(models.Noozra(**api_response))

    return res


def parse_bored_api(data: models.SourceResponse) -> list[models.ParsedItem]:
    api_response = {}
    data_fields = {f.name for f in fields(models.BoredApi)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v

    return [models.BoredApi(**api_response)]


def parse_open_meteo(data: models.SourceResponse) -> list[models.ParsedItem]:
    api_response = {}
    data_fields = {f.name for f in fields(models.OpenMeteo)}
    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v
        if isinstance(v, dict):
            for k_c, v_c in v.items():
                if k_c in data_fields:
                    api_response[k_c] = v_c

    if "time" in api_response:
        dt = datetime.strptime(api_response["time"], "%Y-%m-%dT%H:%M")
        api_response["time"] = dt.strftime("%Y-%m-%d %H:%M:%S")

    return [models.OpenMeteo(**api_response)]


def parse_exchangerate(data: models.SourceResponse) -> list[models.ParsedItem]:
    api_response = {}

    if "error-type" in data.response.keys():
        raise exceptions.RequestError(status_code=data.status_code, raw=data.response)

    data_fields = {f.name for f in fields(models.Exchangerate)}

    for k, v in data.response.items():
        if k in data_fields:
            api_response[k] = v

    if "time_last_update_utc" in api_response:
        dt = datetime.strptime(
            api_response["time_last_update_utc"], "%a, %d %b %Y %H:%M:%S %z"
        )
        api_response["time_last_update_utc"] = dt.strftime("%Y-%m-%d %H:%M:%S")

    return [models.Exchangerate(**api_response)]


PARSE_SOURCES: dict[str, Callable[[models.SourceResponse], list[models.ParsedItem]]] = {
    "JokeApi": parse_joke_api,
    "Noozra": parse_noozra,
    "BoredApi": parse_bored_api,
    "OpenMeteo": parse_open_meteo,
    "Exchangerate": parse_exchangerate,
}


def parse_source(api_source: models.SourceResponse) -> models.SourcesResults:
    parse_functon = PARSE_SOURCES[api_source.name]

    sr = models.SourcesResults(name=api_source.name, items=parse_functon(api_source))

    return sr
